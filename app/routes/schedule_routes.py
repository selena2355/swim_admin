
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from sqlalchemy import or_

from app import db
from app.models import ScheduleSlot, Instructor, Pool


schedule_bp = Blueprint(
    "schedules",
    __name__,
    url_prefix="/schedules",
)


DAY_NAMES = {
    1: "Senin",
    2: "Selasa",
    3: "Rabu",
    4: "Kamis",
    5: "Jumat",
    6: "Sabtu",
    7: "Minggu",
}


def parse_time(value):
    """Mengubah input jam HTML menjadi objek time."""
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (ValueError, TypeError):
        raise ValueError("Format jam tidak valid.")


def check_schedule_conflict(
    instructor_id,
    pool_id,
    day_of_week,
    start_time,
    end_time,
    exclude_id=None,
):
    """
    Memeriksa bentrok jadwal tentor.

    Kolam boleh digunakan oleh beberapa tentor pada waktu yang sama.
    """

    query = ScheduleSlot.query.filter(
        ScheduleSlot.status == "active",
        ScheduleSlot.instructor_id == instructor_id,
        ScheduleSlot.day_of_week == day_of_week,
        ScheduleSlot.start_time < end_time,
        ScheduleSlot.end_time > start_time,
    )

    if exclude_id is not None:
        query = query.filter(ScheduleSlot.id != exclude_id)

    conflict = query.first()

    if conflict:
        return (
            False,
            f"Tentor {conflict.instructor.name} sudah memiliki "
            f"jadwal pada hari {conflict.day_name}, "
            f"pukul {conflict.start_time.strftime('%H:%M')}–"
            f"{conflict.end_time.strftime('%H:%M')}.",
        )

    return True, None


def save_schedule_form(slot=None):
    """Memvalidasi dan menyimpan data slot jadwal."""

    instructor_id = request.form.get("instructor_id", type=int)
    pool_id = request.form.get("pool_id", type=int)
    day_of_week = request.form.get("day_of_week", type=int)

    start_value = request.form.get("start_time", "").strip()
    end_value = request.form.get("end_time", "").strip()

    if not instructor_id or not pool_id:
        return False, "Tentor dan kolam wajib dipilih."

    if day_of_week not in DAY_NAMES:
        return False, "Hari yang dipilih tidak valid."

    instructor = db.session.get(Instructor, instructor_id)
    pool = db.session.get(Pool, pool_id)

    if not instructor or instructor.status != "active":
        return False, "Tentor tidak ditemukan atau sudah tidak aktif."

    if not pool or pool.status != "active":
        return False, "Kolam tidak ditemukan atau sudah tidak aktif."

    try:
        start_time = parse_time(start_value)
        end_time = parse_time(end_value)
    except ValueError as error:
        return False, str(error)

    if start_time >= end_time:
        return False, "Jam selesai harus setelah jam mulai."

    status = (
        request.form.get("status", "active").strip()
        if slot
        else "active"
    )

    if status not in ("active", "inactive"):
        return False, "Status jadwal tidak valid."

    # Slot aktif tidak boleh berbenturan dengan slot aktif lain.
    if status == "active":
        valid, message = check_schedule_conflict(
            instructor_id=instructor_id,
            pool_id=pool_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            exclude_id=slot.id if slot else None,
        )

        if not valid:
            return False, message

    if slot is None:
        slot = ScheduleSlot()

    slot.instructor_id = instructor_id
    slot.pool_id = pool_id
    slot.day_of_week = day_of_week
    slot.start_time = start_time
    slot.end_time = end_time
    slot.status = status

    # Kapasitas akan ditentukan ketika kelompok murid ditempatkan.
    # Nilai awal hanya sebagai batas sementara, bukan tipe paket.
    if slot.capacity is None or slot.capacity < 1:
        slot.capacity = 5

    try:
        db.session.add(slot)
        db.session.commit()
        return True, "Slot jadwal berhasil disimpan."
    except Exception:
        db.session.rollback()
        return False, "Slot jadwal gagal disimpan."


@schedule_bp.route("/")
def index():
    slots = ScheduleSlot.query.order_by(
        ScheduleSlot.day_of_week.asc(),
        ScheduleSlot.start_time.asc(),
        ScheduleSlot.id.asc(),
    ).all()

    grouped_slots = {
        day: [
            slot for slot in slots
            if slot.day_of_week == day
        ]
        for day in DAY_NAMES
    }

    return render_template(
        "schedules/index.html",
        grouped_slots=grouped_slots,
        day_names=DAY_NAMES,
        total_slots=slots,
    )


@schedule_bp.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        success, message = save_schedule_form()

        if success:
            flash(message, "success")
            return redirect(url_for("schedules.index"))

        flash(message, "error")

    instructors = Instructor.query.filter_by(
        status="active"
    ).order_by(Instructor.name.asc()).all()

    pools = Pool.query.filter_by(
        status="active"
    ).order_by(Pool.name.asc()).all()

    return render_template(
        "schedules/form.html",
        slot=None,
        instructors=instructors,
        pools=pools,
        day_names=DAY_NAMES,
    )


@schedule_bp.route("/<int:slot_id>/edit", methods=["GET", "POST"])
def edit(slot_id):
    slot = db.get_or_404(ScheduleSlot, slot_id)

    if request.method == "POST":
        success, message = save_schedule_form(slot)

        if success:
            flash(message, "success")
            return redirect(url_for("schedules.index"))

        flash(message, "error")

    instructors = Instructor.query.filter(
        or_(
            Instructor.status == "active",
            Instructor.id == slot.instructor_id,
        )
    ).order_by(Instructor.name.asc()).all()

    pools = Pool.query.filter(
        or_(
            Pool.status == "active",
            Pool.id == slot.pool_id,
        )
    ).order_by(Pool.name.asc()).all()

    return render_template(
        "schedules/form.html",
        slot=slot,
        instructors=instructors,
        pools=pools,
        day_names=DAY_NAMES,
    )


@schedule_bp.route(
    "/<int:slot_id>/toggle-status",
    methods=["POST"],
)
def toggle_status(slot_id):
    slot = db.get_or_404(ScheduleSlot, slot_id)

    if slot.status == "active":
        slot.status = "inactive"
    else:
        # Saat diaktifkan kembali, periksa bentrok jadwal.
        valid, message = check_schedule_conflict(
            instructor_id=slot.instructor_id,
            pool_id=slot.pool_id,
            day_of_week=slot.day_of_week,
            start_time=slot.start_time,
            end_time=slot.end_time,
            exclude_id=slot.id,
        )

        if not valid:
            flash(message, "error")
            return redirect(url_for("schedules.index"))

        slot.status = "active"

    try:
        db.session.commit()
        flash("Status slot jadwal berhasil diperbarui.", "success")
    except Exception:
        db.session.rollback()
        flash("Status slot jadwal gagal diperbarui.", "error")

    return redirect(url_for("schedules.index"))
