import hashlib
import secrets
import json
import numpy as np
import faiss
from sqlalchemy.orm import Session


_tokens: dict[int, str] = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def generate_token(admin_id: int) -> str:
    token = secrets.token_hex(32)
    _tokens[admin_id] = token
    return token


def verify_token(token: str) -> int | None:
    for admin_id, t in _tokens.items():
        if t == token:
            return admin_id
    return None


def register_admin_face(admin_id: int, embedding: np.ndarray, db: Session):
    from .models import Admin
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if admin:
        admin.face_embedding = json.dumps(embedding.tolist())
        db.commit()


def recognize_admin_face(embedding: np.ndarray, db: Session) -> int | None:
    from .models import Admin
    admins = db.query(Admin).filter(Admin.face_embedding.isnot(None)).all()
    if not admins:
        return None

    best_admin_id = None
    best_distance = -1

    for admin in admins:
        stored = json.loads(admin.face_embedding)
        stored_emb = np.array(stored, dtype=np.float32).reshape(1, -1)
        query_emb = embedding.reshape(1, -1).astype(np.float32)

        index = faiss.IndexFlatIP(512)
        index.add(stored_emb)
        distances, _ = index.search(query_emb, 1)
        distance = float(distances[0][0])

        if distance > best_distance:
            best_distance = distance
            best_admin_id = admin.id

    if best_distance < 0.5:
        return None

    return best_admin_id
