"""Admin (instructor) views."""
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st


from database import get_connection
# ------------- Course schedule options -------------
DAY_OPTIONS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    "Mon - Tue", "Mon - Wed", "Mon - Thu", "Mon - Fri", "Mon - Sat",
    "Tue - Wed", "Tue - Thu", "Tue - Fri", "Tue - Sat",
    "Wed - Thu", "Wed - Fri", "Wed - Sat",
    "Thu - Fri", "Thu - Sat",
    "Fri - Sat",
]

DURATION_OPTIONS = {
    "1 hour": 60,
    "1 hour 30 minutes": 90,
    "2 hours": 120,
    "2 hours 30 minutes": 150,
    "3 hours": 180,
    "3 hours 30 minutes": 210,
    "4 hours": 240,
    "5 hours": 300,
}

def _generate_start_times():
    t = datetime.strptime("07:00", "%H:%M")
    end = datetime.strptime("20:00", "%H:%M")
    out = []
    while t <= end:
        out.append(t.strftime("%H:%M"))
        t += timedelta(minutes=30)
    return out

START_TIME_OPTIONS = _generate_start_times()

def format_time_slot(start_str: str, duration_min: int) -> str:
    start = datetime.strptime(start_str, "%H:%M")
    end = start + timedelta(minutes=duration_min)
    return f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"

def render_admin():
    user = st.session_state.user
    with st.sidebar:
        st.markdown(f"### Welcome, {user['full_name']}")
        st.caption("Signed in as **admin**")
        st.divider()
        page = st.radio(
            "Navigate",
            [
                "Dashboard",
                "Courses",
                "Enrollment Requests",
                "Consultations",
                "Course Manager",
            ],
            label_visibility="collapsed",
        )
        if st.button("Sign out", use_container_width=True):
            st.session_state.sign_out_requested = True
            st.rerun()

    if page == "Dashboard":
        admin_dashboard()
    elif page == "Courses":
        admin_courses()
    elif page == "Enrollment Requests":
        admin_enrollments()
    elif page == "Consultations":
        admin_consultations()
    elif page == "Course Manager":
        admin_course_manager()


# ----------------------------- Dashboard -----------------------------
def admin_dashboard():
    st.title("Dashboard")
    conn = get_connection()
    n_students = conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    n_courses = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    n_pending = conn.execute(
        "SELECT COUNT(*) FROM enrollments WHERE status='pending'"
    ).fetchone()[0]
    n_consults = conn.execute(
        "SELECT COUNT(*) FROM consultations WHERE status='pending'"
    ).fetchone()[0]
    conn.close()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Students", n_students)
    c2.metric("Courses", n_courses)
    c3.metric("Pending Enrollments", n_pending)
    c4.metric("Pending Consultations", n_consults)

    st.divider()
    st.subheader("Class schedule")
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT code AS Code, name AS Course, room AS Room, "
        "schedule_day AS Day, schedule_time AS Time "
        "FROM courses ORDER BY schedule_day, schedule_time",
        conn,
    )
    conn.close()
    if df.empty:
        st.info("No courses yet. Add one in **Courses**.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


# ----------------------------- Courses -----------------------------
def admin_courses():
    with st.expander("➕ Add a new course", expanded=False):
        with st.form("new_course", clear_on_submit=True):
            c1, c2 = st.columns(2)
            code = c1.text_input("Course code", placeholder="e.g. CS401")
            name = c2.text_input("Course name", placeholder="e.g. Advanced Image Processing")

            c3, c4 = st.columns(2)
            room = c3.text_input("Room", placeholder="e.g. Lab 3-201")
            day = c4.selectbox("Day / Days", DAY_OPTIONS)

            c5, c6 = st.columns(2)
            duration_label = c5.selectbox("Class duration", list(DURATION_OPTIONS.keys()))
            start_time = c6.selectbox("Start time", START_TIME_OPTIONS)

            if st.form_submit_button("Create course"):
                if not code or not name:
                    st.error("Code and name are required.")
                else:
                    duration_min = DURATION_OPTIONS[duration_label]
                    time_str = format_time_slot(start_time, duration_min)
                    try:
                        conn = get_connection()
                        conn.execute(
                            "INSERT INTO courses (code, name, room, schedule_day, schedule_time) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (code.upper().strip(), name.strip(), room.strip(), day, time_str),
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"Course {code.upper()} created — {day}, {time_str}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not create course: {e}")

    conn = get_connection()
    courses = conn.execute("SELECT * FROM courses ORDER BY code").fetchall()
    conn.close()

    if not courses:
        st.info("No courses created yet.")
        return

    for c in courses:
        st.markdown(
            f"""
            <div class="card">
                <h4 style="margin:0;">{c['code']} — {c['name']}</h4>
                <p style="margin:0.35rem 0 0; color:#555;">
                    📍 {c['room'] or 'TBA'} &nbsp;·&nbsp; 🗓 {c['schedule_day'] or 'TBA'} &nbsp;·&nbsp; ⏰ {c['schedule_time'] or 'TBA'}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col1, _ = st.columns([1, 6])
        if col1.button("Delete", key=f"del_{c['id']}"):
            conn = get_connection()
            conn.execute("DELETE FROM courses WHERE id = ?", (c["id"],))
            conn.commit()
            conn.close()
            st.rerun()


# ----------------------------- Enrollments -----------------------------
def admin_enrollments():
    st.title("Enrollment Requests")
    st.caption("Approve or reject students who requested to enroll in your courses.")

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT e.id, e.status, e.requested_at,
               u.id AS student_id, u.full_name, u.email,
               c.id AS course_id, c.code, c.name
        FROM enrollments e
        JOIN users u ON u.id = e.user_id
        JOIN courses c ON c.id = e.course_id
        ORDER BY (e.status='pending') DESC, e.requested_at DESC
        """
    ).fetchall()
    conn.close()

    if not rows:
        st.info("No enrollment requests yet.")
        return

    status_filter = st.selectbox("Filter", ["All", "Pending", "Approved", "Rejected"])

    for r in rows:
        if status_filter != "All" and r["status"] != status_filter.lower():
            continue
        chip_class = f"chip-{r['status']}"
        st.markdown(
            f"""
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong>{r['full_name']}</strong>
                        <span style="color:#666;">({r['email']})</span><br>
                        <span style="color:#333;">Requested: <strong>{r['code']}</strong> — {r['name']}</span>
                    </div>
                    <span class="chip {chip_class}">{r['status'].upper()}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if r["status"] == "pending":
            c1, c2, _ = st.columns([1, 1, 6])
            if c1.button("✅ Approve", key=f"apv_{r['id']}"):
                conn = get_connection()
                conn.execute(
                    "UPDATE enrollments SET status='approved' WHERE id = ?", (r["id"],)
                )
                conn.commit()
                conn.close()
                st.rerun()
            if c2.button("❌ Reject", key=f"rej_{r['id']}"):
                conn = get_connection()
                conn.execute(
                    "UPDATE enrollments SET status='rejected' WHERE id = ?", (r["id"],)
                )
                conn.commit()
                conn.close()
                st.rerun()


# ----------------------------- Consultations -----------------------------
def admin_consultations():
    st.title("Consultation Requests")
    st.caption("Confirm or decline consultation bookings from students.")

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT co.*, u.full_name, u.email
        FROM consultations co
        JOIN users u ON u.id = co.student_id
        ORDER BY (co.status='pending') DESC, co.requested_date, co.requested_time
        """
    ).fetchall()
    conn.close()

    if not rows:
        st.info("No consultation requests yet.")
        return

    for r in rows:
        st.markdown(
            f"""
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div>
                        <strong>{r['full_name']}</strong>
                        <span style="color:#666;">({r['email']})</span><br>
                        🗓 <strong>{r['requested_date']}</strong> at <strong>{r['requested_time']}</strong><br>
                        <em style="color:#333;">Topic: {r['topic']}</em>
                    </div>
                    <span class="chip chip-{r['status']}">{r['status'].upper()}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if r["status"] == "pending":
            c1, c2, _ = st.columns([1, 1, 6])
            if c1.button("✅ Confirm", key=f"con_{r['id']}"):
                conn = get_connection()
                conn.execute(
                    "UPDATE consultations SET status='confirmed' WHERE id = ?", (r["id"],)
                )
                conn.commit()
                conn.close()
                st.rerun()
            if c2.button("❌ Decline", key=f"dec_{r['id']}"):
                conn = get_connection()
                conn.execute(
                    "UPDATE consultations SET status='rejected' WHERE id = ?", (r["id"],)
                )
                conn.commit()
                conn.close()
                st.rerun()


# --------------------------- Course Manager ---------------------------
def admin_course_manager():
    st.title("Course Manager")
    st.caption("Pick a course to manage its announcements, attendance, and roster.")

    conn = get_connection()
    courses = conn.execute("SELECT * FROM courses ORDER BY code").fetchall()
    conn.close()

    if not courses:
        st.info("No courses yet. Create one in **Courses** first.")
        return

    labels = [f"{c['code']} — {c['name']}" for c in courses]
    idx = st.selectbox("Course", range(len(courses)), format_func=lambda i: labels[i])
    course = courses[idx]

    tab_ann, tab_att, tab_students = st.tabs(
        ["📢 Announcements", "✅ Attendance", "👥 Enrolled Students"]
    )
    with tab_ann:
        manage_announcements(course["id"])
    with tab_att:
        manage_attendance(course["id"])
    with tab_students:
        show_enrolled_students(course["id"])


def manage_announcements(course_id: int):
    st.subheader("Post an announcement")
    st.caption("Only students enrolled (approved) in this course will see it.")
    with st.form("new_ann", clear_on_submit=True):
        c1, c2 = st.columns([3, 1])
        title = c1.text_input("Title")
        ann_type = c2.selectbox("Type", ["activity", "status"])
        content = st.text_area(
            "Message",
            placeholder="e.g. 'I cannot attend tomorrow's class' or 'Quiz on Chapter 4 this Friday'",
        )
        if st.form_submit_button("Post"):
            if not title or not content:
                st.error("Title and message are required.")
            else:
                conn = get_connection()
                conn.execute(
                    "INSERT INTO announcements (course_id, title, content, type) "
                    "VALUES (?, ?, ?, ?)",
                    (course_id, title.strip(), content.strip(), ann_type),
                )
                conn.commit()
                conn.close()
                st.success("Announcement posted.")
                st.rerun()

    st.divider()
    st.subheader("Previous announcements")
    conn = get_connection()
    anns = conn.execute(
        "SELECT * FROM announcements WHERE course_id = ? ORDER BY posted_at DESC",
        (course_id,),
    ).fetchall()
    conn.close()

    if not anns:
        st.info("No announcements posted yet for this course.")
        return

    for a in anns:
        icon = "📌" if a["type"] == "activity" else "📣"
        st.markdown(
            f"""
            <div class="card">
                <div style="display:flex; justify-content:space-between;">
                    <strong>{icon} {a['title']}</strong>
                    <span style="color:#888; font-size:0.8rem;">{a['posted_at']}</span>
                </div>
                <p style="margin:0.5rem 0 0; white-space:pre-wrap;">{a['content']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Delete", key=f"delann_{a['id']}"):
            conn = get_connection()
            conn.execute("DELETE FROM announcements WHERE id = ?", (a["id"],))
            conn.commit()
            conn.close()
            st.rerun()


def manage_attendance(course_id: int):
    st.subheader("Record attendance")
    conn = get_connection()
    students = conn.execute(
        """
        SELECT u.id, u.full_name, u.email
        FROM users u
        JOIN enrollments e ON e.user_id = u.id
        WHERE e.course_id = ? AND e.status = 'approved'
        ORDER BY u.full_name
        """,
        (course_id,),
    ).fetchall()
    conn.close()

    if not students:
        st.info("No approved students enrolled in this course yet.")
        return

    att_date = st.date_input("Date", value=date.today())

    st.write("Mark attendance:")
    statuses = {}
    for s in students:
        c1, c2 = st.columns([3, 2])
        c1.write(f"**{s['full_name']}** — {s['email']}")
        statuses[s["id"]] = c2.selectbox(
            f"Status_{s['id']}",
            ["present", "absent", "late"],
            label_visibility="collapsed",
            key=f"att_{s['id']}_{att_date.isoformat()}",
        )

    if st.button("Save attendance", type="primary"):
        conn = get_connection()
        for sid, status in statuses.items():
            conn.execute(
                """
                INSERT INTO attendance (course_id, student_id, date, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(course_id, student_id, date) DO UPDATE SET status = excluded.status
                """,
                (course_id, sid, att_date.isoformat(), status),
            )
        conn.commit()
        conn.close()
        st.success(f"Attendance saved for {att_date.isoformat()}.")

    st.divider()
    st.subheader("Attendance history")
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT a.date AS Date, u.full_name AS Student, a.status AS Status
        FROM attendance a
        JOIN users u ON u.id = a.student_id
        WHERE a.course_id = ?
        ORDER BY a.date DESC, u.full_name
        """,
        conn,
        params=(course_id,),
    )
    conn.close()
    if df.empty:
        st.info("No attendance records yet.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def show_enrolled_students(course_id: int):
    st.subheader("Enrolled students (approved)")
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT u.full_name AS "Full name", u.email AS Email,
               e.requested_at AS "Enrolled since"
        FROM users u
        JOIN enrollments e ON e.user_id = u.id
        WHERE e.course_id = ? AND e.status = 'approved'
        ORDER BY u.full_name
        """,
        conn,
        params=(course_id,),
    )
    conn.close()
    if df.empty:
        st.info("No approved students yet.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
