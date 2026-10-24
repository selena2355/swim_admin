
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from app import db
from app.models import Pool


pool_bp = Blueprint("pools", __name__, url_prefix="/pools")


@pool_bp.route("/")
def index():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = Pool.query

    if search:
        query = query.filter(Pool.name.ilike(f"%{search}%"))

    if status_filter in ["active", "inactive"]:
        query = query.filter(Pool.status == status_filter)

    pools = query.order_by(Pool.name.asc()).all()

    return render_template(
        "pools/index.html",
        pools=pools,
        search=search,
        status_filter=status_filter,
    )


@pool_bp.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            flash("Nama kolam wajib diisi.", "error")
            return render_template("pools/form.html", pool=None)

        pool = Pool(
            name=name,
            address=address or None,
            status="active",
        )

        try:
            db.session.add(pool)
            db.session.commit()
            flash("Kolam berhasil ditambahkan.", "success")
            return redirect(url_for("pools.index"))

        except Exception:
            db.session.rollback()
            flash("Kolam gagal disimpan. Silakan periksa kembali.", "error")

    return render_template("pools/form.html", pool=None)


@pool_bp.route("/<int:pool_id>/edit", methods=["GET", "POST"])
def edit(pool_id):
    pool = db.get_or_404(Pool, pool_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            flash("Nama kolam wajib diisi.", "error")
            return render_template("pools/form.html", pool=pool)

        pool.name = name
        pool.address = address or None

        try:
            db.session.commit()
            flash("Informasi kolam berhasil diperbarui.", "success")
            return redirect(url_for("pools.index"))

        except Exception:
            db.session.rollback()
            flash("Perubahan gagal disimpan.", "error")

    return render_template("pools/form.html", pool=pool)


@pool_bp.route("/<int:pool_id>/toggle-status", methods=["POST"])
def toggle_status(pool_id):
    pool = db.get_or_404(Pool, pool_id)

    if pool.status == "active":
        pool.status = "inactive"
        message = f"Kolam {pool.name} berhasil dinonaktifkan."
    else:
        pool.status = "active"
        message = f"Kolam {pool.name} berhasil diaktifkan kembali."

    try:
        db.session.commit()
        flash(message, "success")

    except Exception:
        db.session.rollback()
        flash("Status kolam gagal diperbarui.", "error")

    return redirect(url_for("pools.index"))
