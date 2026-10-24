from datetime import datetime

from app import db


class PackageType(db.Model):
    __tablename__ = "package_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_type = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    session_quota = db.Column(db.Integer, nullable=False, default=4)
    
    min_participants = db.Column(db.Integer, nullable=False, default=1)
    max_participants = db.Column(db.Integer, nullable=False, default=1)

    status = db.Column(db.String(20), nullable=False, default="active")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<PackageType {self.name}>"