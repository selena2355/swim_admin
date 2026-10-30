
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from app import db
from app.models import PackageType


package_type_bp = Blueprint("package_types", __name__, url_prefix="/package-types",)


PACKAGE_OPTIONS = {
    "private_1": {
        "name": "Private 1",
        "class_type": "private",
        "min_participants": 1,
        "max_participants": 1,
        "price": Decimal("250000"),
    },
    "private_2": {
        "name": "Private 2",
        "class_type": "private",
        "min_participants": 2,
        "max_participants": 2,
        "price": Decimal("250000"),
    },
    "rombel": {
        "name": "Rombel",
        "class_type": "rombel",
        "min_participants": 3,
        "max_participants": 5,
        "price": Decimal("220000"),
    },
}


def get_variant(package):
    if package.class_type == "rombel":
        return "rombel"

    if package.max_participants == 2:
        return "private_2"

    return "private_1"


def save_package_form(package=None):
    variant = request.form.get("variant", "").strip()
    service_type = request.form.get("service_type", "").strip()
    price_text = request.form.get("price", "").strip()
    quota_text = request.form.get("session_quota", "4").strip()

    if variant not in PACKAGE_OPTIONS:
        return None, "Pilih jenis paket yang valid."

    if service_type not in ["reguler", "khusus"]:
        return None, "Pilih jenis layanan yang valid."

    try:
        price = Decimal(price_text)
        if not price.is_finite() or price < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        return None, "Harga harus berupa angka nol atau lebih."

    try:
        session_quota = int(quota_text)
        if session_quota < 1:
            raise ValueError
    except ValueError:
        return None, "Kuota sesi minimal 1."

    option = PACKAGE_OPTIONS[variant]
    name = f"{option['name']} {service_type.capitalize()}"
    
    existing = PackageType.query.filter_by(name=name).first()

    if existing and (package is None or existing.id != package.id):
        return None, "Kombinasi tipe paket tersebut sudah tersedia."

    if package is None:
        package = PackageType()

    package.name = name
    package.class_type = option["class_type"]
    package.service_type = service_type
    package.price = price
    package.session_quota = session_quota
    package.min_participants = option["min_participants"]
    package.max_participants = option["max_participants"]

    return package, None


@package_type_bp.route("/")
def index():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = PackageType.query

    if search:
        query = query.filter(PackageType.name.ilike(f"%{search}%"))

    if status_filter in ["active", "inactive"]:
        query = query.filter(PackageType.status == status_filter)

    packages = query.order_by(PackageType.name.asc()).all()

    return render_template(
        "package_types/index.html",
        packages=packages,
        search=search,
        status_filter=status_filter,
    )


@package_type_bp.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        package, error = save_package_form()

        if error:
            flash(error, "error")
            return render_template(
                "package_types/form.html",
                package=None,
                selected_variant=request.form.get("variant", "private_1"),
                selected_service=request.form.get("service_type", "reguler"),
                price_value=request.form.get("price", "250000"),
                quota_value=request.form.get("session_quota", "4"),
            )

        package.status = "active"

        try:
            db.session.add(package)
            db.session.commit()
            flash("Tipe paket berhasil ditambahkan.", "success")
            return redirect(url_for("package_types.index"))

        except Exception:
            db.session.rollback()
            flash(
                "Paket gagal disimpan. Periksa apakah paket yang sama sudah ada.",
                "error",
            )

    return render_template(
        "package_types/form.html",
        package=None,
        selected_variant="private_1",
        selected_service="reguler",
        price_value="250000",
        quota_value="4",
    )


@package_type_bp.route("/<int:package_id>/edit", methods=["GET", "POST"])
def edit(package_id):
    package = db.get_or_404(PackageType, package_id)

    if request.method == "POST":
        updated_package, error = save_package_form(package)

        if error:
            flash(error, "error")
            return render_template(
                "package_types/form.html",
                package=package,
                selected_variant=request.form.get(
                    "variant", get_variant(package)
                ),
                selected_service=request.form.get(
                    "service_type", package.service_type
                ),
                price_value=request.form.get("price", str(package.price)),
                quota_value=request.form.get(
                    "session_quota", str(package.session_quota)
                ),
            )

        try:
            db.session.commit()
            flash("Tipe paket berhasil diperbarui.", "success")
            return redirect(url_for("package_types.index"))

        except Exception:
            db.session.rollback()
            flash("Perubahan paket gagal disimpan.", "error")

    return render_template(
        "package_types/form.html",
        package=package,
        selected_variant=get_variant(package),
        selected_service=package.service_type,
        price_value=str(package.price),
        quota_value=str(package.session_quota),
    )


@package_type_bp.route("/<int:package_id>/toggle-status", methods=["POST"])
def toggle_status(package_id):
    package = db.get_or_404(PackageType, package_id)

    if package.status == "active":
        package.status = "inactive"
        message = f"Paket {package.name} berhasil dinonaktifkan."
    else:
        package.status = "active"
        message = f"Paket {package.name} berhasil diaktifkan kembali."

    try:
        db.session.commit()
        flash(message, "success")

    except Exception:
        db.session.rollback()
        flash("Status paket gagal diperbarui.", "error")

    return redirect(url_for("package_types.index"))
