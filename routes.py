import csv
import io
import time
from datetime import date, datetime
from functools import wraps
from urllib.parse import urlparse

from flask import (Blueprint, Response, abort, current_app, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

import ai
from models import STATUSES, Application, Company, Job, User, db

bp = Blueprint("main", __name__)


# ---------- helpers ----------
def admin_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        if not current_user.is_admin:
            abort(403)
        return f(*a, **k)
    return wrapper


def student_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        if current_user.is_admin:
            abort(403)
        return f(*a, **k)
    return wrapper


def to_float(value, lo=None, hi=None):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        return None
    return v


def safe_next(target):
    return target if target and not urlparse(target).netloc and target.startswith("/") else None


# ---------- public ----------
@bp.route("/")
def index():
    today = date.today()
    stats = {
        "jobs": Job.query.filter(Job.deadline >= today).count(),
        "companies": Company.query.count(),
        "students": User.query.filter_by(role="student").count(),
        "placed": db.session.query(func.count(func.distinct(Application.student_id)))
        .filter(Application.status == "Selected").scalar(),
    }
    latest = (Job.query.filter(Job.deadline >= today)
              .order_by(Job.posted_on.desc()).limit(5).all())
    return render_template("index.html", stats=stats, latest=latest)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        f = request.form
        name, email = f.get("name", "").strip(), f.get("email", "").strip().lower()
        roll, dept = f.get("roll_no", "").strip(), f.get("department", "").strip()
        phone, password = f.get("phone", "").strip(), f.get("password", "")
        cgpa = to_float(f.get("cgpa"), 0, 10)
        errors = []
        if not all([name, email, roll, dept]):
            errors.append("Fill in name, email, roll number and department.")
        if "@" not in email:
            errors.append("Enter a valid email address.")
        if cgpa is None:
            errors.append("CGPA must be a number between 0 and 10.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if User.query.filter_by(email=email).first():
            errors.append("That email is already registered. Log in instead.")
        if roll and User.query.filter_by(roll_no=roll).first():
            errors.append("That roll number is already registered.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html"), 400
        u = User(name=name, email=email, roll_no=roll, department=dept, cgpa=cgpa,
                 phone=phone, role="student")
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash("Account created. Log in to start applying.", "success")
        return redirect(url_for("main.login"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user)
            flash(f"Welcome back, {user.name.split()[0]}.", "success")
            return redirect(safe_next(request.args.get("next")) or url_for("main.dashboard"))
        flash("Email or password is incorrect.", "error")
        return render_template("login.html"), 401
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You're logged out.", "info")
    return redirect(url_for("main.index"))


# ---------- student ----------
@bp.route("/jobs")
@login_required
def jobs():
    today = date.today()
    q = request.args.get("q", "").strip()
    eligible_only = request.args.get("eligible") == "1" and not current_user.is_admin
    query = Job.query.join(Company).filter(Job.deadline >= today)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Job.title.ilike(like), Company.name.ilike(like),
                                 Job.location.ilike(like)))
    if eligible_only:
        query = query.filter(Job.eligibility_cgpa <= (current_user.cgpa or 0))
    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Job.deadline.asc()).paginate(page=page, per_page=8, error_out=False)
    applied_ids = set()
    if not current_user.is_admin:
        applied_ids = {a.job_id for a in current_user.applications}
    return render_template("jobs.html", pagination=pagination, q=q,
                           eligible_only=eligible_only, applied_ids=applied_ids)


@bp.route("/jobs/<int:job_id>")
@login_required
def job_detail(job_id):
    job = db.get_or_404(Job, job_id)
    application = None
    eligible = True
    if not current_user.is_admin:
        application = Application.query.filter_by(student_id=current_user.id, job_id=job.id).first()
        eligible = (current_user.cgpa or 0) >= job.eligibility_cgpa
    return render_template("job_detail.html", job=job, application=application, eligible=eligible)


@bp.route("/jobs/<int:job_id>/apply", methods=["POST"])
@login_required
@student_required
def apply(job_id):
    job = db.get_or_404(Job, job_id)
    if not job.is_open:
        flash("Applications for this job have closed.", "error")
    elif (current_user.cgpa or 0) < job.eligibility_cgpa:
        flash(f"This job needs a CGPA of {job.eligibility_cgpa:.2f} or higher. "
              f"Yours is {current_user.cgpa or 0:.2f}.", "error")
    elif Application.query.filter_by(student_id=current_user.id, job_id=job.id).first():
        flash("You've already applied to this job.", "info")
    else:
        try:
            db.session.add(Application(student_id=current_user.id, job_id=job.id, status="Applied"))
            db.session.commit()
            flash(f"Applied to {job.title} at {job.company.name}.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("You've already applied to this job.", "info")
    return redirect(url_for("main.job_detail", job_id=job.id))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
@student_required
def profile():
    if request.method == "POST":
        cgpa = to_float(request.form.get("cgpa"), 0, 10)
        if cgpa is None:
            flash("CGPA must be a number between 0 and 10.", "error")
            return render_template("profile.html"), 400
        current_user.cgpa = cgpa
        current_user.phone = request.form.get("phone", "").strip()
        current_user.department = request.form.get("department", "").strip()
        current_user.resume_link = request.form.get("resume_link", "").strip()
        db.session.commit()
        flash("Profile saved.", "success")
        return redirect(url_for("main.profile"))
    return render_template("profile.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("main.admin_dashboard"))
    apps = (Application.query.filter_by(student_id=current_user.id)
            .order_by(Application.applied_on.desc()).all())
    counts = {s: sum(1 for a in apps if a.status == s) for s in STATUSES}
    return render_template("dashboard.html", apps=apps, counts=counts)


# ---------- admin ----------
@bp.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    jobs = Job.query.order_by(Job.deadline.desc()).all()
    companies = Company.query.order_by(Company.name).all()
    total_apps = Application.query.count()
    return render_template("admin_dashboard.html", jobs=jobs, companies=companies,
                           total_apps=total_apps)


@bp.route("/admin/company/new", methods=["GET", "POST"])
@login_required
@admin_required
def add_company():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Company name is required.", "error")
        elif Company.query.filter(func.lower(Company.name) == name.lower()).first():
            flash("A company with that name already exists.", "error")
        else:
            db.session.add(Company(name=name, description=request.form.get("description", "").strip(),
                                   website=request.form.get("website", "").strip()))
            db.session.commit()
            flash(f"{name} added. You can post a job for it now.", "success")
            return redirect(url_for("main.post_job"))
        return render_template("add_company.html"), 400
    return render_template("add_company.html")


def _save_job(job):
    f = request.form
    company = db.session.get(Company, f.get("company_id", type=int) or 0)
    cgpa = to_float(f.get("eligibility_cgpa"), 0, 10)
    package = to_float(f.get("package_lpa"), 0)
    try:
        deadline = datetime.strptime(f.get("deadline", ""), "%Y-%m-%d").date()
    except ValueError:
        deadline = None
    errors = []
    if not company:
        errors.append("Choose a company.")
    if not f.get("title", "").strip():
        errors.append("Job title is required.")
    if cgpa is None:
        errors.append("Minimum CGPA must be between 0 and 10.")
    if package is None:
        errors.append("Package must be a positive number (LPA).")
    if deadline is None:
        errors.append("Enter a valid application deadline.")
    if errors:
        for e in errors:
            flash(e, "error")
        return False
    job.company_id = company.id
    job.title = f["title"].strip()
    job.description = f.get("description", "").strip()
    job.eligibility_cgpa, job.package_lpa = cgpa, package
    job.location = f.get("location", "").strip()
    job.deadline = deadline
    db.session.add(job)
    db.session.commit()
    return True


@bp.route("/admin/job/new", methods=["GET", "POST"])
@login_required
@admin_required
def post_job():
    companies = Company.query.order_by(Company.name).all()
    if not companies:
        flash("Add a company before posting a job.", "info")
        return redirect(url_for("main.add_company"))
    if request.method == "POST":
        job = Job()
        if _save_job(job):
            flash("Job posted. Students can see it now.", "success")
            return redirect(url_for("main.admin_dashboard"))
        return render_template("job_form.html", companies=companies, job=None), 400
    return render_template("job_form.html", companies=companies, job=None)


@bp.route("/admin/job/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_job(job_id):
    job = db.get_or_404(Job, job_id)
    companies = Company.query.order_by(Company.name).all()
    if request.method == "POST":
        if _save_job(job):
            flash("Job updated.", "success")
            return redirect(url_for("main.admin_dashboard"))
        db.session.rollback()
        return render_template("job_form.html", companies=companies, job=job), 400
    return render_template("job_form.html", companies=companies, job=job)


@bp.route("/admin/job/<int:job_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_job(job_id):
    job = db.get_or_404(Job, job_id)
    db.session.delete(job)
    db.session.commit()
    flash(f"Deleted {job.title}, including its applications.", "info")
    return redirect(url_for("main.admin_dashboard"))


@bp.route("/admin/job/<int:job_id>/applicants")
@login_required
@admin_required
def applicants(job_id):
    job = db.get_or_404(Job, job_id)
    status = request.args.get("status")
    apps = Application.query.filter_by(job_id=job.id)
    if status in STATUSES:
        apps = apps.filter_by(status=status)
    apps = apps.join(User).order_by(User.cgpa.desc()).all()
    return render_template("applicants.html", job=job, apps=apps, status=status)


@bp.route("/admin/application/<int:app_id>/status", methods=["POST"])
@login_required
@admin_required
def update_status(app_id):
    application = db.get_or_404(Application, app_id)
    new = request.form.get("status")
    if new not in STATUSES:
        abort(400, "Unknown status.")
    application.status = new
    db.session.commit()
    flash(f"{application.student.name} is now {new}.", "success")
    return redirect(url_for("main.applicants", job_id=application.job_id))


@bp.route("/admin/job/<int:job_id>/export.csv")
@login_required
@admin_required
def export_applicants(job_id):
    job = db.get_or_404(Job, job_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Name", "Roll no", "Email", "Department", "CGPA", "Phone", "Resume", "Status", "Applied on"])
    for a in job.applications:
        s = a.student
        w.writerow([s.name, s.roll_no, s.email, s.department, s.cgpa, s.phone, s.resume_link,
                    a.status, a.applied_on.strftime("%Y-%m-%d %H:%M")])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=applicants_job_{job.id}.csv"})


# ---------- AI assistant ----------
@bp.route("/assistant")
def assistant_page():
    return render_template("assistant.html")


@bp.route("/assistant/chat", methods=["POST"])
def assistant_chat():
    window, limit = 600, current_app.config["AI_RATE_LIMIT"]
    key = f"u{current_user.id}" if current_user.is_authenticated else f"ip{request.remote_addr}"
    hits = current_app.extensions.setdefault("ai_hits", {})
    recent = [t for t in hits.get(key, []) if time.time() - t < window]
    if len(recent) >= limit:
        return jsonify(error="You’re sending messages quickly. Please wait a few minutes and try again."), 429
    history = ai.clean_messages((request.get_json(silent=True) or {}).get("messages"))
    if not history:
        return jsonify(error="Type a message first."), 400
    recent.append(time.time())
    hits[key] = recent
    try:
        return jsonify(reply=ai.reply(history, current_user))
    except ai.AssistantError as e:
        current_app.logger.warning("AI unavailable: %s", e)
        if current_app.config.get("AI_FALLBACK", True):
            return jsonify(reply=ai.fallback_reply(history, current_user), offline=True)
        return jsonify(error=str(e)), (503 if isinstance(e, ai.AssistantUnavailable) else 502)
