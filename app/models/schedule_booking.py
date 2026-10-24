
from datetime import datetime

from app import db


class ScheduleBooking(db.Model):
    __tablename__ = "schedule_bookings"

    id = db.Column(db.Integer, primary_key=True)

    schedule_slot_id = db.Column(db.Integer, db.ForeignKey("schedule_slots.id"), nullable=False)

    student_id = db.Column(db.Integer, db.ForeignKey("students.id"),nullable=False)

    status = db.Column(db.String(20), nullable=False, default="active")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    schedule_slot = db.relationship("ScheduleSlot", backref=db.backref("bookings", lazy=True))

    student = db.relationship("Student", backref=db.backref("schedule_bookings", lazy=True))

    def __repr__(self):
        return (
            f"<ScheduleBooking "
            f"student_id={self.student_id} "
            f"schedule_slot_id={self.schedule_slot_id}>"
        )
