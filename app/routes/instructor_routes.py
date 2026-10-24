
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from app import db
from app.models import Instructor


instructor_bp = Blueprint("instructors", __name__, url_prefix="/instructors")


@instructor_bp.route("/")
def index():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Instructor.query

    if search:
        query = query.filter(
            db.or_(
                Instructor.name.ilike(f"%{search}%"),
                Instructor.phone.ilike(f"%{search}%"),
            )
        )

    if status_filter in ["active", "inactive"]:
        query = query.filter(Instructor.status == status_filter)

    instructors = query.order_by(Instructor.name.asc()).all()

    return render_template(
        "instructors/index.html",
        instructors=instructors,
        search=search,
        status_filter=status_filter,
    )


@instructor_bp.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name:
            flash("Nama tentor wajib diisi.", "error")
            return render_template("instructors/form.html", instructor=None)

        instructor = Instructor(
            name=name,
            gender=gender or None,
            phone=phone or None,
            status="active",
        )

        try:
            db.session.add(instructor)
            db.session.commit()
            flash("Data tentor berhasil ditambahkan.", "success")
            return redirect(url_for("instructors.index"))

        except Exception:
            db.session.rollback()
            flash("Data tentor gagal disimpan.", "error")

    return render_template("instructors/form.html", instructor=None)


@instructor_bp.route("/<int:instructor_id>/edit", methods=["GET", "POST"])
def edit(instructor_id):
    instructor = db.get_or_404(Instructor, instructor_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        gender = request.form.get("gender", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name:
            flash("Nama tentor wajib diisi.", "error")
            return render_template("instructors/form.html", instructor=instructor)

        instructor.name = name
        instructor.gender = gender or None
        instructor.phone = phone or None

        try:
            db.session.commit()
            flash("Data tentor berhasil diperbarui.", "success")
            return redirect(url_for("instructors.index"))

        except Exception:
            db.session.rollback()
            flash("Perubahan data tentor gagal disimpan.", "error")

    return render_template("instructors/form.html", instructor=instructor,)


@instructor_bp.route("/<int:instructor_id>/toggle-status", methods=["POST"])
def toggle_status(instructor_id):
    instructor = db.get_or_404(Instructor, instructor_id)

    if instructor.status == "active":
        instructor.status = "inactive"
        message = f"Tentor {instructor.name} berhasil dinonaktifkan."
    else:
        instructor.status = "active"
        message = f"Tentor {instructor.name} berhasil diaktifkan kembali."

    try:
        db.session.commit()
        flash(message, "success")

    except Exception:
        db.session.rollback()
        flash("Status tentor gagal diperbarui.", "error")

    return redirect(url_for("instructors.index"))
