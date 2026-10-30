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
from sqlalchemy.orm import joinedload

from app import db
from app.models import (
    ScheduleSlot,
    ScheduleBooking,
    StudentPackage,
    Student,
    PackageType,
    Instructor,
    Pool,
)

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
    
def get_active_student_packages():
    """Mengambil paket aktif milik murid aktif."""
    return (
        StudentPackage.query
        .join(Student, StudentPackage.student_id == Student.id)
        .join(PackageType, StudentPackage.package_type_id == PackageType.id)
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
    """Memvalidasi dan menyimpan slot beserta kelompok murid."""

    instructor_id = request.form.get("instructor_id", type=int)
    pool_id = request.form.get("pool_id", type=int)
    day_of_week = request.form.get("day_of_week", type=int)

    start_value = request.form.get("start_time", "").strip()
    end_value = request.form.get("end_time", "").strip()

    def fail(message):
        db.session.rollback()
        return False, message

    if not instructor_id or not pool_id:
        return fail("Tentor dan kolam wajib dipilih.")

    if day_of_week not in DAY_NAMES:
        return fail("Hari yang dipilih tidak valid.")

    instructor = db.session.get(Instructor, instructor_id)
    pool = db.session.get(Pool, pool_id)

    if not instructor or instructor.status != "active":
        return fail("Tentor tidak ditemukan atau sudah tidak aktif.")

    if not pool or pool.status != "active":
        return fail("Kolam tidak ditemukan atau sudah tidak aktif.")

    try:
        start_time = parse_time(start_value)
        end_time = parse_time(end_value)
    except ValueError as error:
        return fail(str(error))

    if start_time >= end_time:
        return fail("Jam selesai harus setelah jam mulai.")

    status = slot.status if slot else "active"

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
            return fail(message)

    # Ambil pilihan kelompok dari form.
    package_type_id = request.form.get("package_type_id", type=int)
    raw_ids = request.form.getlist("student_package_ids")

    try:
        selected_ids = [int(value) for value in raw_ids]
    except (ValueError, TypeError):
        return fail("Pilihan paket murid tidak valid.")

    if len(selected_ids) != len(set(selected_ids)):
        return fail("Ada paket murid yang dipilih lebih dari sekali.")

    if bool(package_type_id) != bool(selected_ids):
        return fail(
            "Pilih jenis paket dan murid secara lengkap, "
            "atau biarkan keduanya kosong."
        )

    selected_packages = []
    package_type = None

    if selected_ids:
        package_type = db.session.get(PackageType, package_type_id)

        if not package_type or package_type.status != "active":
            return fail("Jenis paket tidak ditemukan atau sudah nonaktif.")

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
            return fail(
                "Ada paket murid yang tidak ditemukan atau tidak aktif."
            )

        # Validasi setiap murid dan jenis paketnya.
        student_ids = []

        for student_package in selected_packages:
            student = student_package.student

            if student.status != "active":
                return fail(
                    f"Murid {student.name} tidak berstatus aktif."
                )

            if student_package.package_type_id != package_type.id:
                return fail(
                    "Semua murid harus menggunakan jenis paket yang sama."
                )

            if student_package.package_type.status != "active":
                return fail("Jenis paket salah satu murid sudah nonaktif.")

            student_ids.append(student.id)

        if len(student_ids) != len(set(student_ids)):
            return fail(
                "Satu murid tidak boleh dipilih lebih dari satu kali."
            )

        total_students = len(selected_packages)

        if not (
            package_type.min_participants
            <= total_students
            <= package_type.max_participants
        ):
            return fail(
                f"Paket {package_type.name} harus berisi "
                f"{package_type.min_participants}–"
                f"{package_type.max_participants} murid. "
                f"Kamu memilih {total_students} murid."
            )

        if status != "active":
            return fail(
                "Slot nonaktif tidak dapat menerima kelompok baru."
            )

    # Siapkan slot.
    if slot is None:
        slot = ScheduleSlot()
        db.session.add(slot)

    slot.instructor_id = instructor_id
    slot.pool_id = pool_id
    slot.day_of_week = day_of_week
    slot.start_time = start_time
    slot.end_time = end_time

    if package_type:
        slot.capacity = package_type.max_participants
    elif slot.capacity is None or slot.capacity < 1:
        slot.capacity = 5

    try:
        # Flush agar slot baru memiliki ID sebelum booking dibuat.
        db.session.flush()

        if selected_packages:
            selected_id_set = set(selected_ids)

            # Periksa konflik jadwal setiap murid.
            for student_package in selected_packages:
                conflict = (
                    ScheduleBooking.query
                    .join(ScheduleSlot)
                    .filter(
                        ScheduleBooking.student_id
                        == student_package.student_id,
                        ScheduleBooking.status == "active",
                        ScheduleSlot.status == "active",
                        ScheduleSlot.id != slot.id,
                        ScheduleSlot.day_of_week == day_of_week,
                        ScheduleSlot.start_time < end_time,
                        ScheduleSlot.end_time > start_time,
                    )
                    .first()
                )

                if conflict:
                    db.session.rollback()
                    return (
                        False,
                        f"Murid {student_package.student.name} "
                        "sudah memiliki jadwal yang bertabrakan.",
                    )

            # Pertahankan booking yang masih dipilih.
            # Booking yang dilepas menjadi inactive agar riwayatnya
            # tidak hilang.
            existing_bookings = ScheduleBooking.query.filter_by(
                schedule_slot_id=slot.id,
                status="active",
            ).all()

            existing_ids = set()

            for booking in existing_bookings:
                if booking.student_package_id in selected_id_set:
                    existing_ids.add(booking.student_package_id)
                else:
                    booking.status = "inactive"

            # Tambahkan booking baru yang belum ada.
            for student_package in selected_packages:
                if student_package.id not in existing_ids:
                    db.session.add(
                        ScheduleBooking(
                            schedule_slot_id=slot.id,
                            student_id=student_package.student_id,
                            student_package_id=student_package.id,
                            status="active",
                        )
                    )

        db.session.commit()
        return True, "Jadwal berhasil disimpan."

    except Exception:
        db.session.rollback()
        return False, "Jadwal gagal disimpan. Tidak ada perubahan yang disimpan."


@schedule_bp.route("/")
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
            ScheduleSlot.id.asc(),
        )
        .all()
    )

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

def render_schedule_form(slot=None):
    instructors = Instructor.query.filter_by(
        status="active"
    ).order_by(Instructor.name.asc()).all()

    pools = Pool.query.filter_by(
        status="active"
    ).order_by(Pool.name.asc()).all()

    package_types = PackageType.query.filter_by(
        status="active"
    ).order_by(PackageType.name.asc()).all()

    student_packages = get_active_student_packages()

    if request.method == "POST":
        selected_package_type_id = request.form.get(
            "package_type_id",
            type=int,
        )
        selected_ids = request.form.getlist("student_package_ids")
    else:
        selected_package_type_id = None
        selected_ids = []

        if slot:
            active_bookings = ScheduleBooking.query.filter_by(
                schedule_slot_id=slot.id,
                status="active",
            ).all()

            selected_ids = [
                str(booking.student_package_id)
                for booking in active_bookings
                if booking.student_package_id is not None
            ]

            if active_bookings and active_bookings[0].student_package:
                selected_package_type_id = (
                    active_bookings[0].student_package.package_type_id
                )

    return render_template(
        "schedules/form.html",
        slot=slot,
        instructors=instructors,
        pools=pools,
        day_names=DAY_NAMES,
        package_types=package_types,
        student_packages=student_packages,
        selected_package_type_id=selected_package_type_id,
        selected_student_package_ids=selected_ids,
    )

@schedule_bp.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        success, message = save_schedule_form()

        if success:
            flash(message, "success")
            return redirect(url_for("schedules.index"))

        flash(message, "error")

    return render_schedule_form()

@schedule_bp.route("/<int:slot_id>/edit", methods=["GET", "POST"])
def edit(slot_id):
    slot = db.get_or_404(ScheduleSlot, slot_id)

    if request.method == "POST":
        success, message = save_schedule_form(slot)

        if success:
            flash(message, "success")
            return redirect(url_for("schedules.index"))

        flash(message, "error")

    return render_schedule_form(slot)

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

@schedule_bp.route("/<int:slot_id>/delete", methods=["POST"])
def delete(slot_id):
    slot = ScheduleSlot.query.get_or_404(slot_id)

    # Cek apakah slot masih memiliki booking
    bookings = ScheduleBooking.query.filter_by(
        schedule_slot_id=slot.id
    ).all()

    if bookings:
        flash(
            "Jadwal tidak bisa dihapus karena sudah memiliki riwayat penempatan murid.",
            "danger"
        )
        return redirect(url_for("schedules.index"))

    db.session.delete(slot)
    db.session.commit()

    flash("Jadwal berhasil dihapus.", "success")
    return redirect(url_for("schedules.index"))