import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TIDB_HOST: str = os.getenv("TIDB_HOST", "localhost")
    TIDB_PORT: int = int(os.getenv("TIDB_PORT", "4000"))
    TIDB_USER: str = os.getenv("TIDB_USER", "root")
    TIDB_PASSWORD: str = os.getenv("TIDB_PASSWORD", "")
    TIDB_DB_NAME: str = os.getenv("TIDB_DB_NAME", "facial_attendance")
    CA_PATH: str = os.getenv("CA_PATH", "")

    FACE_DB_DIR: str = os.getenv("FACE_DB_DIR", "data/face_db")
    FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.4"))
    MODEL_PACK: str = os.getenv("MODEL_PACK", "buffalo_l")

    WHATSAPP_SERVICE_URL: str = os.getenv("WHATSAPP_SERVICE_URL", "http://localhost:3001")
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))


config = Config()
