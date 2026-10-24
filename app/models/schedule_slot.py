
from datetime import datetime

from app import db


class ScheduleSlot(db.Model):
    __tablename__ = "schedule_slots"

    id = db.Column(db.Integer, primary_key=True)

    instructor_id = db.Column(db.Integer, db.ForeignKey("instructors.id"), nullable=False)

    pool_id = db.Column(db.Integer, db.ForeignKey("pools.id"), nullable=False)

    day_of_week = db.Column(db.Integer, nullable=False)

    start_time = db.Column(db.Time,nullable=False)

    end_time = db.Column(db.Time,nullable=False)

    capacity = db.Column(db.Integer, nullable=False, default=1)

    status = db.Column(db.String(20), nullable=False, default="active")

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now,onupdate=datetime.now)

    instructor = db.relationship("Instructor", backref=db.backref("schedule_slots", lazy=True))

    pool = db.relationship("Pool", backref=db.backref("schedule_slots", lazy=True))

    @property
    def day_name(self):
        days = {
            1: "Senin",
            2: "Selasa",
            3: "Rabu",
            4: "Kamis",
            5: "Jumat",
            6: "Sabtu",
            7: "Minggu"
        }

        return days.get(self.day_of_week, "Tidak diketahui")

    def __repr__(self):
        return f"<ScheduleSlot {self.id}>"
