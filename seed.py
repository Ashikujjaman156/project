"""Create tables and load demo data. Run: python seed.py"""
from datetime import date, timedelta

from app import app
from models import Application, Company, Job, User, db


def seed():
    db.create_all()
    if User.query.filter_by(email="admin@university.edu").first():
        return
    admin = User(name="Placement Cell", email="admin@university.edu", role="admin")
    admin.set_password("Admin@123")
    db.session.add(admin)

    students = []
    for i, (n, cg, dep) in enumerate([("Ayesha Rahman", 8.9, "CSE"), ("Rafi Ahmed", 7.4, "EEE"),
                                      ("Nusrat Jahan", 9.2, "CSE"), ("Tanvir Hasan", 6.5, "BBA")], 1):
        s = User(name=n, email=f"student{i}@university.edu", role="student", roll_no=f"2026{i:03d}",
                 department=dep, cgpa=cg, phone=f"01700000{i:03d}")
        s.set_password("Student@123")
        students.append(s)
    db.session.add_all(students)

    c1 = Company(name="Nimbus Software", website="https://example.com",
                 description="Cloud tooling company hiring graduate engineers.")
    c2 = Company(name="Meridian Bank", website="https://example.com",
                 description="Retail and corporate banking, management trainee program.")
    c3 = Company(name="GridWorks Energy", website="https://example.com",
                 description="Power systems and smart-grid engineering.")
    db.session.add_all([c1, c2, c3])
    db.session.flush()

    today = date.today()
    jobs = [
        Job(company_id=c1.id, title="Backend Engineer", eligibility_cgpa=7.5, package_lpa=14,
            location="Dhaka", deadline=today + timedelta(days=21),
            description="Build APIs in Python and Go. Strong data-structure fundamentals expected."),
        Job(company_id=c2.id, title="Management Trainee", eligibility_cgpa=6.0, package_lpa=8.5,
            location="Chattogram", deadline=today + timedelta(days=14),
            description="18-month rotational program across retail, credit and operations."),
        Job(company_id=c3.id, title="Graduate Electrical Engineer", eligibility_cgpa=7.0, package_lpa=10,
            location="Dhaka", deadline=today + timedelta(days=30),
            description="Work on substation automation and grid monitoring projects."),
    ]
    db.session.add_all(jobs)
    db.session.flush()
    db.session.add_all([
        Application(student_id=students[0].id, job_id=jobs[0].id, status="Shortlisted"),
        Application(student_id=students[2].id, job_id=jobs[0].id, status="Selected"),
        Application(student_id=students[1].id, job_id=jobs[2].id, status="Applied"),
    ])
    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        seed()
    print("Seeded. Admin: admin@university.edu / Admin@123   Student: student1@university.edu / Student@123")
