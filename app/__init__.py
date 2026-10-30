from flask import Flask, app, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "dev-secret-key"
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL"
    )

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    
    from app.models import Student
    from app.models import PackageType
    from app.models import StudentPackage
    from app.models import Pool
    from app.models import Instructor
    from app.models import ScheduleSlot
    from app.models import ScheduleBooking
    
    migrate.init_app(app, db)

    from app.routes.pool_routes import pool_bp
    from app.routes.instructor_routes import instructor_bp
    from app.routes.package_type_routes import package_type_bp
    from app.routes.student_routes import student_bp
    from app.routes.schedule_routes import schedule_bp
    from app.routes.placement_routes import placement_bp

    app.register_blueprint(pool_bp)
    app.register_blueprint(instructor_bp)
    app.register_blueprint(package_type_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(placement_bp)
    
    
    
    
    @app.route("/")
    def index():
        from app.models import (
            Student,
            Instructor,
            Pool,
            PackageType,
            ScheduleSlot,
        )

        return render_template(
            "dashboard.html",
            total_students=Student.query.count(),
            total_instructors=Instructor.query.count(),
            total_pools=Pool.query.count(),
            total_packages=PackageType.query.count(),
            total_slots=ScheduleSlot.query.count(),
        ) 
    
    @app.route("/test-db")
    def test_db():
        from sqlalchemy import text

        with db.engine.connect() as connection:
            result = connection.execute(
                text("SELECT DATABASE()")
            )
            database_name = result.scalar()

        return f"Koneksi database berhasil: {database_name}"

    return app
