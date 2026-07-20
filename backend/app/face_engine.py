import os
import json
import numpy as np
import cv2
import faiss
from .config import config


class FaceEngine:
    def __init__(self):
        self._loaded = False
        self.embeddings_dir = config.FACE_DB_DIR
        os.makedirs(self.embeddings_dir, exist_ok=True)
        self.index = None
        self.labels = []
        self._load_index()

    def _ensure_loaded(self):
        if self._loaded:
            return
        from insightface.app import FaceAnalysis
        self.app = FaceAnalysis(
            name=config.MODEL_PACK,
            providers=["CPUExecutionProvider"],
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        self._loaded = True

    def _get_index_path(self):
        return os.path.join(self.embeddings_dir, "faiss.index")

    def _get_labels_path(self):
        return os.path.join(self.embeddings_dir, "labels.json")

    def _load_index(self):
        index_path = self._get_index_path()
        labels_path = self._get_labels_path()

        if os.path.exists(index_path) and os.path.exists(labels_path):
            self.index = faiss.read_index(index_path)
            with open(labels_path, "r") as f:
                self.labels = json.load(f)
        else:
            self.index = faiss.IndexFlatIP(512)
            self.labels = []

    def _save_index(self):
        faiss.write_index(self.index, self._get_index_path())
        with open(self._get_labels_path(), "w") as f:
            json.dump(self.labels, f)

    def extract_embedding(self, image_bytes: bytes) -> tuple[np.ndarray | None, dict | None]:
        self._ensure_loaded()
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None, None

        faces = self.app.get(img)
        if not faces:
            return None, None

        face = max(faces, key=lambda f: f.bbox[2] - f.bbox[0])
        embedding = face.normed_embedding
        bbox = face.bbox.astype(int).tolist()
        return embedding, {"bbox": bbox, "det_score": float(face.det_score)}

    def register_face(self, student_id: int, embedding: np.ndarray):
        self.index.add(embedding.reshape(1, -1).astype(np.float32))
        self.labels.append(student_id)
        self._save_index()

    def recognize(self, embedding: np.ndarray) -> tuple[int | None, float]:
        if self.index.ntotal == 0:
            return None, 0.0

        distances, indices = self.index.search(embedding.reshape(1, -1).astype(np.float32), 1)
        best_distance = float(distances[0][0])
        best_idx = int(indices[0][0])

        if best_distance < (1.0 - config.FACE_MATCH_THRESHOLD):
            return None, 0.0

        student_id = self.labels[best_idx]
        confidence = best_distance
        return student_id, confidence

    def delete_student_embeddings(self, student_id: int):
        indices_to_keep = [i for i, sid in enumerate(self.labels) if sid != student_id]
        if not indices_to_keep:
            self.index = faiss.IndexFlatIP(512)
            self.labels = []
        else:
            kept_embeddings = np.vstack([
                self.index.reconstruct(i) for i in indices_to_keep
            ])
            self.index = faiss.IndexFlatIP(512)
            self.index.add(kept_embeddings)
            self.labels = [self.labels[i] for i in indices_to_keep]
        self._save_index()


face_engine = FaceEngine()
