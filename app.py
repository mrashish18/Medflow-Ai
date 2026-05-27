from datetime import datetime, timedelta
import os
import sqlite3

from flask import Flask, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "medflow.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-medflow-secret")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def get_or_create_patient_by_name(name):
    patient_name = name.strip()
    patient = query(
        "SELECT * FROM patients WHERE lower(name) = lower(?) ORDER BY id DESC",
        (patient_name,),
        one=True,
    )
    if patient:
        return patient["id"]

    patient_code = f"MF-{datetime.now().strftime('%H%M%S')}"
    return execute(
        """
        INSERT INTO patients
        (patient_code, name, age, gender, blood_group, phone, address, symptoms, doctor, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patient_code,
            patient_name,
            0,
            "Not specified",
            "",
            "",
            "",
            "Appointment booking",
            "",
            datetime.now().strftime("%Y-%m-%d"),
        ),
    )


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            blood_group TEXT,
            phone TEXT,
            address TEXT,
            symptoms TEXT,
            doctor TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        );

        CREATE TABLE IF NOT EXISTS lab_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            test_name TEXT NOT NULL,
            result TEXT,
            status TEXT NOT NULL,
            uploaded_file TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        );
        """
    )
    db.commit()
    seed_db()


def seed_db():
    db = get_db()
    users = query("SELECT COUNT(*) AS count FROM users", one=True)["count"]
    if users:
        return

    db.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        ("Dr. Ashish Sharma", "admin@medflow.ai", generate_password_hash("medflow123"), "Admin"),
    )

    patients = [
        ("MF-1001", "Aarav Mehta", 34, "Male", "B+", "9876543210", "Sector 14, Gurugram", "Fever, fatigue", "Dr. Nisha Rao"),
        ("MF-1002", "Priya Nair", 28, "Female", "O+", "9876501234", "Indiranagar, Bengaluru", "Throat pain", "Dr. Kabir Sethi"),
        ("MF-1003", "Rohan Gupta", 47, "Male", "A-", "9876512345", "Salt Lake, Kolkata", "High sugar symptoms", "Dr. Nisha Rao"),
        ("MF-1004", "Meera Iyer", 52, "Female", "AB+", "9876523456", "Adyar, Chennai", "Thyroid follow-up", "Dr. Sana Khan"),
        ("MF-1005", "Dev Patel", 19, "Male", "O-", "9876534567", "Vastrapur, Ahmedabad", "Sports injury", "Dr. Kabir Sethi"),
        ("MF-1006", "Ananya Singh", 41, "Female", "A+", "9876545678", "Hazratganj, Lucknow", "Routine health check", "Dr. Sana Khan"),
    ]
    today = datetime.now()
    for index, item in enumerate(patients):
        db.execute(
            """
            INSERT INTO patients
            (patient_code, name, age, gender, blood_group, phone, address, symptoms, doctor, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*item, (today - timedelta(days=index * 2)).strftime("%Y-%m-%d")),
        )

    appointments = [
        (1, "Dr. Nisha Rao", 0, "09:30", "Confirmed", "Initial diagnosis"),
        (2, "Dr. Kabir Sethi", 0, "10:15", "Pending", "ENT review"),
        (3, "Dr. Nisha Rao", 1, "12:00", "Confirmed", "Sugar review"),
        (4, "Dr. Sana Khan", 2, "15:30", "Completed", "Endocrine follow-up"),
        (5, "Dr. Kabir Sethi", 3, "11:45", "Cancelled", "Rescheduled by patient"),
    ]
    for patient_id, doctor, days, appt_time, status, notes in appointments:
        db.execute(
            "INSERT INTO appointments (patient_id, doctor, date, time, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (patient_id, doctor, (today + timedelta(days=days)).strftime("%Y-%m-%d"), appt_time, status, notes),
        )

    reports = [
        (1, "CBC", "WBC mildly elevated", "Processing"),
        (2, "Urine Test", "Awaiting microscopy", "Sample collected"),
        (3, "Blood Sugar", "Fasting: 142 mg/dL", "Completed"),
        (4, "Thyroid", "TSH under review", "Delivered"),
        (6, "Lipid Profile", "LDL borderline high", "Completed"),
    ]
    for patient_id, test_name, result, status in reports:
        db.execute(
            "INSERT INTO lab_reports (patient_id, test_name, result, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (patient_id, test_name, result, status, today.strftime("%Y-%m-%d")),
        )
    db.commit()


@app.before_request
def before_request():
    init_db()


def require_login():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return None


def current_user():
    if "user_id" not in session:
        return None
    return query("SELECT * FROM users WHERE id = ?", (session["user_id"],), one=True)


@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "now": datetime.now()}


@app.route("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = query("SELECT * FROM users WHERE email = ?", (request.form["email"],), one=True)
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        error = "Invalid email or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/dashboard")
def dashboard():
    gate = require_login()
    if gate:
        return gate
    stats = {
        "patients": query("SELECT COUNT(*) AS count FROM patients", one=True)["count"],
        "appointments": query("SELECT COUNT(*) AS count FROM appointments", one=True)["count"],
        "reports": query("SELECT COUNT(*) AS count FROM lab_reports WHERE status != 'Delivered'", one=True)["count"],
        "doctors": 8,
    }
    recent_patients = query("SELECT * FROM patients ORDER BY id DESC LIMIT 5")
    upcoming = query(
        """
        SELECT appointments.*, patients.name AS patient_name
        FROM appointments
        JOIN patients ON patients.id = appointments.patient_id
        ORDER BY date ASC, time ASC
        LIMIT 5
        """
    )
    return render_template("dashboard.html", stats=stats, recent_patients=recent_patients, upcoming=upcoming)


@app.route("/patients", methods=["GET", "POST"])
def patients():
    gate = require_login()
    if gate:
        return gate
    if request.method == "POST":
        code = f"MF-{datetime.now().strftime('%H%M%S')}"
        execute(
            """
            INSERT INTO patients
            (patient_code, name, age, gender, blood_group, phone, address, symptoms, doctor, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                request.form["name"],
                request.form["age"],
                request.form["gender"],
                request.form.get("blood_group"),
                request.form.get("phone"),
                request.form.get("address"),
                request.form.get("symptoms"),
                request.form.get("doctor"),
                datetime.now().strftime("%Y-%m-%d"),
            ),
        )
        return redirect(url_for("patients"))

    search = request.args.get("q", "").strip()
    gender = request.args.get("gender", "")
    sql = "SELECT * FROM patients WHERE 1=1"
    args = []
    if search:
        sql += " AND (name LIKE ? OR patient_code LIKE ? OR phone LIKE ?)"
        args.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if gender:
        sql += " AND gender = ?"
        args.append(gender)
    sql += " ORDER BY id DESC"
    return render_template("patients.html", patients=query(sql, args), search=search, gender=gender)


@app.route("/patients/<int:patient_id>")
def patient_detail(patient_id):
    gate = require_login()
    if gate:
        return gate
    patient = query("SELECT * FROM patients WHERE id = ?", (patient_id,), one=True)
    if patient is None:
        return redirect(url_for("patients"))
    appointments_data = query(
        "SELECT * FROM appointments WHERE patient_id = ? ORDER BY date DESC, time DESC",
        (patient_id,),
    )
    reports_data = query(
        "SELECT * FROM lab_reports WHERE patient_id = ? ORDER BY created_at DESC, id DESC",
        (patient_id,),
    )
    return render_template(
        "patient_detail.html",
        patient=patient,
        appointments=appointments_data,
        reports=reports_data,
    )


@app.route("/patients/delete/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):
    gate = require_login()
    if gate:
        return gate
    execute("DELETE FROM lab_reports WHERE patient_id = ?", (patient_id,))
    execute("DELETE FROM appointments WHERE patient_id = ?", (patient_id,))
    execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    return redirect(url_for("patients"))


@app.route("/appointments", methods=["GET", "POST"])
def appointments():
    gate = require_login()
    if gate:
        return gate
    if request.method == "POST":
        patient_id = get_or_create_patient_by_name(request.form["patient_name"])
        execute(
            "INSERT INTO appointments (patient_id, doctor, date, time, status, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (
                patient_id,
                request.form["doctor"],
                request.form["date"],
                request.form["time"],
                request.form["status"],
                request.form.get("notes"),
            ),
        )
        return redirect(url_for("appointments"))
    data = query(
        """
        SELECT appointments.*, patients.name AS patient_name, patients.patient_code
        FROM appointments
        JOIN patients ON patients.id = appointments.patient_id
        ORDER BY date ASC, time ASC
        """
    )
    status_counts = {
        "Pending": query("SELECT COUNT(*) AS count FROM appointments WHERE status = 'Pending'", one=True)["count"],
        "Confirmed": query("SELECT COUNT(*) AS count FROM appointments WHERE status = 'Confirmed'", one=True)["count"],
        "Completed": query("SELECT COUNT(*) AS count FROM appointments WHERE status = 'Completed'", one=True)["count"],
        "Cancelled": query("SELECT COUNT(*) AS count FROM appointments WHERE status = 'Cancelled'", one=True)["count"],
    }
    doctors = ["Dr. Nisha Rao", "Dr. Kabir Sethi", "Dr. Sana Khan", "Dr. Arjun Menon"]
    week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    calendar_items = {day: [] for day in week_days}
    for index, item in enumerate(data):
        calendar_items[week_days[index % len(week_days)]].append(item)
    return render_template(
        "appointments.html",
        appointments=data,
        patients=query("SELECT id, name FROM patients ORDER BY name"),
        status_counts=status_counts,
        doctors=doctors,
        calendar_items=calendar_items,
    )


@app.route("/lab-reports", methods=["GET", "POST"])
def lab_reports():
    gate = require_login()
    if gate:
        return gate
    if request.method == "POST":
        execute(
            "INSERT INTO lab_reports (patient_id, test_name, result, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                request.form["patient_id"],
                request.form["test_name"],
                request.form.get("result"),
                request.form["status"],
                datetime.now().strftime("%Y-%m-%d"),
            ),
        )
        return redirect(url_for("lab_reports"))
    reports = query(
        """
        SELECT lab_reports.*, patients.name AS patient_name, patients.patient_code
        FROM lab_reports
        JOIN patients ON patients.id = lab_reports.patient_id
        ORDER BY lab_reports.id DESC
        """
    )
    return render_template("lab_reports.html", reports=reports, patients=query("SELECT id, name FROM patients ORDER BY name"))


@app.route("/analytics")
def analytics():
    gate = require_login()
    if gate:
        return gate
    return render_template("analytics.html")


@app.route("/ai-tools")
def ai_tools():
    gate = require_login()
    if gate:
        return gate
    return render_template("ai_tools.html")


@app.route("/settings")
def settings():
    gate = require_login()
    if gate:
        return gate
    return render_template("settings.html")


@app.route("/api/chart-data")
def chart_data():
    gate = require_login()
    if gate:
        return {"error": "Unauthorized"}, 401
    return {
        "patients": [18, 25, 32, 38, 44, 58, 67],
        "appointments": [12, 19, 15, 28, 24, 31, 27],
        "tests": {"CBC": 34, "Blood Sugar": 26, "Urine": 18, "Thyroid": 14, "Lipid": 22},
        "workload": [72, 58, 81, 63],
    }


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
