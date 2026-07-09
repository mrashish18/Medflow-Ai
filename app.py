from datetime import datetime, timedelta
from functools import wraps
import os
import sqlite3

from flask import Flask, abort, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "medflow.db")

ROLE_SUPER_ADMIN = "super_admin"
ROLE_DOCTOR = "doctor"
ROLE_LAB_TECH = "lab_tech"
ROLE_RECEPTIONIST = "receptionist"
ROLE_PATIENT = "patient"

ROLE_LABELS = {
    ROLE_SUPER_ADMIN: "Super Admin",
    ROLE_DOCTOR: "Doctor",
    ROLE_LAB_TECH: "Laboratory Technician",
    ROLE_RECEPTIONIST: "Receptionist",
    ROLE_PATIENT: "Patient",
}


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-medicore-secret")


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


def table_columns(table_name):
    return {row[1] for row in get_db().execute(f"PRAGMA table_info({table_name})").fetchall()}


def add_column_if_missing(table_name, column_name, column_sql):
    if column_name not in table_columns(table_name):
        get_db().execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            doctor_name TEXT,
            patient_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT UNIQUE,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
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
            assigned_doctor_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(assigned_doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor TEXT NOT NULL,
            doctor_id INTEGER,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE IF NOT EXISTS lab_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            test_name TEXT NOT NULL,
            result TEXT,
            status TEXT NOT NULL,
            uploaded_file TEXT,
            created_at TEXT NOT NULL,
            assigned_to_user_id INTEGER,
            doctor TEXT,
            doctor_id INTEGER,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id),
            FOREIGN KEY(assigned_to_user_id) REFERENCES users(id)
        );
        """
    )
    db.commit()
    migrate_schema()
    seed_db()


def migrate_schema():
    db = get_db()
    add_column_if_missing("users", "role", "role TEXT NOT NULL DEFAULT 'patient'")
    add_column_if_missing("users", "doctor_name", "doctor_name TEXT")
    add_column_if_missing("users", "patient_id", "patient_id INTEGER")
    add_column_if_missing("doctors", "specialization", "specialization TEXT DEFAULT 'General Medicine'")
    add_column_if_missing("doctors", "department", "department TEXT DEFAULT 'General Medicine'")
    add_column_if_missing("doctors", "email", "email TEXT")
    add_column_if_missing("doctors", "user_id", "user_id INTEGER")
    add_column_if_missing("patients", "assigned_doctor_id", "assigned_doctor_id INTEGER")
    add_column_if_missing("appointments", "doctor_id", "doctor_id INTEGER")
    add_column_if_missing("lab_reports", "assigned_to_user_id", "assigned_to_user_id INTEGER")
    add_column_if_missing("lab_reports", "doctor", "doctor TEXT")
    add_column_if_missing("lab_reports", "doctor_id", "doctor_id INTEGER")
    db.execute("UPDATE users SET role = ? WHERE role IN ('Admin', 'admin')", (ROLE_SUPER_ADMIN,))
    db.commit()


def upsert_user(name, email, password, role, doctor_name=None, patient_id=None):
    user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
    if user:
        execute(
            "UPDATE users SET name = ?, role = ?, doctor_name = ?, patient_id = ? WHERE email = ?",
            (name, role, doctor_name, patient_id, email),
        )
        return query("SELECT * FROM users WHERE email = ?", (email,), one=True)["id"]
    password_hash = generate_password_hash(password)
    return execute(
        """
        INSERT INTO users (name, email, password_hash, role, doctor_name, patient_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, email, password_hash, role, doctor_name, patient_id),
    )


def upsert_doctor(name, email, specialization, department):
    doctor = query("SELECT * FROM doctors WHERE email = ?", (email,), one=True)
    user_id = upsert_user(name, email, "medicore123", ROLE_DOCTOR, doctor_name=name)
    if doctor:
        execute(
            "UPDATE doctors SET name = ?, specialization = ?, department = ?, user_id = ? WHERE email = ?",
            (name, specialization, department, user_id, email),
        )
        return query("SELECT * FROM doctors WHERE email = ?", (email,), one=True)
    doctor_id = execute(
        "INSERT INTO doctors (name, specialization, department, email, user_id) VALUES (?, ?, ?, ?, ?)",
        (name, specialization, department, email, user_id),
    )
    return query("SELECT * FROM doctors WHERE id = ?", (doctor_id,), one=True)


def seed_db():
    today = datetime.now()
    upsert_user("Dr. Ashish Sharma", "admin@medicore.ai", "medicore123", ROLE_SUPER_ADMIN)
    receptionist_id = upsert_user("Riya Reception", "reception@medicore.ai", "medicore123", ROLE_RECEPTIONIST)
    lab_user_id = upsert_user("Laksh Lab", "lab@medicore.ai", "medicore123", ROLE_LAB_TECH)

    doctor_specs = [
        ("Dr. Nisha Rao", "nisha.rao@medicore.ai", "Cardiology", "Cardiology"),
        ("Dr. Kabir Sethi", "kabir.sethi@medicore.ai", "Neurology", "Neurology"),
        ("Dr. Sana Khan", "sana.khan@medicore.ai", "Orthopedics", "Orthopedics"),
        ("Dr. Arjun Menon", "arjun.menon@medicore.ai", "Pediatrics", "Pediatrics"),
        ("Dr. Meera Iyer", "meera.iyer@medicore.ai", "General Medicine", "General Medicine"),
    ]
    doctors = [upsert_doctor(*doctor) for doctor in doctor_specs]

    patients = [
        ("Aarav Mehta", 34, "Male", "B+", "Fever, fatigue"),
        ("Priya Nair", 28, "Female", "O+", "Throat pain"),
        ("Rohan Gupta", 47, "Male", "A-", "High sugar symptoms"),
        ("Meera Shah", 52, "Female", "AB+", "Thyroid follow-up"),
        ("Dev Patel", 19, "Male", "O-", "Sports injury"),
        ("Ananya Singh", 41, "Female", "A+", "Routine health check"),
        ("Ishaan Verma", 63, "Male", "B-", "Chest discomfort"),
        ("Kavya Reddy", 12, "Female", "O+", "Fever"),
        ("Nikhil Joshi", 55, "Male", "A+", "Back pain"),
        ("Sara Khan", 31, "Female", "B+", "Migraine"),
        ("Vivaan Rao", 6, "Male", "AB-", "Vaccination"),
        ("Tara Das", 44, "Female", "O-", "Follow-up"),
        ("Aditya Bose", 38, "Male", "A-", "BP review"),
        ("Maya Kapoor", 25, "Female", "B-", "Allergy"),
        ("Kunal Jain", 49, "Male", "O+", "Knee pain"),
        ("Diya Menon", 9, "Female", "A+", "Cough"),
        ("Om Prakash", 70, "Male", "AB+", "Cardiac review"),
        ("Leela Nair", 60, "Female", "B+", "Diabetes care"),
        ("Yash Malhotra", 22, "Male", "O-", "Fracture review"),
        ("Noor Ali", 36, "Female", "A+", "Neurology follow-up"),
    ]

    patient_ids = []
    for index, patient_data in enumerate(patients, start=1):
        doctor = doctors[(index - 1) % len(doctors)]
        code = f"MF-{1000 + index}"
        patient = query("SELECT * FROM patients WHERE patient_code = ?", (code,), one=True)
        values = (
            code,
            patient_data[0],
            patient_data[1],
            patient_data[2],
            patient_data[3],
            f"98765{index:05d}",
            f"MediCore Demo Address {index}",
            patient_data[4],
            doctor["name"],
            doctor["id"],
            (today - timedelta(days=index)).strftime("%Y-%m-%d"),
        )
        if patient:
            patient_id = patient["id"]
            execute(
                """
                UPDATE patients
                SET patient_code = ?, name = ?, age = ?, gender = ?, blood_group = ?, phone = ?,
                    address = ?, symptoms = ?, doctor = ?, assigned_doctor_id = ?, created_at = ?
                WHERE id = ?
                """,
                (*values, patient_id),
            )
        else:
            patient_id = execute(
                """
                INSERT INTO patients
                (patient_code, name, age, gender, blood_group, phone, address, symptoms, doctor, assigned_doctor_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
        patient_ids.append(patient_id)
        upsert_user(patient_data[0], f"patient{index}@medicore.ai", "medicore123", ROLE_PATIENT, patient_id=patient_id)

    for row in query("SELECT id FROM patients WHERE assigned_doctor_id IS NULL OR assigned_doctor_id = ''"):
        doctor = doctors[(row["id"] - 1) % len(doctors)]
        execute("UPDATE patients SET assigned_doctor_id = ?, doctor = ? WHERE id = ?", (doctor["id"], doctor["name"], row["id"]))

    if query("SELECT COUNT(*) AS count FROM appointments", one=True)["count"] < 12:
        statuses = ["Confirmed", "Pending", "Completed", "Cancelled"]
        for index, patient_id in enumerate(patient_ids[:12]):
            patient = query("SELECT * FROM patients WHERE id = ?", (patient_id,), one=True)
            execute(
                "INSERT INTO appointments (patient_id, doctor, doctor_id, date, time, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    patient_id,
                    patient["doctor"],
                    patient["assigned_doctor_id"],
                    (today + timedelta(days=index % 6)).strftime("%Y-%m-%d"),
                    f"{9 + (index % 8):02d}:30",
                    statuses[index % len(statuses)],
                    "Demo appointment",
                ),
            )

    for row in query("SELECT appointments.id, patients.doctor, patients.assigned_doctor_id FROM appointments JOIN patients ON patients.id = appointments.patient_id WHERE appointments.doctor_id IS NULL"):
        execute("UPDATE appointments SET doctor = ?, doctor_id = ? WHERE id = ?", (row["doctor"], row["assigned_doctor_id"], row["id"]))

    if query("SELECT COUNT(*) AS count FROM lab_reports", one=True)["count"] < 15:
        tests = ["CBC", "Blood Sugar", "Urine Test", "Thyroid", "Lipid Profile"]
        statuses = ["Sample collected", "Processing", "Completed", "Delivered"]
        for index, patient_id in enumerate(patient_ids[:15]):
            patient = query("SELECT * FROM patients WHERE id = ?", (patient_id,), one=True)
            execute(
                """
                INSERT INTO lab_reports
                (patient_id, test_name, result, status, created_at, assigned_to_user_id, doctor, doctor_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    tests[index % len(tests)],
                    "Demo result pending clinical review",
                    statuses[index % len(statuses)],
                    (today - timedelta(days=index % 5)).strftime("%Y-%m-%d"),
                    lab_user_id,
                    patient["doctor"],
                    patient["assigned_doctor_id"],
                ),
            )

    for row in query("SELECT lab_reports.id, patients.doctor, patients.assigned_doctor_id FROM lab_reports JOIN patients ON patients.id = lab_reports.patient_id WHERE lab_reports.doctor_id IS NULL OR lab_reports.assigned_to_user_id IS NULL"):
        execute(
            "UPDATE lab_reports SET doctor = ?, doctor_id = ?, assigned_to_user_id = COALESCE(assigned_to_user_id, ?) WHERE id = ?",
            (row["doctor"], row["assigned_doctor_id"], lab_user_id, row["id"]),
        )


@app.before_request
def before_request():
    if not app.config.get("_DB_READY"):
        init_db()
        app.config["_DB_READY"] = True


def current_user():
    if "user_id" not in session:
        return None
    return query("SELECT * FROM users WHERE id = ?", (session["user_id"],), one=True)


def role_label(role):
    return ROLE_LABELS.get(role, role.replace("_", " ").title())


def doctor_id_for_user(user):
    if not user:
        return None
    doctor = query("SELECT id FROM doctors WHERE user_id = ? OR name = ?", (user["id"], user["doctor_name"] or ""), one=True)
    return doctor["id"] if doctor else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def roles_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user or user["role"] not in allowed_roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


admin_required = roles_required(ROLE_SUPER_ADMIN)
doctor_required = roles_required(ROLE_SUPER_ADMIN, ROLE_DOCTOR)
lab_required = roles_required(ROLE_SUPER_ADMIN, ROLE_LAB_TECH)
reception_required = roles_required(ROLE_SUPER_ADMIN, ROLE_RECEPTIONIST)
patient_required = roles_required(ROLE_PATIENT)


def redirect_for_user(user):
    return redirect(url_for("dashboard"))


def nav_items_for(user):
    if not user:
        return []
    if user["role"] == ROLE_SUPER_ADMIN:
        return [
            ("Dashboard", "bi-grid-1x2", "dashboard"),
            ("Patients", "bi-people", "patients"),
            ("Appointments", "bi-calendar2-week", "appointments"),
            ("Lab Reports", "bi-file-earmark-medical", "lab_reports"),
            ("Analytics", "bi-graph-up-arrow", "analytics"),
            ("Settings", "bi-sliders2", "settings"),
        ]
    if user["role"] == ROLE_DOCTOR:
        return [
            ("Dashboard", "bi-grid-1x2", "dashboard"),
            ("My Patients", "bi-people", "patients"),
            ("Appointments", "bi-calendar2-week", "appointments"),
            ("Lab Reports", "bi-file-earmark-medical", "lab_reports"),
            ("Settings", "bi-sliders2", "settings"),
        ]
    if user["role"] == ROLE_LAB_TECH:
        return [
            ("Dashboard", "bi-grid-1x2", "dashboard"),
            ("Assigned Reports", "bi-file-earmark-medical", "lab_reports"),
            ("Settings", "bi-sliders2", "settings"),
        ]
    if user["role"] == ROLE_RECEPTIONIST:
        return [
            ("Dashboard", "bi-grid-1x2", "dashboard"),
            ("Patients", "bi-people", "patients"),
            ("Appointments", "bi-calendar2-week", "appointments"),
            ("Settings", "bi-sliders2", "settings"),
        ]
    return [
        ("Dashboard", "bi-grid-1x2", "dashboard"),
        ("My Profile", "bi-person", "patients"),
        ("My Appointments", "bi-calendar2-week", "appointments"),
        ("My Reports", "bi-file-earmark-medical", "lab_reports"),
        ("Settings", "bi-sliders2", "settings"),
    ]


def patient_scope_sql(user, prefix=""):
    table = f"{prefix}." if prefix else ""
    if user["role"] in (ROLE_SUPER_ADMIN, ROLE_RECEPTIONIST):
        return "1=1", []
    if user["role"] == ROLE_DOCTOR:
        return f"{table}assigned_doctor_id = ?", [doctor_id_for_user(user) or -1]
    if user["role"] == ROLE_PATIENT:
        return f"{table}id = ?", [user["patient_id"] or -1]
    return f"{table}id IN (SELECT patient_id FROM lab_reports WHERE assigned_to_user_id = ?)", [user["id"]]


def can_access_patient(user, patient_id):
    where_sql, args = patient_scope_sql(user)
    return query(f"SELECT id FROM patients WHERE id = ? AND {where_sql}", [patient_id, *args], one=True) is not None


def report_progress_width(status):
    if status == "Delivered":
        return 100
    if status == "Completed":
        return 78
    if status == "Processing":
        return 52
    return 24


@app.context_processor
def inject_globals():
    user = current_user()
    return {
        "current_user": user,
        "nav_items": nav_items_for(user),
        "now": datetime.now(),
        "role_label": role_label,
    }


@app.errorhandler(403)
def forbidden(_error):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.route("/")
def landing():
    user = current_user()
    if user:
        return redirect_for_user(user)
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = query("SELECT * FROM users WHERE lower(email) = lower(?)", (request.form["email"],), one=True)
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session.clear()
            session["user_id"] = user["id"]
            return redirect_for_user(user)
        error = "Invalid email or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    today = datetime.now().strftime("%Y-%m-%d")
    patient_where, patient_args = patient_scope_sql(user)
    appointment_where = "1=1"
    appointment_args = []
    report_where = "1=1"
    report_args = []

    if user["role"] == ROLE_DOCTOR:
        appointment_where = "appointments.doctor_id = ?"
        appointment_args = [doctor_id_for_user(user) or -1]
        report_where = "lab_reports.doctor_id = ?"
        report_args = [doctor_id_for_user(user) or -1]
    elif user["role"] == ROLE_PATIENT:
        appointment_where = "appointments.patient_id = ?"
        appointment_args = [user["patient_id"] or -1]
        report_where = "lab_reports.patient_id = ?"
        report_args = [user["patient_id"] or -1]
    elif user["role"] == ROLE_LAB_TECH:
        appointment_where = "0=1"
        report_where = "lab_reports.assigned_to_user_id = ?"
        report_args = [user["id"]]
    elif user["role"] == ROLE_RECEPTIONIST:
        report_where = "0=1"

    stats = {
        "patients": query(f"SELECT COUNT(*) AS count FROM patients WHERE {patient_where}", patient_args, one=True)["count"],
        "appointments": query(f"SELECT COUNT(*) AS count FROM appointments WHERE {appointment_where}", appointment_args, one=True)["count"],
        "reports": query(f"SELECT COUNT(*) AS count FROM lab_reports WHERE status NOT IN ('Delivered', 'Completed') AND {report_where}", report_args, one=True)["count"],
        "doctors": query("SELECT COUNT(*) AS count FROM doctors", one=True)["count"],
    }
    recent_patients = query(f"SELECT * FROM patients WHERE {patient_where} ORDER BY id DESC LIMIT 5", patient_args)
    upcoming = query(
        f"""
        SELECT appointments.*, patients.name AS patient_name
        FROM appointments
        JOIN patients ON patients.id = appointments.patient_id
        WHERE {appointment_where}
        ORDER BY date ASC, time ASC
        LIMIT 5
        """,
        appointment_args,
    )
    return render_template("dashboard.html", stats=stats, recent_patients=recent_patients, upcoming=upcoming)


@app.route("/patients", methods=["GET", "POST"])
@roles_required(ROLE_SUPER_ADMIN, ROLE_DOCTOR, ROLE_RECEPTIONIST, ROLE_PATIENT)
def patients():
    user = current_user()
    if request.method == "POST":
        if user["role"] not in (ROLE_SUPER_ADMIN, ROLE_RECEPTIONIST):
            abort(403)
        doctor_id = request.form.get("assigned_doctor_id")
        doctor = query("SELECT * FROM doctors WHERE id = ?", (doctor_id,), one=True) if doctor_id else None
        code = f"MF-{datetime.now().strftime('%H%M%S')}"
        execute(
            """
            INSERT INTO patients
            (patient_code, name, age, gender, blood_group, phone, address, symptoms, doctor, assigned_doctor_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                doctor["name"] if doctor else request.form.get("doctor"),
                doctor["id"] if doctor else None,
                datetime.now().strftime("%Y-%m-%d"),
            ),
        )
        return redirect(url_for("patients"))

    search = request.args.get("q", "").strip()
    gender = request.args.get("gender", "")
    where_sql, args = patient_scope_sql(user)
    if search:
        where_sql += " AND (name LIKE ? OR patient_code LIKE ? OR phone LIKE ?)"
        args.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if gender:
        where_sql += " AND gender = ?"
        args.append(gender)
    doctors = query("SELECT * FROM doctors ORDER BY name")
    return render_template(
        "patients.html",
        patients=query(f"SELECT * FROM patients WHERE {where_sql} ORDER BY id DESC", args),
        doctors=doctors,
        search=search,
        gender=gender,
    )


@app.route("/patients/<int:patient_id>")
@login_required
def patient_detail(patient_id):
    user = current_user()
    if user["role"] == ROLE_LAB_TECH:
        abort(403)
    if not can_access_patient(user, patient_id):
        abort(403)
    patient = query("SELECT * FROM patients WHERE id = ?", (patient_id,), one=True)
    if patient is None:
        return redirect(url_for("patients"))
    appointments_data = query("SELECT * FROM appointments WHERE patient_id = ? ORDER BY date DESC, time DESC", (patient_id,))
    reports_data = [] if user["role"] == ROLE_RECEPTIONIST else query("SELECT * FROM lab_reports WHERE patient_id = ? ORDER BY created_at DESC, id DESC", (patient_id,))
    return render_template("patient_detail.html", patient=patient, appointments=appointments_data, reports=reports_data)


@app.route("/patients/delete/<int:patient_id>", methods=["POST"])
@admin_required
def delete_patient(patient_id):
    execute("DELETE FROM lab_reports WHERE patient_id = ?", (patient_id,))
    execute("DELETE FROM appointments WHERE patient_id = ?", (patient_id,))
    execute("DELETE FROM patients WHERE id = ?", (patient_id,))
    return redirect(url_for("patients"))


def get_or_create_patient_by_name(name, doctor):
    patient_name = name.strip()
    patient = query("SELECT * FROM patients WHERE lower(name) = lower(?) ORDER BY id DESC", (patient_name,), one=True)
    if patient:
        return patient["id"]
    return execute(
        """
        INSERT INTO patients
        (patient_code, name, age, gender, blood_group, phone, address, symptoms, doctor, assigned_doctor_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"MF-{datetime.now().strftime('%H%M%S')}",
            patient_name,
            0,
            "Not specified",
            "",
            "",
            "",
            "Appointment booking",
            doctor["name"],
            doctor["id"],
            datetime.now().strftime("%Y-%m-%d"),
        ),
    )


@app.route("/appointments", methods=["GET", "POST"])
@roles_required(ROLE_SUPER_ADMIN, ROLE_DOCTOR, ROLE_RECEPTIONIST, ROLE_PATIENT)
def appointments():
    user = current_user()
    if request.method == "POST":
        if user["role"] not in (ROLE_SUPER_ADMIN, ROLE_RECEPTIONIST):
            abort(403)
        doctor = query("SELECT * FROM doctors WHERE id = ?", (request.form["doctor_id"],), one=True)
        patient_id = get_or_create_patient_by_name(request.form["patient_name"], doctor)
        execute(
            "INSERT INTO appointments (patient_id, doctor, doctor_id, date, time, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (patient_id, doctor["name"], doctor["id"], request.form["date"], request.form["time"], request.form["status"], request.form.get("notes")),
        )
        return redirect(url_for("appointments"))

    where_sql = "1=1"
    args = []
    if user["role"] == ROLE_DOCTOR:
        where_sql = "appointments.doctor_id = ?"
        args = [doctor_id_for_user(user) or -1]
    elif user["role"] == ROLE_PATIENT:
        where_sql = "appointments.patient_id = ?"
        args = [user["patient_id"] or -1]

    data = query(
        f"""
        SELECT appointments.*, patients.name AS patient_name, patients.patient_code
        FROM appointments
        JOIN patients ON patients.id = appointments.patient_id
        WHERE {where_sql}
        ORDER BY date ASC, time ASC
        """,
        args,
    )
    status_counts = {status: sum(1 for item in data if item["status"] == status) for status in ["Pending", "Confirmed", "Completed", "Cancelled"]}
    week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    calendar_items = {day: [] for day in week_days}
    for index, item in enumerate(data):
        calendar_items[week_days[index % len(week_days)]].append(item)
    return render_template(
        "appointments.html",
        appointments=data,
        patients=query("SELECT id, name FROM patients ORDER BY name"),
        status_counts=status_counts,
        doctors=query("SELECT * FROM doctors ORDER BY name"),
        calendar_items=calendar_items,
    )


@app.route("/lab-reports", methods=["GET", "POST"])
@roles_required(ROLE_SUPER_ADMIN, ROLE_DOCTOR, ROLE_LAB_TECH, ROLE_PATIENT)
def lab_reports():
    user = current_user()
    if request.method == "POST":
        if user["role"] not in (ROLE_SUPER_ADMIN, ROLE_DOCTOR, ROLE_LAB_TECH):
            abort(403)
        report_id = request.form.get("report_id")
        if report_id:
            report = query("SELECT * FROM lab_reports WHERE id = ?", (report_id,), one=True)
            if user["role"] == ROLE_LAB_TECH and report["assigned_to_user_id"] != user["id"]:
                abort(403)
            execute("UPDATE lab_reports SET result = ?, status = ? WHERE id = ?", (request.form.get("result"), request.form["status"], report_id))
        else:
            patient = query("SELECT * FROM patients WHERE id = ?", (request.form["patient_id"],), one=True)
            if not can_access_patient(user, patient["id"]):
                abort(403)
            lab_user = query("SELECT * FROM users WHERE role = ? ORDER BY id LIMIT 1", (ROLE_LAB_TECH,), one=True)
            execute(
                """
                INSERT INTO lab_reports
                (patient_id, test_name, result, status, created_at, assigned_to_user_id, doctor, doctor_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient["id"],
                    request.form["test_name"],
                    request.form.get("result"),
                    request.form["status"],
                    datetime.now().strftime("%Y-%m-%d"),
                    lab_user["id"] if lab_user else None,
                    patient["doctor"],
                    patient["assigned_doctor_id"],
                ),
            )
        return redirect(url_for("lab_reports"))

    where_sql = "1=1"
    args = []
    if user["role"] == ROLE_DOCTOR:
        where_sql = "lab_reports.doctor_id = ?"
        args = [doctor_id_for_user(user) or -1]
    elif user["role"] == ROLE_PATIENT:
        where_sql = "lab_reports.patient_id = ?"
        args = [user["patient_id"] or -1]
    elif user["role"] == ROLE_LAB_TECH:
        where_sql = "lab_reports.assigned_to_user_id = ?"
        args = [user["id"]]
    reports = query(
        f"""
        SELECT lab_reports.*, patients.name AS patient_name, patients.patient_code
        FROM lab_reports
        JOIN patients ON patients.id = lab_reports.patient_id
        WHERE {where_sql}
        ORDER BY lab_reports.id DESC
        """,
        args,
    )
    enhanced_reports = []
    for report in reports:
        item = dict(report)
        item["progress_width"] = report_progress_width(report["status"])
        enhanced_reports.append(item)
    patient_where, patient_args = patient_scope_sql(user)
    return render_template("lab_reports.html", reports=enhanced_reports, patients=query(f"SELECT id, name FROM patients WHERE {patient_where} ORDER BY name", patient_args))


@app.route("/analytics")
@admin_required
def analytics():
    return render_template("analytics.html")


@app.route("/ai-tools")
@roles_required(ROLE_SUPER_ADMIN, ROLE_DOCTOR)
def ai_tools():
    return render_template("ai_tools.html")


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@app.route("/api/chart-data")
@login_required
def chart_data():
    user = current_user()
    if user["role"] not in (ROLE_SUPER_ADMIN, ROLE_DOCTOR, ROLE_RECEPTIONIST):
        return {"error": "Forbidden"}, 403
    return {
        "patients": [18, 25, 32, 38, 44, 58, 67],
        "appointments": [12, 19, 15, 28, 24, 31, 27],
        "tests": {"CBC": 34, "Blood Sugar": 26, "Urine": 18, "Thyroid": 14, "Lipid": 22},
        "workload": [72, 58, 81, 63],
    }


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
