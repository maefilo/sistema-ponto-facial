import hashlib
import secrets
import json
import os
import numpy as np
import faiss
from .config import config


ADMIN_FACE_DIR = os.path.join(config.FACE_DB_DIR, "admin_faces")
os.makedirs(ADMIN_FACE_DIR, exist_ok=True)

_tokens: dict[int, str] = {}
_admin_index = None
_admin_labels: list[int] = []


def _get_admin_index_path():
    return os.path.join(ADMIN_FACE_DIR, "admin_faiss.index")


def _get_admin_labels_path():
    return os.path.join(ADMIN_FACE_DIR, "admin_labels.json")


def _load_admin_index():
    global _admin_index, _admin_labels
    index_path = _get_admin_index_path()
    labels_path = _get_admin_labels_path()

    if os.path.exists(index_path) and os.path.exists(labels_path):
        _admin_index = faiss.read_index(index_path)
        with open(labels_path, "r") as f:
            _admin_labels = json.load(f)
    else:
        _admin_index = faiss.IndexFlatIP(512)
        _admin_labels = []


def _save_admin_index():
    faiss.write_index(_admin_index, _get_admin_index_path())
    with open(_get_admin_labels_path(), "w") as f:
        json.dump(_admin_labels, f)


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


def register_admin_face(admin_id: int, embedding: np.ndarray):
    _load_admin_index()
    _admin_index.add(embedding.reshape(1, -1).astype(np.float32))
    _admin_labels.append(admin_id)
    _save_admin_index()


def recognize_admin_face(embedding: np.ndarray) -> int | None:
    _load_admin_index()
    if _admin_index.ntotal == 0:
        return None

    distances, indices = _admin_index.search(embedding.reshape(1, -1).astype(np.float32), 1)
    best_distance = float(distances[0][0])
    best_idx = int(indices[0][0])

    if best_distance < 0.5:
        return None

    return _admin_labels[best_idx]
