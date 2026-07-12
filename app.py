"""Instructor Hub — main entry point.

Run locally:
    streamlit run app.py

Default admin (change after first login by editing data.db or add a change-password page):
    Email:    [email protected]
    Password: admin123
"""
import base64
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st
import extra_streamlit_components as stx

from admin_views import render_admin
from auth import sign_in, sign_up, create_session, get_user_from_session, delete_session
from database import init_db, seed_admin
from student_views import render_student

# -------------------- Page config --------------------
BASE_DIR = Path(__file__).parent
ICON_PATH = BASE_DIR / "icons" / "roll-call.png"

st.set_page_config(
    page_title="CCS Studenthub",
    page_icon=str(ICON_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

with open(ICON_PATH, "rb") as _f:
    ICON_B64 = base64.b64encode(_f.read()).decode()


# -------------------- Init DB + seed admin --------------------
init_db()
# 👇 CHANGE THESE VALUES to your own before deploying
seed_admin(
    email="[email protected]",
    password="admin123",
    full_name="Kadra",
)

# -------------------- Styling --------------------
st.markdown(
    """
    <style>
        /* Base */
        .stApp {
            background-color: #FFFFFF;
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
            color: #1A1A1A;
        }
        .stApp p, .stApp label, .stApp span, .stApp div { font-size: 1.05rem; }

        /* Typography */
        h1 {
            color: #C2185B;
            font-weight: 700;
            font-size: 5.5rem;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }
        h2 { color: #C2185B; font-weight: 600; font-size: 1.9rem; letter-spacing: -0.01em; }
        h3 { color: #C2185B; font-weight: 600; font-size: 1.45rem; }
        h4 { color: #1A1A1A; font-weight: 600; font-size: 1.2rem; }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #FAFAFA;
            border-right: 1px solid #EEEEEE;
        }
        section[data-testid="stSidebar"] .stMarkdown { font-size: 1.05rem; }
        section[data-testid="stSidebar"] [role="radiogroup"] label {
            font-size: 1.05rem;
            padding: 0.35rem 0;
        }

        /* Buttons */
        .stButton > button, [data-testid="stFormSubmitButton"] button {
            background-color: #C2185B;
            color: #FFFFFF;
            border: none;
            border-radius: 12px;
            padding: 0.7rem 1.6rem;
            font-weight: 500;
            font-size: 1rem;
            transition: all 0.15s ease;
            box-shadow: 0 1px 2px rgba(194, 24, 91, 0.15);
        }
        .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
            background-color: #AD1457;
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(194, 24, 91, 0.30);
            color: #FFFFFF;
        }
        .stButton > button:focus { outline: none; box-shadow: 0 0 0 3px rgba(194, 24, 91, 0.25); color: #FFFFFF; }

        /* Cards */
        .card {
            background: #FFFFFF;
            border: 1px solid #F0F0F0;
            border-left: 4px solid #C2185B;
            border-radius: 14px;
            padding: 1.5rem 1.75rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            transition: box-shadow 0.15s ease;
            font-size: 1.05rem;
        }
        .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .card h4 { color: #1A1A1A; margin: 0; font-size: 1.25rem; }
        .card p { font-size: 1rem; line-height: 1.5; }

        /* Chips */
        .chip {
            display: inline-block;
            padding: 0.3rem 0.9rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            white-space: nowrap;
        }
        .chip-pending   { background: #FFF3E0; color: #E65100; }
        .chip-approved  { background: #E8F5E9; color: #2E7D32; }
        .chip-confirmed { background: #E8F5E9; color: #2E7D32; }
        .chip-rejected  { background: #FFEBEE; color: #C62828; }

        /* Inputs */
        input[type="text"], input[type="password"], textarea {
            font-size: 1.05rem !important;
            border-radius: 10px !important;
            padding: 0.6rem 0.85rem !important;
        }
        .stSelectbox div[data-baseweb="select"] > div,
        .stDateInput input, .stTimeInput input {
            font-size: 1.05rem !important;
            border-radius: 10px !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
        .stTabs [data-baseweb="tab"] { font-size: 1.05rem; padding: 0.6rem 1rem; }
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] { color: #C2185B; }
        .stTabs [data-baseweb="tab-highlight"] { background-color: #C2185B; }

        /* Metrics */
        [data-testid="stMetricValue"] { color: #C2185B; font-size: 2.2rem; font-weight: 700; }
        [data-testid="stMetricLabel"] { font-size: 1rem; }

        /* Dividers */
        hr { border-color: #EEEEEE; margin: 1.5rem 0; }

        /* DataFrames */
        .stDataFrame { font-size: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- Session state --------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "current_course" not in st.session_state:
    st.session_state.current_course = None
if "hub_session_token" not in st.session_state:
    st.session_state.hub_session_token = None

# -------------------- Cookie manager --------------------
cookies = stx.CookieManager(key="hub_cookie_manager")
all_cookies = cookies.get_all()  # force cookies to load into memory

# Handle sign-out (triggered from admin/studen  t views)
if st.session_state.get("sign_out_requested"):
    st.session_state.sign_out_requested = False
    old_token = st.session_state.get("hub_session_token")
    if old_token:
        delete_session(old_token)
    try:
        cookies.delete("hub_session", key="delete_hub_session")
    except Exception:
        pass
    st.session_state.user = None
    st.session_state.current_course = None
    st.session_state.hub_session_token = None
    st.rerun()

# Restore session from cookie on page load
if st.session_state.user is None:
    saved_token = (all_cookies or {}).get("hub_session")
    if saved_token:
        restored = get_user_from_session(saved_token)
        if restored:
            st.session_state.user = restored
            st.session_state.hub_session_token = saved_token
        else:
            # Cookie exists but the session is gone (DB reset, expired, or logged out
            # from elsewhere). Clean up the stale cookie so the user gets a fresh start.
            try:
                cookies.delete("hub_session", key="delete_stale_hub_session")
            except Exception:
                pass

# -------------------- Login / Signup screen --------------------
def login_screen():
    col_left, col_mid, col_right = st.columns([1, 4, 1])
    with col_mid:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 20px; margin: 1rem 0 1.5rem 0;">
                <img src="data:image/png;base64,{ICON_B64}" style="width: 130px; height: auto; display: block;"/>
                <span style="
                    color: #C2185B;
                    font-size: 6rem;
                    font-weight: 800;
                    letter-spacing: -0.03em;
                    line-height: 1;
                    white-space: nowrap;
                    font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
                ">
                    CCS Studenthub
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Consultation booking · Class schedule · Course announcements")

        tab_signin, tab_signup = st.tabs(["Sign in", "Sign up"])

        with tab_signin:
            with st.form("signin_form"):
                email = st.text_input("Email", key="signin_email")
                password = st.text_input(
                    "Password", type="password", key="signin_pw"
                )
                if st.form_submit_button("Sign in", use_container_width=True):
                    user = sign_in(email, password)
                    if user:
                        token = create_session(user["id"])
                        cookies.set(
                            "hub_session",
                            token,
                            expires_at=datetime.now() + timedelta(days=30),
                            key="set_hub_session",
                        )
                        st.session_state.user = user
                        st.session_state.hub_session_token = token
                        # Small delay so the browser has time to receive the cookie
                        import time
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")

        with tab_signup:
            with st.form("signup_form", clear_on_submit=True):
                full_name = st.text_input("Full name", key="signup_name")
                email = st.text_input("Email", key="signup_email")
                password = st.text_input(
                    "Password (min 6 characters)",
                    type="password",
                    key="signup_pw",
                )
                if st.form_submit_button("Create account", use_container_width=True):
                    ok, msg = sign_up(email, password, full_name)
                    (st.success if ok else st.error)(msg)
            st.caption(
                "Only student accounts can be created here. "
                "The instructor account is set by the admin."
            )


# -------------------- Route --------------------
# The cookie component reports `None` OR `{}` on the first script run
# (before it has finished loading in the browser). We treat both as
# "cookies not ready yet" and show a loader instead of the login screen.
cookies_ready = all_cookies is not None and len(all_cookies) > 0

if st.session_state.user is None and not cookies_ready:
    # Cookies not yet loaded — show a subtle loading placeholder
    st.markdown(
        """
        <div style="display:flex; justify-content:center; align-items:center;
                    height:60vh; color:#C2185B;">
            <div style="text-align:center;">
                <div style="width:40px; height:40px; margin:0 auto 1rem;
                            border:4px solid #FCE4EC; border-top-color:#C2185B;
                            border-radius:50%; animation:spin 0.8s linear infinite;"></div>
                <div style="font-size:1.1rem;">Loading…</div>
            </div>
        </div>
        <style>
            @keyframes spin { to { transform: rotate(360deg); } }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

if st.session_state.user is None:
    login_screen()
else:
    if st.session_state.user["role"] == "admin":
        render_admin()
    else:
        render_student()