from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StudentBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: str
    registration_number: str
    parent_phone: Optional[str] = None


class StudentCreate(StudentBase):
    pass


class StudentResponse(StudentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceResponse(BaseModel):
    id: int
    student_id: int
    student_name: str
    date: datetime
    status: str
    confidence: Optional[float] = None
    whatsapp_notified: bool

    class Config:
        from_attributes = True


class RecognizeResponse(BaseModel):
    success: bool
    student: Optional[StudentResponse] = None
    confidence: Optional[float] = None
    message: str = ""


class RegisterFaceRequest(BaseModel):
    student_id: int


class AttendanceStats(BaseModel):
    total_students: int
    present_today: int
    absent_today: int
    attendance_rate: float


class SendNotificationRequest(BaseModel):
    student_id: int
    message: str


class ClassCreate(BaseModel):
    name: str
    schedule: Optional[str] = None


class ClassResponse(BaseModel):
    id: int
    name: str
    schedule: Optional[str] = None
    student_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class ClassStudentRequest(BaseModel):
    student_id: int


class AdminRegister(BaseModel):
    name: str
    email: str
    password: str


class AdminLogin(BaseModel):
    email: str
    password: str


class AdminResponse(BaseModel):
    id: int
    name: str
    email: str
    has_face: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    token: str
    admin: AdminResponse
