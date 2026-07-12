"""Student views."""
from datetime import date, time

import pandas as pd
import streamlit as st

from database import get_connection


def render_student():
    user = st.session_state.user
    with st.sidebar:
        st.markdown(f"### 👋 {user['full_name']}")
        st.caption("Signed in as **student**")
        st.divider()
        page = st.radio(
            "Navigate",
            [
                "My Courses",
                "Enroll in a Course",
                "Book a Consultation",
                "My Consultations",
                "Class Schedule",
            ],
            label_visibility="collapsed",
        )
        st.divider()
        if st.button("Sign out", use_container_width=True):
            st.session_state.sign_out_requested = True
            st.rerun()

    # Reset course view when navigating away from "My Courses"
    if page != "My Courses":
        st.session_state.current_course = None

    if page == "My Courses":
        student_my_courses()
    elif page == "Enroll in a Course":
        student_enroll()
    elif page == "Book a Consultation":
        student_book()
    elif page == "My Consultations":
        student_my_consultations()
    elif page == "Class Schedule":
        student_schedule()


# ----------------------------- My Courses -----------------------------
def student_my_courses():
    user = st.session_state.user

    conn = get_connection()
    approved = conn.execute(
        """
        SELECT c.*
        FROM courses c
        JOIN enrollments e ON e.course_id = c.id
        WHERE e.user_id = ? AND e.status = 'approved'
        ORDER BY c.code
        """,
        (user["id"],),
    ).fetchall()
    conn.close()

    if st.session_state.get("current_course") is None:
        st.title("My Courses")
        if not approved:
            st.info(
                "You are not enrolled in any course yet. "
                "Go to **Enroll in a Course** to request enrollment."
            )
            return
        st.caption("Pick a course to open its announcement board.")
        for c in approved:
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
            if st.button("Open course", key=f"open_{c['id']}"):
                st.session_state.current_course = c["id"]
                st.rerun()
    else:
        show_course_inside(st.session_state.current_course)


def show_course_inside(course_id: int):
    user = st.session_state.user

    conn = get_connection()
    course = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    # Verify the student is still approved for this course
    enrolled = conn.execute(
        "SELECT 1 FROM enrollments WHERE user_id = ? AND course_id = ? AND status = 'approved'",
        (user["id"], course_id),
    ).fetchone()
    conn.close()

    if not course or not enrolled:
        st.error("This course is no longer available to you.")
        st.session_state.current_course = None
        if st.button("Back"):
            st.rerun()
        return

    if st.button("← Back to my courses"):
        st.session_state.current_course = None
        st.rerun()

    st.title(f"{course['code']} — {course['name']}")
    st.caption(
        f"📍 {course['room'] or 'TBA'}  ·  🗓 {course['schedule_day'] or 'TBA'}  ·  ⏰ {course['schedule_time'] or 'TBA'}"
    )

    tab_ann, tab_att = st.tabs(["📢 Announcements", "✅ My Attendance"])

    with tab_ann:
        conn = get_connection()
        anns = conn.execute(
            "SELECT * FROM announcements WHERE course_id = ? ORDER BY posted_at DESC",
            (course_id,),
        ).fetchall()
        conn.close()
        if not anns:
            st.info("No announcements yet for this course.")
        else:
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

    with tab_att:
        conn = get_connection()
        df = pd.read_sql_query(
            """
            SELECT date AS Date, status AS Status
            FROM attendance
            WHERE course_id = ? AND student_id = ?
            ORDER BY date DESC
            """,
            conn,
            params=(course_id, user["id"]),
        )
        conn.close()
        if df.empty:
            st.info("No attendance recorded yet.")
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)


# --------------------------- Enroll ---------------------------
def student_enroll():
    st.title("Enroll in a Course")
    st.caption("Request enrollment. Your instructor will approve or reject the request.")
    user = st.session_state.user

    conn = get_connection()
    all_courses = conn.execute("SELECT * FROM courses ORDER BY code").fetchall()
    existing = {
        r["course_id"]: r["status"]
        for r in conn.execute(
            "SELECT course_id, status FROM enrollments WHERE user_id = ?", (user["id"],)
        ).fetchall()
    }
    conn.close()

    if not all_courses:
        st.info("No courses have been created yet.")
        return

    for c in all_courses:
        current = existing.get(c["id"])
        if current == "approved":
            chip = '<span class="chip chip-approved">ENROLLED</span>'
        elif current == "pending":
            chip = '<span class="chip chip-pending">PENDING</span>'
        elif current == "rejected":
            chip = '<span class="chip chip-rejected">REJECTED</span>'
        else:
            chip = ""

        st.markdown(
            f"""
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h4 style="margin:0;">{c['code']} — {c['name']}</h4>
                        <p style="margin:0.35rem 0 0; color:#555;">
                            📍 {c['room'] or 'TBA'} · 🗓 {c['schedule_day'] or 'TBA'} · ⏰ {c['schedule_time'] or 'TBA'}
                        </p>
                    </div>
                    {chip}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if current is None:
            if st.button("Request enrollment", key=f"enr_{c['id']}"):
                conn = get_connection()
                conn.execute(
                    "INSERT INTO enrollments (user_id, course_id, status) "
                    "VALUES (?, ?, 'pending')",
                    (user["id"], c["id"]),
                )
                conn.commit()
                conn.close()
                st.rerun()
        elif current == "rejected":
            if st.button("Request again", key=f"reenr_{c['id']}"):
                conn = get_connection()
                conn.execute(
                    "UPDATE enrollments SET status='pending' WHERE user_id = ? AND course_id = ?",
                    (user["id"], c["id"]),
                )
                conn.commit()
                conn.close()
                st.rerun()


# --------------------------- Book Consultation ---------------------------
def student_book():
    st.title("Book a Consultation")
    st.caption("Request a 1-on-1 consultation with your instructor.")
    user = st.session_state.user

    with st.form("book_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        req_date = c1.date_input("Preferred date", min_value=date.today())
        req_time = c2.time_input("Preferred time", value=time(10, 0))
        topic = st.text_area(
            "What would you like to discuss?",
            placeholder="e.g. Thesis chapter feedback, exam questions, project consultation…",
        )
        submitted = st.form_submit_button("Request consultation")
        if submitted:
            if not topic.strip():
                st.error("Please describe the topic.")
            else:
                conn = get_connection()
                conn.execute(
                    """
                    INSERT INTO consultations (student_id, requested_date, requested_time, topic, status)
                    VALUES (?, ?, ?, ?, 'pending')
                    """,
                    (
                        user["id"],
                        req_date.isoformat(),
                        req_time.strftime("%H:%M"),
                        topic.strip(),
                    ),
                )
                conn.commit()
                conn.close()
                st.success("Consultation request sent.")


def student_my_consultations():
    st.title("My Consultations")
    user = st.session_state.user
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM consultations
        WHERE student_id = ?
        ORDER BY requested_date DESC, requested_time DESC
        """,
        (user["id"],),
    ).fetchall()
    conn.close()

    if not rows:
        st.info("No consultation requests yet.")
        return

    for r in rows:
        st.markdown(
            f"""
            <div class="card">
                <div style="display:flex; justify-content:space-between;">
                    <div>
                        🗓 <strong>{r['requested_date']}</strong> at <strong>{r['requested_time']}</strong><br>
                        <em>Topic: {r['topic']}</em>
                    </div>
                    <span class="chip chip-{r['status']}">{r['status'].upper()}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --------------------------- Class Schedule ---------------------------
def student_schedule():
    st.title("Class Schedule")
    st.caption("All courses offered by the instructor.")
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT code AS Code, name AS Course, room AS Room, "
        "schedule_day AS Day, schedule_time AS Time "
        "FROM courses ORDER BY schedule_day, schedule_time",
        conn,
    )
    conn.close()
    if df.empty:
        st.info("No courses posted yet.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
