from datetime import datetime

from app import db


class Instructor(db.Model):
    __tablename__ = "instructors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True)

    status = db.Column(db.String(20), nullable=False, default="active")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Instructor {self.name}>"