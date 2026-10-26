import os
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin or technician
    active = db.Column(db.Boolean, nullable=False, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Issue(db.Model):
    __tablename__ = "issues"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    status = db.Column(db.String(20), nullable=False, default="Pending")
    reporter = db.Column(db.String(80), nullable=False, default="Student")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    # Nullable so existing reports remain valid when upgrading an existing database.
    assigned_technician_id = db.Column(db.Integer, nullable=True)

    @property
    def technician(self):
        if not self.assigned_technician_id:
            return None
        return db.session.get(User, self.assigned_technician_id)

    def as_dict(self):
        technician = self.technician
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "location": self.location, "category": self.category, "priority": self.priority,
            "status": self.status, "reporter": self.reporter,
            "assigned_technician": technician.display_name if technician else None,
            "created_at": self.created_at.isoformat()
        }


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
    default_db = "sqlite:///" + os.path.join(os.path.dirname(__file__), "campus_issues.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", default_db)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    app.User = User
    app.Issue = Issue
    PrometheusMetrics(app, path="/metrics")


    with app.app_context():
        db.create_all()
        # Small, safe schema migration: add assignment field to the existing issues table
        # without deleting the database or any reports already submitted.
        columns = {column["name"] for column in inspect(db.engine).get_columns("issues")}
        if "assigned_technician_id" not in columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE issues ADD COLUMN assigned_technician_id INTEGER"))
        seed_user("admin", os.getenv("CAMPUSCARE_ADMIN_PASSWORD", "AdminDemo123!"), "Campus Administrator", "admin", User)
        seed_user("tech1", os.getenv("CAMPUSCARE_TECH_PASSWORD", "TechDemo123!"), "Ravi Kumar · Technician", "technician", User)
        seed_user("tech2", os.getenv("CAMPUSCARE_TECH2_PASSWORD", "TechDemo456!"), "Priya Sharma · Technician", "technician", User)

    def current_user():
        user_id = session.get("user_id")
        return db.session.get(User, user_id) if user_id else None

    def login_required(role=None):
        def decorator(view):
            @wraps(view)
            def wrapped(*args, **kwargs):
                user = current_user()
                if not user or not user.active:
                    flash("Please sign in to continue.", "error")
                    return redirect(url_for("login", next=request.path))
                if role and user.role != role:
                    flash("You do not have permission to access that page.", "error")
                    return redirect(url_for("dashboard"))
                return view(*args, **kwargs)
            return wrapped
        return decorator

    @app.context_processor
    def inject_user():
        return {"logged_in_user": current_user()}

    @app.get("/")
    def index():
        status_filter = request.args.get("status", "").strip()
        query = Issue.query
        if status_filter in {"Pending", "Assigned", "In Progress", "Resolved"}:
            query = query.filter_by(status=status_filter)
        issues = query.order_by(Issue.created_at.desc()).all()
        counts = {
            "total": Issue.query.count(),
            "pending": Issue.query.filter_by(status="Pending").count(),
            "in_progress": Issue.query.filter_by(status="In Progress").count(),
            "resolved": Issue.query.filter_by(status="Resolved").count(),
        }
        return render_template("index.html", issues=issues, counts=counts, status_filter=status_filter)

    @app.post("/issues")
    def create_issue():
        fields = {
            "title": request.form.get("title", "").strip(),
            "description": request.form.get("description", "").strip(),
            "location": request.form.get("location", "").strip(),
            "category": request.form.get("category", "").strip(),
            "priority": request.form.get("priority", "Medium").strip(),
            "reporter": request.form.get("reporter", "Student").strip() or "Student",
        }
        if not all(fields[k] for k in ("title", "description", "location", "category")):
            flash("Please complete all required fields.", "error")
            return redirect(url_for("index"))
        if len(fields["title"]) > 120 or len(fields["location"]) > 120 or len(fields["reporter"]) > 80:
            flash("One or more fields are too long.", "error")
            return redirect(url_for("index"))
        if fields["priority"] not in {"Low", "Medium", "High"}:
            fields["priority"] = "Medium"
        issue = Issue(**fields)
        db.session.add(issue)
        db.session.commit()
        flash(f"Issue #{issue.id} was reported. The administrator can now assign it to a technician.", "success")
        return redirect(url_for("index"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username, active=True).first()
            if user and user.check_password(password):
                session.clear()
                session["user_id"] = user.id
                flash(f"Welcome, {user.display_name}.", "success")
                return redirect(url_for("dashboard"))
            flash("Username or password is incorrect.", "error")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        flash("You have signed out.", "success")
        return redirect(url_for("index"))

    @app.get("/dashboard")
    @login_required()
    def dashboard():
        user = current_user()
        return redirect(url_for("admin_dashboard" if user.role == "admin" else "technician_dashboard"))

    @app.get("/admin")
    @login_required("admin")
    def admin_dashboard():
        issues = Issue.query.order_by(Issue.created_at.desc()).all()
        technicians = User.query.filter_by(role="technician", active=True).order_by(User.display_name).all()
        counts = {
            "total": Issue.query.count(),
            "unassigned": Issue.query.filter_by(assigned_technician_id=None).count(),
            "in_progress": Issue.query.filter_by(status="In Progress").count(),
            "resolved": Issue.query.filter_by(status="Resolved").count(),
        }
        return render_template("admin.html", issues=issues, technicians=technicians, counts=counts)

    @app.post("/admin/issues/<int:issue_id>/assign")
    @login_required("admin")
    def assign_issue(issue_id):
        issue = db.get_or_404(Issue, issue_id)
        raw_id = request.form.get("technician_id", "").strip()
        if not raw_id:
            issue.assigned_technician_id = None
            issue.status = "Pending"
            flash(f"Issue #{issue.id} is now unassigned.", "success")
        else:
            try:
                technician_id = int(raw_id)
            except ValueError:
                technician_id = -1
            technician = User.query.filter_by(id=technician_id, role="technician", active=True).first()
            if not technician:
                flash("Choose a valid technician.", "error")
                return redirect(url_for("admin_dashboard"))
            issue.assigned_technician_id = technician.id
            if issue.status in {"Pending", "Assigned"}:
                issue.status = "Assigned"
            flash(f"Issue #{issue.id} assigned to {technician.display_name}.", "success")
        db.session.commit()
        return redirect(url_for("admin_dashboard"))

    @app.get("/technician")
    @login_required("technician")
    def technician_dashboard():
        user = current_user()
        issues = Issue.query.filter_by(assigned_technician_id=user.id).order_by(Issue.created_at.desc()).all()
        return render_template("technician.html", issues=issues)

    @app.post("/technician/issues/<int:issue_id>/status")
    @login_required("technician")
    def technician_update_status(issue_id):
        user = current_user()
        issue = db.get_or_404(Issue, issue_id)
        if issue.assigned_technician_id != user.id:
            flash("You can only update issues assigned to you.", "error")
            return redirect(url_for("technician_dashboard"))
        new_status = request.form.get("status", "")
        if new_status not in {"In Progress", "Resolved"}:
            flash("Choose In Progress or Resolved.", "error")
            return redirect(url_for("technician_dashboard"))
        issue.status = new_status
        db.session.commit()
        flash(f"Issue #{issue.id} updated to {new_status}.", "success")
        return redirect(url_for("technician_dashboard"))

    @app.get("/api/issues")
    def api_issues():
        return jsonify([issue.as_dict() for issue in Issue.query.order_by(Issue.created_at.desc()).all()])

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "healthy", "database": "connected"}), 200
        except Exception:
            app.logger.exception("Health check failed")
            return jsonify({"status": "unhealthy", "database": "unavailable"}), 503

    @app.get("/ready")
    def ready():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"ready": True}), 200
        except Exception:
            return jsonify({"ready": False}), 503

    return app


def seed_user(username, password, display_name, role, user_model):
    """Create demo accounts only when missing; existing passwords are not overwritten."""
    if not user_model.query.filter_by(username=username).first():
        user = user_model(username=username, display_name=display_name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()


app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
