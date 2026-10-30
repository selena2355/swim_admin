
from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.orm import joinedload

from app import db
from app.models import (
    ScheduleSlot,
    ScheduleBooking,
    Student,
    StudentPackage,
    PackageType,
)


placement_bp = Blueprint("placements", __name__, url_prefix="/placements")


def get_active_student_packages():
    """Ambil paket aktif milik murid yang masih aktif."""
    return (
        StudentPackage.query
        .join(Student, StudentPackage.student_id == Student.id)
        .join(
            PackageType,
            StudentPackage.package_type_id == PackageType.id,
        )
        .filter(
            StudentPackage.status == "active",
            Student.status == "active",
            PackageType.status == "active",
        )
        .options(
            joinedload(StudentPackage.student),
            joinedload(StudentPackage.package_type),
        )
        .order_by(Student.name.asc())
        .all()
    )


@placement_bp.route("/")
def index():
    slots = (
        ScheduleSlot.query
        .options(
            joinedload(ScheduleSlot.instructor),
            joinedload(ScheduleSlot.pool),
            joinedload(ScheduleSlot.bookings)
            .joinedload(ScheduleBooking.student),
            joinedload(ScheduleSlot.bookings)
            .joinedload(ScheduleBooking.student_package)
            .joinedload(StudentPackage.package_type),
        )
        .order_by(
            ScheduleSlot.day_of_week.asc(),
            ScheduleSlot.start_time.asc(),
        )
        .all()
    )

    return render_template(
        "placements/index.html",
        slots=slots,
    )


@placement_bp.route("/<int:slot_id>/create", methods=["GET", "POST"])
def create(slot_id):
    slot = db.get_or_404(ScheduleSlot, slot_id)

    if slot.status != "active":
        flash("Slot nonaktif tidak dapat digunakan.", "error")
        return redirect(url_for("placements.index"))

    package_types = (
        PackageType.query
        .filter_by(status="active")
        .order_by(PackageType.name.asc())
        .all()
    )

    student_packages = get_active_student_packages()

    if request.method == "POST":
        package_type_id = request.form.get(
            "package_type_id",
            type=int,
        )

        raw_ids = request.form.getlist("student_package_ids")

        try:
            selected_ids = [int(value) for value in raw_ids]
        except (ValueError, TypeError):
            flash("Pilihan paket murid tidak valid.", "error")
            return redirect(
                url_for("placements.create", slot_id=slot.id)
            )

        package_type = db.session.get(PackageType, package_type_id)

        if not package_type or package_type.status != "active":
            flash("Tipe paket tidak valid atau sudah nonaktif.", "error")
            return redirect(
                url_for("placements.create", slot_id=slot.id)
            )

        if len(selected_ids) != len(set(selected_ids)):
            flash("Ada paket murid yang dipilih lebih dari sekali.", "error")
            return redirect(
                url_for("placements.create", slot_id=slot.id)
            )

        if not selected_ids:
            flash("Pilih murid yang akan ditempatkan.", "error")
            return redirect(
                url_for("placements.create", slot_id=slot.id)
            )

        # Satu slot diisi satu kelompok. Kelompok baru harus
        # ditempatkan sekaligus agar kapasitas minimal terpenuhi.
        existing_bookings = ScheduleBooking.query.filter_by(
            schedule_slot_id=slot.id,
            status="active",
        ).count()

        if existing_bookings:
            flash(
                "Slot ini sudah memiliki kelompok murid.",
                "error",
            )
            return redirect(url_for("placements.index"))

        selected_packages = (
            StudentPackage.query
            .filter(
                StudentPackage.id.in_(selected_ids),
                StudentPackage.status == "active",
            )
            .options(
                joinedload(StudentPackage.student),
                joinedload(StudentPackage.package_type),
            )
            .all()
        )

        if len(selected_packages) != len(selected_ids):
            flash(
                "Ada paket murid yang tidak ditemukan atau tidak aktif.",
                "error",
            )
            return redirect(
                url_for("placements.create", slot_id=slot.id)
            )

        # Semua murid harus menggunakan tipe paket yang dipilih.
        for student_package in selected_packages:
            if student_package.student.status != "active":
                flash(
                    f"Murid {student_package.student.name} tidak aktif.",
                    "error",
                )
                return redirect(
                    url_for("placements.create", slot_id=slot.id)
                )

            if student_package.package_type_id != package_type.id:
                flash(
                    "Semua murid harus menggunakan tipe paket yang sama.",
                    "error",
                )
                return redirect(
                    url_for("placements.create", slot_id=slot.id)
                )

            if student_package.package_type.status != "active":
                flash(
                    "Tipe paket salah satu murid sudah tidak aktif.",
                    "error",
                )
                return redirect(
                    url_for("placements.create", slot_id=slot.id)
                )

        # Pastikan jumlah peserta memenuhi aturan paket.
        total_students = len(selected_packages)

        if not (
            package_type.min_participants
            <= total_students
            <= package_type.max_participants
        ):
            flash(
                f"Paket {package_type.name} harus berisi "
                f"{package_type.min_participants}–"
                f"{package_type.max_participants} murid. "
                f"Kamu memilih {total_students} murid.",
                "error",
            )
            return redirect(
                url_for("placements.create", slot_id=slot.id)
            )

        # Cegah murid memiliki dua jadwal aktif yang waktunya
        # bertabrakan pada hari yang sama.
        for student_package in selected_packages:
            conflicting_booking = (
                ScheduleBooking.query
                .join(
                    ScheduleSlot,
                    ScheduleBooking.schedule_slot_id == ScheduleSlot.id,
                )
                .filter(
                    ScheduleBooking.student_id
                    == student_package.student_id,
                    ScheduleBooking.status == "active",
                    ScheduleSlot.status == "active",
                    ScheduleSlot.day_of_week == slot.day_of_week,
                    ScheduleSlot.start_time < slot.end_time,
                    ScheduleSlot.end_time > slot.start_time,
                )
                .first()
            )

            if conflicting_booking:
                flash(
                    f"Murid {student_package.student.name} sudah "
                    "memiliki jadwal aktif yang bertabrakan.",
                    "error",
                )
                return redirect(
                    url_for("placements.create", slot_id=slot.id)
                )

        try:
            # Kapasitas slot mengikuti paket kelompok.
            slot.capacity = package_type.max_participants

            for student_package in selected_packages:
                booking = ScheduleBooking(
                    schedule_slot_id=slot.id,
                    student_id=student_package.student_id,
                    student_package_id=student_package.id,
                    status="active",
                )
                db.session.add(booking)

            db.session.commit()

            flash(
                f"Berhasil menempatkan {total_students} murid "
                f"pada slot {slot.day_name}.",
                "success",
            )
            return redirect(url_for("placements.index"))

        except Exception:
            db.session.rollback()
            flash(
                "Penempatan gagal disimpan. Tidak ada perubahan "
                "yang disimpan.",
                "error",
            )

    return render_template(
        "placements/form.html",
        slot=slot,
        package_types=package_types,
        student_packages=student_packages,
    )
