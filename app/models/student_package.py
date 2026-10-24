from datetime import date

from app import db


class StudentPackage(db.Model):
    __tablename__ = "student_packages"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)

    package_type_id = db.Column(db.Integer, db.ForeignKey("package_types.id"), nullable=False)

    purchase_date = db.Column(db.Date, nullable=False, default=date.today)

    status = db.Column(db.String(20), nullable=False, default="active")

    student = db.relationship("Student",backref=db.backref("packages", lazy=True))

    package_type = db.relationship("PackageType", backref=db.backref("student_packages", lazy=True))

    def __repr__(self):
        return (
            f"<StudentPackage student_id={self.student_id} "
            f"package_type_id={self.package_type_id}>"
        )