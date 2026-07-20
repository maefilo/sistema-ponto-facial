from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from .database import Base
import enum


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), unique=True, nullable=False)
    registration_number = Column(String(50), unique=True, nullable=False)
    parent_phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    face_embeddings = relationship("FaceEmbedding", back_populates="student", cascade="all, delete-orphan")
    attendances = relationship("Attendance", back_populates="student")


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    embedding = Column(Text, nullable=False)
    image_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="face_embeddings")


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(AttendanceStatus), default=AttendanceStatus.PRESENT)
    confidence = Column(Float, nullable=True)
    whatsapp_notified = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="attendances")


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    schedule = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClassStudent(Base):
    __tablename__ = "class_students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    face_embedding = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
