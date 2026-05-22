from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "teamflow-secret-key-change-later")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///teamflow.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Railway/Postgres compatibility if DATABASE_URL starts with postgres://
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config["SQLALCHEMY_DATABASE_URI"].replace("postgres://", "postgresql://", 1)

db = SQLAlchemy(app)

# -------------------- DATABASE MODELS --------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Member")  # Admin / Member

    created_projects = db.relationship("Project", backref="creator", lazy=True)
    assigned_tasks = db.relationship("Task", foreign_keys="Task.assigned_to", backref="assignee", lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    tasks = db.relationship("Task", backref="project", lazy=True, cascade="all, delete-orphan")
    members = db.relationship("ProjectMember", backref="project", lazy=True, cascade="all, delete-orphan")

class ProjectMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    user = db.relationship("User", backref="project_memberships")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Pending")
    due_date = db.Column(db.Date, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    creator = db.relationship("User", foreign_keys=[created_by], backref="tasks_created")

# -------------------- HELPERS --------------------

def current_user():
    if "user_id" not in session:
        return None
    return User.query.get(session["user_id"])

def login_required():
    if "user_id" not in session:
        flash("Please login first.", "error")
        return False
    return True

def admin_required():
    user = current_user()
    if not user or user.role != "Admin":
        flash("Only Admin can perform this action.", "error")
        return False
    return True

@app.context_processor
def inject_user():
    return {"user": current_user()}

# -------------------- AUTH ROUTES --------------------

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "Member")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("signup"))

        if role not in ["Admin", "Member"]:
            role = "Member"

        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "error")
            return redirect(url_for("login"))

        new_user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Signup successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

        session["user_id"] = user.id
        session["role"] = user.role
        flash("Login successful.", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))

# -------------------- DASHBOARD --------------------

@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))

    user = current_user()

    if user.role == "Admin":
        tasks = Task.query.all()
        projects_count = Project.query.count()
        users_count = User.query.count()
    else:
        tasks = Task.query.filter_by(assigned_to=user.id).all()
        project_ids = [pm.project_id for pm in ProjectMember.query.filter_by(user_id=user.id).all()]
        projects_count = len(project_ids)
        users_count = None

    today = date.today()
    total_tasks = len(tasks)
    pending = len([t for t in tasks if t.status == "Pending"])
    in_progress = len([t for t in tasks if t.status == "In Progress"])
    completed = len([t for t in tasks if t.status == "Completed"])
    overdue = len([t for t in tasks if t.due_date < today and t.status != "Completed"])

    recent_tasks = sorted(tasks, key=lambda x: x.due_date)[:6]

    return render_template(
        "dashboard.html",
        total_tasks=total_tasks,
        pending=pending,
        in_progress=in_progress,
        completed=completed,
        overdue=overdue,
        projects_count=projects_count,
        users_count=users_count,
        recent_tasks=recent_tasks
    )

# -------------------- PROJECT ROUTES --------------------

@app.route("/projects")
def projects():
    if not login_required():
        return redirect(url_for("login"))

    user = current_user()

    if user.role == "Admin":
        all_projects = Project.query.order_by(Project.id.desc()).all()
    else:
        memberships = ProjectMember.query.filter_by(user_id=user.id).all()
        project_ids = [m.project_id for m in memberships]
        all_projects = Project.query.filter(Project.id.in_(project_ids)).all() if project_ids else []

    members = User.query.filter_by(role="Member").all()

    return render_template("projects.html", projects=all_projects, members=members)

@app.route("/projects/create", methods=["POST"])
def create_project():
    if not admin_required():
        return redirect(url_for("projects"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Project name is required.", "error")
        return redirect(url_for("projects"))

    project = Project(name=name, description=description, created_by=session["user_id"])
    db.session.add(project)
    db.session.commit()

    flash("Project created successfully.", "success")
    return redirect(url_for("projects"))

@app.route("/projects/<int:project_id>/add-member", methods=["POST"])
def add_member(project_id):
    if not admin_required():
        return redirect(url_for("projects"))

    user_id = request.form.get("user_id")

    if not user_id:
        flash("Please select a member.", "error")
        return redirect(url_for("projects"))

    exists = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
    if exists:
        flash("Member already exists in this project.", "error")
        return redirect(url_for("projects"))

    member = ProjectMember(project_id=project_id, user_id=int(user_id))
    db.session.add(member)
    db.session.commit()

    flash("Member added to project.", "success")
    return redirect(url_for("projects"))

@app.route("/projects/<int:project_id>/delete", methods=["POST"])
def delete_project(project_id):
    if not admin_required():
        return redirect(url_for("projects"))

    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()

    flash("Project deleted successfully.", "success")
    return redirect(url_for("projects"))

# -------------------- TASK ROUTES --------------------

@app.route("/tasks")
def tasks():
    if not login_required():
        return redirect(url_for("login"))

    user = current_user()

    if user.role == "Admin":
        all_tasks = Task.query.order_by(Task.due_date.asc()).all()
        projects = Project.query.all()
        members = User.query.filter_by(role="Member").all()
    else:
        all_tasks = Task.query.filter_by(assigned_to=user.id).order_by(Task.due_date.asc()).all()
        projects = []
        members = []

    return render_template("tasks.html", tasks=all_tasks, projects=projects, members=members)

@app.route("/tasks/create", methods=["POST"])
def create_task():
    if not admin_required():
        return redirect(url_for("tasks"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    project_id = request.form.get("project_id")
    assigned_to = request.form.get("assigned_to")
    due_date_str = request.form.get("due_date")

    if not title or not project_id or not assigned_to or not due_date_str:
        flash("Title, project, assigned member and due date are required.", "error")
        return redirect(url_for("tasks"))

    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid due date format.", "error")
        return redirect(url_for("tasks"))

    task = Task(
        title=title,
        description=description,
        project_id=int(project_id),
        assigned_to=int(assigned_to),
        due_date=due_date,
        created_by=session["user_id"]
    )

    db.session.add(task)
    db.session.commit()

    flash("Task created and assigned successfully.", "success")
    return redirect(url_for("tasks"))

@app.route("/tasks/<int:task_id>/status", methods=["POST"])
def update_task_status(task_id):
    if not login_required():
        return redirect(url_for("login"))

    task = Task.query.get_or_404(task_id)
    user = current_user()
    new_status = request.form.get("status")

    if new_status not in ["Pending", "In Progress", "Completed"]:
        flash("Invalid task status.", "error")
        return redirect(url_for("tasks"))

    if user.role == "Admin" or task.assigned_to == user.id:
        task.status = new_status
        db.session.commit()
        flash("Task status updated.", "success")
    else:
        flash("You can update only your assigned tasks.", "error")

    return redirect(url_for("tasks"))

@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    if not admin_required():
        return redirect(url_for("tasks"))

    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()

    flash("Task deleted successfully.", "success")
    return redirect(url_for("tasks"))

# -------------------- REST API ROUTES --------------------

@app.route("/api/tasks", methods=["GET"])
def api_get_tasks():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    user = current_user()
    if user.role == "Admin":
        tasks = Task.query.all()
    else:
        tasks = Task.query.filter_by(assigned_to=user.id).all()

    data = []
    for task in tasks:
        data.append({
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "project": task.project.name,
            "assigned_to": task.assignee.name,
            "status": task.status,
            "due_date": task.due_date.strftime("%Y-%m-%d")
        })

    return jsonify(data)

@app.route("/api/projects", methods=["GET"])
def api_get_projects():
    if not login_required():
        return jsonify({"error": "Unauthorized"}), 401

    projects = Project.query.all()
    data = [{"id": p.id, "name": p.name, "description": p.description} for p in projects]
    return jsonify(data)

# -------------------- INIT DB --------------------

@app.before_request
def create_tables():
    db.create_all()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
