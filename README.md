# 🎓 Instructor Hub

A minimalist Streamlit web app for a college instructor to manage:
- Student sign-up / sign-in with password
- Course enrollment requests (instructor approves each one)
- Class schedule with room and time
- Attendance per course, per date
- Announcements posted **inside each course** (only enrolled students see them)
- 1-on-1 consultation booking

Color palette: **magenta (#C2185B)** on **white**.

---

## 1. Setup

Open the folder in VS Code, then in the built-in terminal:

```bash
# (Recommended) create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Run locally

```bash
streamlit run app.py
```

The app opens in your browser at http://localhost:8501

## 3. First login

The app auto-creates a default admin account on first run:

- **Email:** `[email protected]`
- **Password:** `admin123`

**⚠️ Change these before you deploy.** Open `app.py` and edit the `seed_admin(...)` call at the top. Delete `data.db` and run again to re-seed with your new credentials.

## 4. How the flow works

**As the admin (you):**
1. Sign in with your admin account.
2. Go to **Courses** → create your courses (code, name, room, day, time).
3. Wait for students to sign up and request enrollment.
4. Go to **Enrollment Requests** → approve or reject each one.
5. Go to **Course Manager** → pick a course to:
   - Post announcements (only visible to approved students of that course)
   - Record attendance for a given date
   - View the enrolled student roster
6. Go to **Consultations** → confirm or decline consultation bookings.

**As a student:**
1. Click **Sign up** and create a student account.
2. Go to **Enroll in a Course** → request enrollment in the courses you're taking.
3. Wait for the instructor to approve.
4. Once approved, the course appears in **My Courses**. Click **Open course** to see announcements and your attendance.
5. Use **Book a Consultation** to request a 1-on-1 meeting.

## 5. Project structure

```
instructor_hub/
├── .streamlit/
│   └── config.toml         # Theme colors (magenta + white)
├── app.py                  # Main entry, routing, CSS
├── auth.py                 # Password hashing, sign up, sign in
├── database.py             # SQLite schema and connection
├── admin_views.py          # Instructor screens
├── student_views.py        # Student screens
├── requirements.txt        # Python dependencies
├── data.db                 # Auto-created SQLite database (do not commit)
└── README.md
```

## 6. Deploy to Streamlit Community Cloud (free)

1. Create a public GitHub repo and push this folder.
2. **Important:** add `data.db` to `.gitignore` so it isn't committed.
3. Go to https://share.streamlit.io → **New app** → point it to your repo and `app.py`.
4. First time it runs, it will create a fresh `data.db` and seed the default admin.

**Caveat about SQLite on Streamlit Community Cloud:** the `data.db` file lives on the container's local disk. It persists during normal operation, but if the app is restarted or redeployed, the database is reset. For a long-lived deployment you'd want a hosted DB (e.g. Supabase / Neon Postgres, LiteFS, or Turso). For local use in VS Code, SQLite is perfect.

## 7. Common tweaks

- **Change the color:** edit `.streamlit/config.toml` (`primaryColor`) and the `MAGENTA` constant at the top of `app.py`.
- **Rename the app title:** change `page_title` in `app.py` and the `st.title("🎓 Instructor Hub")` line in the login screen.
- **Reset all data:** stop the app, delete `data.db`, and restart. Everything (users, courses, announcements, attendance) will be cleared.
- **Add more admin users:** the simplest way is to sign up as a student, then manually edit their row in `data.db` with SQLite Browser (`role = 'admin'`).
