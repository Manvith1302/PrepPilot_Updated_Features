# PrepPilot – Recruitment Exam Practice Platform (Python Flask)

## Features
- Student registration and email/password login (passwords are hashed).
- Optional Google OAuth sign-in.
- Student dashboard with practice categories and progress summary.
- Timed multiple-choice quizzes, automatic evaluation and result history.
- Leaderboard based on accumulated correct answers.
- Admin dashboard to add/delete questions and view basic counts.
- SQLite database; sample questions are seeded automatically.

## 1. Requirements
- Python 3.10 or newer
- VS Code (recommended)
- Internet connection for installing packages and Google sign-in

## 2. Run on Windows
Open this folder in VS Code. In Terminal (PowerShell), run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
copy .env.example .env
py app.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. Alternatively, use `py -m pip install -r requirements.txt` and `py app.py` without activating the environment.

Open http://127.0.0.1:5000

## 3. Demo accounts
- Admin: `admin@preppilot.com` / `admin123`
- Student: register a new account using the Sign Up page.

Change the admin password and SECRET_KEY before sharing or deploying the app.

## 4. Enable Google Sign-In
Google sign-in is optional and requires your own OAuth credentials:

1. Open Google Cloud Console: https://console.cloud.google.com/
2. Create/select a project and configure the OAuth consent screen.
3. Create an OAuth Client ID with application type **Web application**.
4. Add this Authorized redirect URI exactly: `http://127.0.0.1:5000/auth/google/callback`
5. Copy the Client ID and Client Secret into `.env`:
   `GOOGLE_CLIENT_ID=...`
   `GOOGLE_CLIENT_SECRET=...`
6. Stop and restart `py app.py`.

The Google button is shown even before setup; until credentials are supplied, the app explains that Google sign-in needs configuration. For deployment, use HTTPS and add your production callback URL in Google Cloud Console. Never commit `.env` or expose the client secret.

## 5. Project structure
```
PrepPilot_Python_Flask/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── .gitignore
├── instance/                 # created automatically
│   └── preppilot.db          # SQLite database
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── quiz.html
    ├── results.html
    ├── leaderboard.html
    └── admin.html
└── static/
    ├── css/style.css
    └── js/quiz.js
```

## 6. Important notes
This is a college-project starter, not a production identity platform. Before public deployment, add CSRF protection, rate limiting, email verification, secure HTTPS cookie settings, stronger admin provisioning, backups, and production logging. Google OAuth cannot work until you create and add credentials in your own Google Cloud project.


## Added study features
- Category-wise performance analytics on the student dashboard.
- Daily practice goal settings.
- Personal study planner with due dates and completion tracking.
- Bookmark questions during quizzes and revise saved answers with explanations.
- New tables are created automatically by SQLAlchemy on application startup.
