from datetime import date, datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

STATUSES = ["Applied", "Shortlisted", "Selected", "Rejected"]


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="student")  # student | admin
    roll_no = db.Column(db.String(30), unique=True)
    department = db.Column(db.String(80))
    cgpa = db.Column(db.Float)
    phone = db.Column(db.String(20))
    resume_link = db.Column(db.String(255))
    applications = db.relationship("Application", backref="student", cascade="all, delete-orphan")

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw, method="pbkdf2:sha256")

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self):
        return self.role == "admin"


class Company(db.Model):
    __tablename__ = "companies"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    website = db.Column(db.String(200))
    jobs = db.relationship("Job", backref="company", cascade="all, delete-orphan")


class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    eligibility_cgpa = db.Column(db.Float, nullable=False, default=0.0)
    package_lpa = db.Column(db.Float)
    location = db.Column(db.String(100))
    deadline = db.Column(db.Date, nullable=False)
    posted_on = db.Column(db.DateTime, default=datetime.utcnow)
    applications = db.relationship("Application", backref="job", cascade="all, delete-orphan")

    @property
    def is_open(self):
        return self.deadline >= date.today()


class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (db.UniqueConstraint("student_id", "job_id", name="uq_student_job"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    status = db.Column(db.String(15), nullable=False, default="Applied")
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)
