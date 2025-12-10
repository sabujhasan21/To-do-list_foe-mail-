# app.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
import json, os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="Daily To-Do List", layout="wide")

USERS_FILE = "users.json"
DEFAULT_USER_STRUCT = {"password": "", "tasks": [], "completed": []}
REMINDER_EMAIL = "info.dusc@daffodilvarsity.edu.bd"

# ------------------ Helpers: load / save ------------------
def ensure_file():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({"sabuj2025": {"password": "sabuj", "tasks": [], "completed": []}}, f, indent=4)

def load_users():
    ensure_file()
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    changed = False
    for uname, data in list(users.items()):
        if not isinstance(data, dict):
            users[uname] = DEFAULT_USER_STRUCT.copy()
            changed = True
            continue
        for k, v in DEFAULT_USER_STRUCT.items():
            if k not in users[uname]:
                users[uname][k] = v
                changed = True
    if changed:
        save_users(users)
    return users

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

# ------------------ Notification popup ------------------
def notify(message, kind="success"):
    color = {
        "success": "#2E7D32",
        "error": "#D32F2F",
        "warning": "#F57C00",
        "info": "#0288D1"
    }.get(kind, "#2E7D32")
    safe_msg = message.replace("\n", "<br>")
    html = f"""
    <div id="toast" style="
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: {color};
        color: white;
        padding: 16px 24px;
        border-radius: 10px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        z-index: 9999;
        font-size: 16px;
        text-align:center;
        max-width: 90%;
    ">
      {safe_msg}
    </div>
    <style>
      @keyframes fadeInOut {{
        0%   {{ opacity: 0; transform: translate(-50%, -60%) scale(0.95); }}
        10%  {{ opacity: 1; transform: translate(-50%, -50%) scale(1); }}
        90%  {{ opacity: 1; transform: translate(-50%, -50%) scale(1); }}
        100% {{ opacity: 0; transform: translate(-50%, -40%) scale(0.95); }}
      }}
      #toast {{
        animation: fadeInOut 1.6s ease-in-out forwards;
      }}
    </style>
    """
    st.markdown(html, unsafe_allow_html=True)

# ------------------ CSS ------------------
def inject_page_style():
    st.markdown("""
    <style>
    .task-card {
        background: white;
        padding: 14px 16px;
        border-radius: 10px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        margin-bottom: 12px;
    }
    .task-title { font-size:18px; font-weight:700; margin-bottom:6px; }
    .task-info { font-size:13px; color:#444; }
    .stButton>button {
        border-radius: 8px;
        padding: 6px 12px;
        transition: transform .12s ease, box-shadow .12s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
    }
    </style>
    """, unsafe_allow_html=True)

# ------------------ Send reminder email ------------------
def send_reminder_email(task_title, end_date):
    sender_email = "your_email@gmail.com"
    sender_pass = "your_app_password"

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Pending Task Reminder: {task_title}"
    message["From"] = sender_email
    message["To"] = REMINDER_EMAIL

    text = f"Reminder: Task '{task_title}' is still pending. Complete by {end_date}."
    part1 = MIMEText(text, "plain")
    message.attach(part1)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, REMINDER_EMAIL, message.as_string())
    except Exception as e:
        print("Email send failed:", e)

def send_pending_reminders():
    users = load_users()
    today = date.today()
    for uname, data in users.items():
        for task in data.get("tasks", []):
            task_end = datetime.strptime(task["End"], "%Y-%m-%d").date()
            if task["Status"] != "Completed" and today <= task_end:
                send_reminder_email(task["Task"], task["End"])

# ------------------ Login ------------------
def login_page():
    st.title("🔐 Daily To-Do List — Login")
    users = load_users()
    col1, col2 = st.columns([2,1])
    with col1:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Login", use_container_width=True):
            if username in users and users[username]["password"]==password:
                st.session_state.logged = True
                st.session_state.user = username
                notify("Login successful", "success")
                st.rerun()
            else:
                notify("Invalid username or password", "error")
    with col2: st.write("")
    st.markdown("---")
    st.subheader("Create new account")
    new_user = st.text_input("New username", key="new_user")
    new_pass = st.text_input("New password", type="password", key="new_pass")
    if st.button("Create account", use_container_width=True):
        users = load_users()
        if not new_user.strip():
            notify("Username cannot be empty", "error")
        elif new_user in users:
            notify("User already exists", "warning")
        else:
            users[new_user] = DEFAULT_USER_STRUCT.copy()
            users[new_user]["password"] = new_pass
            save_users(users)
            notify("Account created — now login", "success")

# ------------------ Add Task ------------------
def add_task_page():
    inject_page_style()
    users = load_users()
    username = st.session_state.user
    tasks = users[username].get("tasks", [])

    st.header("➕ Add New Task")
    with st.form("add_form", clear_on_submit=True):
        title = st.text_input("Task Title")
        desc = st.text_area("Description")
        start = st.date_input("Start", date.today())
        end = st.date_input("End", date.today())
        priority = st.selectbox("Priority", ["High","Medium","Low"])
        assigned = st.text_input("Assigned By")
        submitted = st.form_submit_button("Save Task")
        if submitted:
            if not title.strip():
                notify("Task title required","error")
            else:
                task = {
                    "Task": title.strip(),
                    "Description": desc,
                    "Start": str(start),
                    "End": str(end),
                    "Status": "Pending",
                    "Priority": priority,
                    "AssignedBy": assigned,
                    "Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                users[username]["tasks"].insert(0, task)
                save_users(users)
                notify("Task saved","success")
                st.experimental_rerun()

# ------------------ Active Tasks ------------------
def task_list_page():
    inject_page_style()
    users = load_users()
    username = st.session_state.user
    tasks = users[username].get("tasks", [])
    completed = users[username].get("completed", [])
    st.header("📝 Active Tasks")
    if not tasks: st.info("No active tasks"); return

    for i, t in enumerate(tasks):
        pcolor = {"High":"🔴 Red", "Medium":"🟠 Orange", "Low":"🟢 Green"}[t.get("Priority","Low")]
        scolor = "blue" if t.get("Status")=="Running" else "orange"

        st.markdown(f"<div class='task-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='task-title'>{t.get('Task','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='task-info'>{t.get('Description','')}<br>"
                    f"Start: {t.get('Start','')} | End: {t.get('End','')}<br>"
                    f"<b>Status:</b> <span style='color:{scolor}'>{t.get('Status')}</span> | "
                    f"<b>Priority:</b> {pcolor} | "
                    f"<b>Assigned By:</b> {t.get('AssignedBy','-')}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        c1,c2,c3,c4 = st.columns(4)
        if c1.button("✏️ Edit", key=f"edit_{i}"):
            st.session_state.edit_idx = i
            st.experimental_rerun()
        if c2.button("🗑 Delete", key=f"del_{i}"):
            users = load_users()
            users[username]["tasks"].pop(i)
            save_users(users)
            notify("Task deleted", "warning")
            st.experimental_rerun()
        if c3.button("✔ Complete", key=f"comp_{i}"):
            users = load_users()
            task_obj = users[username]["tasks"].pop(i)
            task_obj["Status"]="Completed"
            task_obj["CompletedAt"]=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            users[username]["completed"].insert(0, task_obj)
            save_users(users)
            notify("Task moved to Completed","success")
            st.experimental_rerun()
        if c4.button("🏃 Running", key=f"run_{i}"):
            users = load_users()
            users[username]["tasks"][i]["Status"]="Running"
            save_users(users)
            notify("Task set to Running","info")
            st.experimental_rerun()

    # Edit form
    if "edit_idx" in st.session_state and st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        if idx>=len(users[username]["tasks"]): st.session_state.edit_idx=None
        else:
            t = users[username]["tasks"][idx]
            st.markdown("---")
            st.subheader("✏️ Edit Task")
            with st.form("edit_form"):
                nt = st.text_input("Title", t.get("Task",""))
                nd = st.text_area("Description", t.get("Description",""))
                ns = st.date_input("Start", value=date.fromisoformat(t.get("Start","2025-01-01")))
                ne = st.date_input("End", value=date.fromisoformat(t.get("End","2025-01-01")))
                np = st.selectbox("Priority", ["High","Medium","Low"], index=["High","Medium","Low"].index(t.get("Priority","Low")))
                na = st.text_input("Assigned By", t.get("AssignedBy",""))
                sv = st.form_submit_button("Save Changes")
                if sv:
                    users[username]["tasks"][idx] = {
                        "Task": nt, "Description": nd, "Start": str(ns), "End": str(ne),
                        "Status": t.get("Status","Pending"), "Priority": np,
                        "AssignedBy": na, "Created": t.get("Created", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    }
                    save_users(users)
                    notify("Task updated","success")
                    st.session_state.edit_idx=None
                    st.experimental_rerun()

# ------------------ Completed Tasks ------------------
def completed_page():
    inject_page_style()
    users = load_users()
    username = st.session_state.user
    completed = users[username].get("completed", [])
    st.header("✅ Completed Tasks")
    if not completed: st.info("No completed tasks yet."); return
    for t in completed:
        st.markdown("<div class='task-card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='task-title'>✅ {t.get('Task')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='task-info'>{t.get('Description','')}<br>"
                    f"Completed at: {t.get('CompletedAt','-')}<br>"
                    f"Priority: {t.get('Priority','-')} | Assigned By: {t.get('AssignedBy','-')}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------ CSV Export ------------------
def csv_page():
    users = load_users()
    username = st.session_state.user
    tasks = users[username].get("tasks", []) + users[username].get("completed", [])
    st.header("⬇ Export Tasks")
    if not tasks: st.info("No tasks"); return
    start = st.date_input("Start Date", date.today())
    end = st.date_input("End Date", date.today())
    filtered = [t for t in tasks if start <= date.fromisoformat(t["Start"]) <= end]
    if not filtered: st.info("No tasks in this range"); return
    df = pd.DataFrame(filtered)
    st.download_button("Download CSV", df.to_csv(index=False), "tasks.csv")

# ------------------ Password ------------------
def password_page():
    users = load_users()
    username = st.session_state.user
    st.header("🔑 Change Password")
    old = st.text_input("Old Password", type="password")
    new = st.text_input("New Password", type="password")
    c = st.text_input("Confirm New Password", type="password")
    if st.button("Update"):
        if users[username]["password"] != old:
            notify("Old password incorrect","error")
        elif new != c:
            notify("Passwords do not match","error")
        else:
            users[username]["password"]=new
            save_users(users)
            notify("Password updated","success")

# ------------------ Main ------------------
def main():
    if "logged" not in st.session_state: st.session_state.logged=False
    if "user" not in st.session_state: st.session_state.user=None
    if "edit_idx" not in st.session_state: st.session_state.edit_idx=None

    if not st.session_state.logged:
        login_page()
        return

    inject_page_style()
    st.sidebar.title("📌 Menu")
    menu_choice = st.sidebar.radio("", ["Add Task","Active Tasks","Completed Tasks","CSV Export","Change Password"])
    if st.sidebar.button("Logout"):
        st.session_state.logged=False
        st.session_state.user=None
        notify("Logged out","info")
        st.experimental_rerun()

    if menu_choice=="Add Task": add_task_page()
    elif menu_choice=="Active Tasks": task_list_page()
    elif menu_choice=="Completed Tasks": completed_page()
    elif menu_choice=="CSV Export": csv_page()
    elif menu_choice=="Change Password": password_page()

    # Send pending reminders (can be commented if not needed)
    send_pending_reminders()

if __name__=="__main__":
    main()
