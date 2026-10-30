
from datetime import datetime

from app import db


class WaitlistEntry(db.Model):
    __tablename__ = "waitlist_entries"

    id = db.Column(db.Integer, primary_key=True)

    student_package_id = db.Column(db.Integer, db.ForeignKey("student_packages.id"), nullable=False)

    # Preferensi jadwal bersifat opsional.
    preferred_day = db.Column(db.Integer, nullable=True)
    preferred_start_time = db.Column(db.Time, nullable=True)

    notes = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="active")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    student_package = db.relationship("StudentPackage", backref=db.backref("waitlist_entries", lazy=True))

    def __repr__(self):
        return (
            f"<WaitlistEntry "
            f"student_package_id={self.student_package_id}>"
        )
