# 🏥 MediCore

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-black?style=for-the-badge)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=for-the-badge)
![Render](https://img.shields.io/badge/Hosted%20on-Render-6C47FF?style=for-the-badge)
![License](https://img.shields.io/badge/License-Custom-green?style=for-the-badge)

## AI-Powered Hospital Management System

MediCore is a modern full-stack Hospital Management System developed using **Flask**, **SQLite**, **HTML**, **CSS**, **JavaScript**, and **Tailwind CSS**.

The application enables hospitals, clinics, pathology laboratories, and healthcare centers to efficiently manage patients, appointments, laboratory reports, healthcare analytics, and AI-assisted workflows through a clean and responsive interface.

This project was built as a professional portfolio application for internships, recruiter evaluations, software demonstrations, and healthcare technology showcases.

---

# 🚀 Live Demo

### 🌐 https://medicore-vjys.onrender.com

---

# 🔐 Demo Login

### Administrator

**Email**

```
admin@medicore.ai
```

**Password**

```
medicore123
```

---

# ✨ Features

✅ Secure Authentication using Flask Sessions

✅ Password Hashing using Werkzeug

✅ Patient Registration & Management

✅ Appointment Scheduling System

✅ Laboratory Report Management

✅ Healthcare Analytics Dashboard

✅ Interactive Charts using Chart.js

✅ AI Module Interface

✅ Settings & User Preferences

✅ Responsive UI for Desktop & Mobile

✅ Dark Mode Support

✅ Render Cloud Deployment

---

# 🏗 Architecture

```
Frontend
(HTML + CSS + JavaScript + Tailwind)

                │

                ▼

Flask Backend

                │

                ▼

SQLite Database

                │

                ▼

Render Cloud Deployment
```

---

# 💻 Tech Stack

## Frontend

- HTML5
- CSS3
- JavaScript
- Tailwind CSS
- Bootstrap Icons
- Chart.js

## Backend

- Python
- Flask
- SQLite
- Werkzeug Authentication
- Gunicorn

---

# 📂 Modules

- Landing Page
- Login System
- Dashboard
- Patient Management
- Patient Details
- Appointment Management
- Laboratory Reports
- Analytics Dashboard
- AI Assistant
- Settings

---

# 📁 Project Structure

```text
MediCore/
│
├── app.py
├── requirements.txt
├── runtime.txt
├── Procfile
├── render.yaml
├── README.md
├── LICENSE
│
├── static/
│   ├── css/
│   ├── js/
│   └── screenshots/
│
└── templates/
    ├── base.html
    ├── landing.html
    ├── login.html
    ├── dashboard.html
    ├── patients.html
    ├── patient_detail.html
    ├── appointments.html
    ├── lab_reports.html
    ├── analytics.html
    ├── ai_tools.html
    └── settings.html
```

---

# ⚙️ Installation

## Clone Repository

```bash
git clone https://github.com/mrashish18/MediCore.git
```

Move into the project

```bash
cd MediCore
```

Create Virtual Environment

```bash
python -m venv .venv
```

Activate Environment

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install Dependencies

```bash
pip install -r requirements.txt
```

Run the Application

```bash
python app.py
```

Open

```
http://127.0.0.1:5000
```

---

# 📸 Screenshots

## 🏠 Homepage

### Landing Page

![Homepage Start](static/screenshots/01_HOMEPAGE_START_01.png)

![Homepage Middle](static/screenshots/02_HOMEPAGE_MIDDLE_02.png)

![Homepage End](static/screenshots/03_HOMEPAGE_END_03.png)

---

## 🔐 Authentication

![Sign In](static/screenshots/04_SIGN%20IN%20OR%20SIGN%20UP%20PAGE.png)

---

## 📊 Dashboard

![Dashboard](static/screenshots/05_HOSPITAL%20DASHBOARD.png)

---

## 👨‍⚕️ Patient Management

![Patient Management](static/screenshots/06_PATIENT%20MANAGEMENT.png)

![Add Patient](static/screenshots/07_ADD%20PATIENT.png)

---

## 📅 Appointment System

![Appointment System](static/screenshots/08_APPOINTMENT%20SYSTEM.png)

![Book Appointment](static/screenshots/09_BOOK%20APPOINTMENT.png)

---

## 🧪 Laboratory Reports

![Lab Reports](static/screenshots/10_LAB%20REPORT%20MANAGEMENT.png)

![Add Lab Test](static/screenshots/11_ADD%20LAB%20TEST.png)

---

## 📈 Analytics

![Analytics](static/screenshots/12_ANALYTICS.png)

---

## 🤖 AI Module

![AI Module](static/screenshots/13_AI%20MODULE.png)

---

# 🚀 Deployment

The project is deployed on **Render**.

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
gunicorn app:app
```

Environment Variables

```
SECRET_KEY
```

---

# 📌 Resume Highlights

- Developed a full-stack Hospital Management System using Flask and SQLite.
- Designed secure authentication with password hashing and Flask sessions.
- Built patient management, appointment scheduling, laboratory reports, analytics, and AI workflow modules.
- Created responsive dashboards using Tailwind CSS and Chart.js.
- Deployed the application on Render with production-ready configuration.
- Managed project development using Git and GitHub.

---

# 🔮 Future Improvements

- Role-Based Access Control (Admin, Doctor, Patient, Lab Technician, Receptionist)
- AI Symptom Checker
- AI Medical Report Summarizer
- QR Code Patient ID
- PDF Report Generation
- Email Notifications
- REST API
- Mobile Application
- OCR Prescription Scanner
- Voice Assistant
- Drug Interaction Checker

---

# 👨‍💻 Author

## Ashish Kumar

**BS in Data Science and Applications**

**Indian Institute of Technology Madras**

GitHub

https://github.com/mrashish18

---

# 📄 License

© 2026 Ashish Kumar

This project is intended for educational, learning, portfolio, and demonstration purposes.

Commercial redistribution, resale, or reproduction without permission is prohibited.

See the **LICENSE** file for complete licensing information.

---

⭐ If you found this project useful, consider giving it a Star on GitHub.