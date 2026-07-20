from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import json

from .database import get_db, engine
from .models import Student, FaceEmbedding, Attendance, AttendanceStatus, Class, ClassStudent, Admin, Base
from .schemas import (
    StudentCreate,
    StudentResponse,
    AttendanceResponse,
    RecognizeResponse,
    AttendanceStats,
    SendNotificationRequest,
    ClassCreate,
    ClassResponse,
    ClassStudentRequest,
    AdminRegister,
    AdminLogin,
    AdminResponse,
    TokenResponse,
)
from .face_engine import face_engine
from .whatsapp_client import send_attendance_notification
from . import auth

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Facial Attendance API",
    description="Sistema de presença por reconhecimento facial",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Facial Attendance API - Running"}


@app.get("/health")
def health():
    return {"status": "ok", "faces_registered": face_engine.index.ntotal}


@app.post("/students", response_model=StudentResponse)
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    existing = db.query(Student).filter(
        (Student.phone == student.phone)
        | (Student.registration_number == student.registration_number)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Telefone ou matrícula já cadastrado")
    db_student = Student(**student.model_dump())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


@app.get("/students", response_model=list[StudentResponse])
def list_students(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Student).offset(skip).limit(limit).all()


@app.get("/students/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return student


@app.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    face_engine.delete_student_embeddings(student_id)
    db.delete(student)
    db.commit()
    return {"message": "Aluno removido com sucesso"}


@app.post("/students/{student_id}/register-face")
async def register_face(student_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    image_bytes = await file.read()
    embedding, info = face_engine.extract_embedding(image_bytes)
    if embedding is None:
        raise HTTPException(status_code=400, detail="Nenhum rosto detectado na imagem")

    face_engine.register_face(student_id, embedding)

    db_embedding = FaceEmbedding(
        student_id=student_id,
        embedding=json.dumps(embedding.tolist()),
        image_path=file.filename,
    )
    db.add(db_embedding)
    db.commit()

    return {
        "message": "Rosto registrado com sucesso",
        "student_id": student_id,
        "det_score": info["det_score"],
    }


@app.post("/recognize", response_model=RecognizeResponse)
async def recognize_face(file: UploadFile = File(...), db: Session = Depends(get_db)):
    image_bytes = await file.read()
    embedding, info = face_engine.extract_embedding(image_bytes)
    if embedding is None:
        return RecognizeResponse(success=False, message="Nenhum rosto detectado na imagem")

    student_id, confidence = face_engine.recognize(embedding)
    if student_id is None:
        return RecognizeResponse(success=False, message="Rosto não reconhecido no sistema")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return RecognizeResponse(success=False, message="Aluno não encontrado no banco de dados")

    today = datetime.utcnow().date()
    existing = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.date >= datetime.combine(today, datetime.min.time()),
    ).first()

    status = AttendanceStatus.PRESENT
    if not existing:
        attendance = Attendance(
            student_id=student_id,
            status=status,
            confidence=confidence,
        )
        db.add(attendance)
        db.commit()

        date_str = datetime.utcnow().strftime("%d/%m/%Y %H:%M")
        if student.parent_phone:
            await send_attendance_notification(
                student.name,
                student.parent_phone,
                status.value,
                date_str,
            )

    return RecognizeResponse(
        success=True,
        student=StudentResponse.model_validate(student),
        confidence=confidence,
        message="Presença registrada com sucesso",
    )


@app.get("/attendances", response_model=list[AttendanceResponse])
def list_attendances(
    date: str = None,
    student_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Attendance)
    if date:
        query = query.filter(Attendance.date >= date)
    if student_id:
        query = query.filter(Attendance.student_id == student_id)
    attendances = query.order_by(Attendance.date.desc()).offset(skip).limit(limit).all()
    result = []
    for att in attendances:
        student = db.query(Student).filter(Student.id == att.student_id).first()
        result.append(
            AttendanceResponse(
                id=att.id,
                student_id=att.student_id,
                student_name=student.name if student else "Desconhecido",
                date=att.date,
                status=att.status.value,
                confidence=att.confidence,
                whatsapp_notified=bool(att.whatsapp_notified),
            )
        )
    return result


@app.get("/stats", response_model=AttendanceStats)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Student).count()
    today = datetime.utcnow().date()
    present = db.query(Attendance).filter(
        Attendance.date >= datetime.combine(today, datetime.min.time()),
        Attendance.status == AttendanceStatus.PRESENT,
    ).count()
    rate = (present / total * 100) if total > 0 else 0.0
    return AttendanceStats(
        total_students=total,
        present_today=present,
        absent_today=total - present,
        attendance_rate=round(rate, 2),
    )


@app.get("/whatsapp-status")
async def whatsapp_status():
    from .config import config
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{config.WHATSAPP_SERVICE_URL}/status", timeout=3.0)
            return r.json()
    except Exception:
        return {"status": "offline", "message": "Serviço WhatsApp não disponível. Para usar notificações, inicie o WhatsApp service localmente."}


@app.post("/notify")
async def send_notification(req: SendNotificationRequest, db: Session = Depends(get_db)):
    from .whatsapp_client import send_whatsapp_message

    student = db.query(Student).filter(Student.id == req.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    if not student.parent_phone:
        raise HTTPException(status_code=400, detail="Telefone do responsável não cadastrado")

    success = await send_whatsapp_message(student.parent_phone, req.message)
    if success:
        return {"message": "Notificação enviada com sucesso", "whatsapp": "online"}
    return {"message": "Serviço WhatsApp offline. Notificação não enviada.", "whatsapp": "offline"}


@app.post("/classes", response_model=ClassResponse)
def create_class(class_data: ClassCreate, db: Session = Depends(get_db)):
    db_class = Class(name=class_data.name, schedule=class_data.schedule)
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return ClassResponse(
        id=db_class.id,
        name=db_class.name,
        schedule=db_class.schedule,
        student_count=0,
        created_at=db_class.created_at,
    )


@app.get("/classes", response_model=list[ClassResponse])
def list_classes(db: Session = Depends(get_db)):
    classes = db.query(Class).all()
    result = []
    for c in classes:
        count = db.query(ClassStudent).filter(ClassStudent.class_id == c.id).count()
        result.append(ClassResponse(
            id=c.id,
            name=c.name,
            schedule=c.schedule,
            student_count=count,
            created_at=c.created_at,
        ))
    return result


@app.get("/classes/{class_id}", response_model=ClassResponse)
def get_class(class_id: int, db: Session = Depends(get_db)):
    db_class = db.query(Class).filter(Class.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    count = db.query(ClassStudent).filter(ClassStudent.class_id == class_id).count()
    return ClassResponse(
        id=db_class.id,
        name=db_class.name,
        schedule=db_class.schedule,
        student_count=count,
        created_at=db_class.created_at,
    )


@app.delete("/classes/{class_id}")
def delete_class(class_id: int, db: Session = Depends(get_db)):
    db_class = db.query(Class).filter(Class.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    db.query(ClassStudent).filter(ClassStudent.class_id == class_id).delete()
    db.delete(db_class)
    db.commit()
    return {"message": "Turma removida com sucesso"}


@app.post("/classes/{class_id}/students")
def add_student_to_class(class_id: int, req: ClassStudentRequest, db: Session = Depends(get_db)):
    db_class = db.query(Class).filter(Class.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    student = db.query(Student).filter(Student.id == req.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    exists = db.query(ClassStudent).filter(
        ClassStudent.class_id == class_id,
        ClassStudent.student_id == req.student_id,
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Aluno já esta nesta turma")
    db.add(ClassStudent(class_id=class_id, student_id=req.student_id))
    db.commit()
    return {"message": f"Aluno {student.name} adicionado a turma {db_class.name}"}


@app.delete("/classes/{class_id}/students/{student_id}")
def remove_student_from_class(class_id: int, student_id: int, db: Session = Depends(get_db)):
    cs = db.query(ClassStudent).filter(
        ClassStudent.class_id == class_id,
        ClassStudent.student_id == student_id,
    ).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Aluno não encontrado nesta turma")
    db.delete(cs)
    db.commit()
    return {"message": "Aluno removido da turma"}


@app.get("/classes/{class_id}/students", response_model=list[StudentResponse])
def list_class_students(class_id: int, db: Session = Depends(get_db)):
    db_class = db.query(Class).filter(Class.id == class_id).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    students = db.query(Student).join(ClassStudent).filter(ClassStudent.class_id == class_id).all()
    return students


@app.post("/auth/register", response_model=TokenResponse)
async def register_admin(
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    name: str = Form(None),
    email: str = Form(None),
    password: str = Form(None),
    json_data: str = Form(None),
):
    if json_data:
        data = AdminRegister.model_validate_json(json_data)
    elif email and password:
        data = AdminRegister(name=name or "", email=email, password=password)
    else:
        raise HTTPException(status_code=400, detail="Dados obrigatórios não enviados")

    existing = db.query(Admin).filter(Admin.email == data.email).first()
    
    if existing:
        token = auth.generate_token(existing.id)
        if file:
            image_bytes = await file.read()
            embedding, info = face_engine.extract_embedding(image_bytes)
            if embedding is not None:
                auth.register_admin_face(existing.id, embedding, db)
        return TokenResponse(
            token=token,
            admin=AdminResponse(
                id=existing.id,
                name=existing.name,
                email=existing.email,
                has_face=existing.face_embedding is not None,
                created_at=existing.created_at,
            ),
        )

    admin = Admin(
        name=data.name,
        email=data.email,
        password_hash=auth.hash_password(data.password),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    if file:
        image_bytes = await file.read()
        embedding, info = face_engine.extract_embedding(image_bytes)
        if embedding is not None:
            auth.register_admin_face(admin.id, embedding, db)
            db.refresh(admin)

    token = auth.generate_token(admin.id)
    return TokenResponse(
        token=token,
        admin=AdminResponse(
            id=admin.id,
            name=admin.name,
            email=admin.email,
            has_face=admin.face_embedding is not None,
            created_at=admin.created_at,
        ),
    )


@app.post("/auth/login", response_model=TokenResponse)
def login_admin(data: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == data.email).first()
    if not admin or not auth.verify_password(data.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")

    token = auth.generate_token(admin.id)
    return TokenResponse(
        token=token,
        admin=AdminResponse(
            id=admin.id,
            name=admin.name,
            email=admin.email,
            has_face=admin.face_embedding is not None,
            created_at=admin.created_at,
        ),
    )


@app.post("/auth/register-face")
async def register_admin_face(admin_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin não encontrado")

    image_bytes = await file.read()
    embedding, info = face_engine.extract_embedding(image_bytes)
    if embedding is None:
        raise HTTPException(status_code=400, detail="Nenhum rosto detectado na imagem")

    auth.register_admin_face(admin_id, embedding, db)
    return {"message": "Rosto do admin registrado com sucesso", "det_score": info["det_score"]}


@app.post("/auth/login-face")
async def login_face(file: UploadFile = File(...), db: Session = Depends(get_db)):
    image_bytes = await file.read()
    embedding, info = face_engine.extract_embedding(image_bytes)
    if embedding is None:
        raise HTTPException(status_code=400, detail="Nenhum rosto detectado na imagem")

    admin_id = auth.recognize_admin_face(embedding, db)
    if admin_id is None:
        raise HTTPException(status_code=401, detail="Rosto não reconhecido como admin")

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin não encontrado")

    token = auth.generate_token(admin.id)
    return TokenResponse(
        token=token,
        admin=AdminResponse(
            id=admin.id,
            name=admin.name,
            email=admin.email,
            has_face=True,
            created_at=admin.created_at,
        ),
    )


@app.get("/auth/me", response_model=AdminResponse)
def get_current_admin(token: str, db: Session = Depends(get_db)):
    admin_id = auth.verify_token(token)
    if not admin_id:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin não encontrado")

    return AdminResponse(
        id=admin.id,
        name=admin.name,
        email=admin.email,
        has_face=admin.face_embedding is not None,
        created_at=admin.created_at,
    )
