
from datetime import datetime

from app import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False)

    guardian_name = db.Column(db.String(100), nullable=False)
    guardian_phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), nullable=False, default="active")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Student {self.name}>"
