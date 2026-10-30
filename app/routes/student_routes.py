
from datetime import date, datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from app import db
from app.models import Student, StudentPackage, PackageType


student_bp = Blueprint("students", __name__, url_prefix="/students",)


def parse_birth_date(value):
    if not value:
        return None

    try:
        birth_date = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Format tanggal lahir tidak valid.")

    if birth_date > date.today():
        raise ValueError("Tanggal lahir tidak boleh di masa depan.")

    return birth_date


@student_bp.route("/")
def index():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Student.query

    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))

    if status_filter in ["active", "inactive"]:
        query = query.filter(Student.status == status_filter)

    students = query.order_by(Student.name.asc()).all()

    return render_template(
        "students/index.html",
        students=students,
        search=search,
        status_filter=status_filter,
    )


@student_bp.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        gender = request.form.get("gender", "").strip()
        guardian_name = request.form.get("guardian_name", "").strip()
        guardian_phone = request.form.get("guardian_phone", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            flash("Nama murid wajib diisi.", "error")
            return render_template("students/form.html", student=None)

        if gender and gender not in ["male", "female"]:
            flash("Jenis kelamin tidak valid.", "error")
            return render_template("students/form.html", student=None)

        try:
            birth_date = parse_birth_date(
                request.form.get("birth_date", "").strip()
            )
        except ValueError as error:
            flash(str(error), "error")
            return render_template("students/form.html", student=None)

        student = Student(
            name=name,
            birth_date=birth_date,
            gender=gender or None,
            guardian_name=guardian_name or None,
            guardian_phone=guardian_phone or None,
            address=address or None,
            status="active",
        )

        try:
            db.session.add(student)
            db.session.commit()
            flash("Data murid berhasil ditambahkan.", "success")
            return redirect(url_for("students.detail", student_id=student.id))

        except Exception:
            db.session.rollback()
            flash("Data murid gagal disimpan.", "error")

    return render_template("students/form.html", student=None)



@student_bp.route("/<int:student_id>")
def detail(student_id):
    student = db.get_or_404(Student, student_id)

    packages = (
        StudentPackage.query
        .filter_by(student_id=student.id)
        .order_by(
            StudentPackage.purchase_date.desc(),
            StudentPackage.id.desc(),
        )
        .all()
    )

    active_packages = (
        PackageType.query
        .filter_by(status="active")
        .order_by(PackageType.name.asc())
        .all()
    )

    return render_template(
        "students/detail.html",
        student=student,
        packages=packages,
        active_packages=active_packages,
        today=date.today().isoformat(),
    )



@student_bp.route("/<int:student_id>/edit", methods=["GET", "POST"])
def edit(student_id):
    student = db.get_or_404(Student, student_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        gender = request.form.get("gender", "").strip()
        guardian_name = request.form.get("guardian_name", "").strip()
        guardian_phone = request.form.get("guardian_phone", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            flash("Nama murid wajib diisi.", "error")
            return render_template("students/form.html", student=student)

        if gender and gender not in ["male", "female"]:
            flash("Jenis kelamin tidak valid.", "error")
            return render_template("students/form.html", student=student)

        try:
            birth_date = parse_birth_date(
                request.form.get("birth_date", "").strip()
            )
        except ValueError as error:
            flash(str(error), "error")
            return render_template("students/form.html", student=student)

        student.name = name
        student.birth_date = birth_date
        student.gender = gender or None
        student.guardian_name = guardian_name or None
        student.guardian_phone = guardian_phone or None
        student.address = address or None

        try:
            db.session.commit()
            flash("Data murid berhasil diperbarui.", "success")
            return redirect(url_for("students.detail", student_id=student.id))

        except Exception:
            db.session.rollback()
            flash("Perubahan data murid gagal disimpan.", "error")

    return render_template("students/form.html", student=student)


@student_bp.route("/<int:student_id>/toggle-status", methods=["POST"])
def toggle_status(student_id):
    student = db.get_or_404(Student, student_id)

    if student.status == "active":
        student.status = "inactive"
        message = f"Murid {student.name} berhasil dinonaktifkan."
    else:
        student.status = "active"
        message = f"Murid {student.name} berhasil diaktifkan kembali."

    try:
        db.session.commit()
        flash(message, "success")

    except Exception:
        db.session.rollback()
        flash("Status murid gagal diperbarui.", "error")

    return redirect(url_for("students.index"))


@student_bp.route("/<int:student_id>/packages/add", methods=["POST"])
def add_package(student_id):
    student = db.get_or_404(Student, student_id)

    package_type_id = request.form.get("package_type_id", type=int)
    purchase_date_text = request.form.get("purchase_date", "").strip()

    package_type = db.session.get(PackageType, package_type_id)

    if not package_type or package_type.status != "active":
        flash("Pilih tipe paket yang masih aktif.", "error")
        return redirect(url_for("students.detail", student_id=student.id))

    try:
        purchase_date = (
            datetime.strptime(purchase_date_text, "%Y-%m-%d").date()
            if purchase_date_text
            else date.today()
        )
    except ValueError:
        flash("Tanggal pembelian tidak valid.", "error")
        return redirect(url_for("students.detail", student_id=student.id))

    if purchase_date > date.today():
        flash("Tanggal pembelian tidak boleh di masa depan.", "error")
        return redirect(url_for("students.detail", student_id=student.id))

    student_package = StudentPackage(
        student_id=student.id,
        package_type_id=package_type.id,
        purchase_date=purchase_date,
        status="active",
    )

    try:
        db.session.add(student_package)
        db.session.commit()
        flash("Riwayat paket berhasil ditambahkan.", "success")

    except Exception:
        db.session.rollback()
        flash("Riwayat paket gagal disimpan.", "error")

    return redirect(url_for("students.detail", student_id=student.id))
