import os
import io
import re
import uuid
import shutil
import sqlite3
import zipfile
from datetime import datetime, date

import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Complete Student Management System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# CONSTANTS
# ============================================================

DB_FILE = "students.db"
PHOTO_FOLDER = "student_photos"
BACKUP_FOLDER = "backups"

os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)

COURSES = [
    "BCA",
    "B.Tech",
    "MCA",
    "MBA",
    "BBA",
    "B.Sc",
    "B.Com",
    "M.Tech",
    "BA",
    "MA",
    "Other"
]

GENDERS = ["Male", "Female", "Other"]

FEE_STATUS = ["Paid", "Pending", "Partial"]

SEMESTERS = [
    "1st Semester",
    "2nd Semester",
    "3rd Semester",
    "4th Semester",
    "5th Semester",
    "6th Semester",
    "7th Semester",
    "8th Semester"
]


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return sqlite3.connect(DB_FILE)


def create_database():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            dob TEXT,
            age INTEGER,
            student_class TEXT,
            gender TEXT,
            course TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT,
            parent_name TEXT,
            parent_phone TEXT,
            semester TEXT,
            fee_amount REAL DEFAULT 0,
            fee_paid REAL DEFAULT 0,
            fee_status TEXT,
            attendance REAL DEFAULT 0,
            subject1 REAL DEFAULT 0,
            subject2 REAL DEFAULT 0,
            subject3 REAL DEFAULT 0,
            subject4 REAL DEFAULT 0,
            subject5 REAL DEFAULT 0,
            photo TEXT,
            registration_date TEXT
        )
    """)

    conn.commit()
    conn.close()


create_database()


# ============================================================
# DATA FUNCTIONS
# ============================================================

def load_students():

    conn = get_connection()

    df = pd.read_sql_query(
        "SELECT * FROM students ORDER BY registration_date DESC",
        conn
    )

    conn.close()

    return df


def add_student(data):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO students (
            student_id, name, dob, age, student_class,
            gender, course, phone, email, address, city,
            state, pincode, parent_name, parent_phone,
            semester, fee_amount, fee_paid, fee_status,
            attendance, subject1, subject2, subject3,
            subject4, subject5, photo, registration_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tuple(data))

    conn.commit()
    conn.close()


def update_student(student_id, data):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE students SET
            name=?,
            dob=?,
            age=?,
            student_class=?,
            gender=?,
            course=?,
            phone=?,
            email=?,
            address=?,
            city=?,
            state=?,
            pincode=?,
            parent_name=?,
            parent_phone=?,
            semester=?,
            fee_amount=?,
            fee_paid=?,
            fee_status=?,
            attendance=?,
            subject1=?,
            subject2=?,
            subject3=?,
            subject4=?,
            subject5=?,
            photo=?
        WHERE student_id=?
    """, tuple(data) + (student_id,))

    conn.commit()
    conn.close()


def delete_student(student_id):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT photo FROM students WHERE student_id=?",
        (student_id,)
    )

    result = cur.fetchone()

    if result and result[0]:
        delete_photo(result[0])

    cur.execute(
        "DELETE FROM students WHERE student_id=?",
        (student_id,)
    )

    conn.commit()
    conn.close()


def get_student(student_id):

    conn = get_connection()

    df = pd.read_sql_query(
        "SELECT * FROM students WHERE student_id=?",
        conn,
        params=(student_id,)
    )

    conn.close()

    if df.empty:
        return None

    return df.iloc[0]


def generate_student_id():

    df = load_students()

    if df.empty:
        return "STU001"

    numbers = []

    for sid in df["student_id"].astype(str):

        match = re.match(r"STU(\d+)", sid)

        if match:
            numbers.append(int(match.group(1)))

    if not numbers:
        return "STU001"

    return f"STU{max(numbers) + 1:03d}"


# ============================================================
# VALIDATION
# ============================================================

def valid_phone(phone):

    return bool(
        re.fullmatch(r"[6-9]\d{9}", str(phone).strip())
    )


def valid_email(email):

    return bool(
        re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            str(email).strip()
        )
    )


def calculate_age(dob):

    if not dob:
        return 18

    try:
        dob_date = datetime.strptime(
            str(dob),
            "%Y-%m-%d"
        ).date()

        today = date.today()

        age = (
            today.year
            - dob_date.year
            - (
                (today.month, today.day)
                <
                (dob_date.month, dob_date.day)
            )
        )

        return age

    except:
        return 18


def calculate_percentage(row):

    marks = [
        row["subject1"],
        row["subject2"],
        row["subject3"],
        row["subject4"],
        row["subject5"]
    ]

    marks = pd.to_numeric(
        marks,
        errors="coerce"
    )

    return round(
        sum(marks) / 5,
        2
    )


def calculate_grade(percentage):

    if percentage >= 90:
        return "A+"
    elif percentage >= 80:
        return "A"
    elif percentage >= 70:
        return "B+"
    elif percentage >= 60:
        return "B"
    elif percentage >= 50:
        return "C"
    elif percentage >= 40:
        return "D"
    else:
        return "F"


def delete_photo(path):

    if path and os.path.exists(path):

        try:
            os.remove(path)
        except:
            pass


def save_photo(uploaded_file, student_id):

    if uploaded_file is None:
        return ""

    extension = os.path.splitext(
        uploaded_file.name
    )[1].lower()

    filename = (
        f"{student_id}_"
        f"{uuid.uuid4().hex[:8]}"
        f"{extension}"
    )

    path = os.path.join(
        PHOTO_FOLDER,
        filename
    )

    with open(path, "wb") as f:
        f.write(
            uploaded_file.getbuffer()
        )

    return path


# ============================================================
# SESSION STATE
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# ============================================================
# ADMIN LOGIN
# ============================================================

if not st.session_state.logged_in:

    st.title("🎓 Student Management System")

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        st.subheader("🔐 Admin Login")

        username = st.text_input(
            "Username"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        login = st.button(
            "🔓 Login",
            use_container_width=True
        )

        st.info(
            "Demo Login\n\n"
            "Username: admin\n\n"
            "Password: admin123"
        )

        if login:

            if (
                username == "admin"
                and password == "admin123"
            ):

                st.session_state.logged_in = True

                st.success(
                    "Login successful!"
                )

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )

    st.stop()


# ============================================================
# LOAD DATA
# ============================================================

df = load_students()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🎓 Student System")

st.sidebar.success(
    "Admin Logged In"
)

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "➕ Add Student",
        "👨‍🎓 All Students",
        "🔍 Search & Filter",
        "✏️ Edit Student",
        "🗑️ Delete Student",
        "👤 Student Profile",
        "📊 Marks & Attendance",
        "💰 Fee Management",
        "🪪 Student ID Card",
        "🧾 Fee Receipt",
        "📈 Reports",
        "💾 Backup & Restore",
        "📥 Export Data"
    ]
)

st.sidebar.markdown("---")

if st.sidebar.button(
    "🚪 Logout",
    use_container_width=True
):

    st.session_state.logged_in = False

    st.rerun()


# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.title("🏠 Dashboard")

    total = len(df)

    male = len(
        df[df["gender"] == "Male"]
    )

    female = len(
        df[df["gender"] == "Female"]
    )

    pending = len(
        df[
            df["fee_status"].isin(
                ["Pending", "Partial"]
            )
        ]
    )

    paid_amount = pd.to_numeric(
        df["fee_paid"],
        errors="coerce"
    ).fillna(0).sum()

    total_fee = pd.to_numeric(
        df["fee_amount"],
        errors="coerce"
    ).fillna(0).sum()

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "👨‍🎓 Students",
        total
    )

    c2.metric(
        "👨 Male",
        male
    )

    c3.metric(
        "👩 Female",
        female
    )

    c4.metric(
        "⏳ Fee Pending",
        pending
    )

    c5.metric(
        "💰 Fee Collected",
        f"₹{paid_amount:,.0f}"
    )

    st.markdown("---")

    if df.empty:

        st.info(
            "No students added yet."
        )

    else:

        col1, col2 = st.columns(2)

        with col1:

            st.subheader(
                "📚 Course-wise Students"
            )

            course_chart = (
                df["course"]
                .value_counts()
            )

            st.bar_chart(
                course_chart
            )

        with col2:

            st.subheader(
                "🏙️ City-wise Students"
            )

            city_chart = (
                df["city"]
                .value_counts()
            )

            st.bar_chart(
                city_chart
            )

        st.markdown("---")

        st.subheader(
            "💰 Fee Summary"
        )

        fc1, fc2, fc3 = st.columns(3)

        fc1.metric(
            "Total Fees",
            f"₹{total_fee:,.0f}"
        )

        fc2.metric(
            "Paid",
            f"₹{paid_amount:,.0f}"
        )

        fc3.metric(
            "Remaining",
            f"₹{total_fee - paid_amount:,.0f}"
        )


# ============================================================
# ADD STUDENT
# ============================================================

elif page == "➕ Add Student":

    st.title("➕ Add New Student")

    with st.form(
        "add_student",
        clear_on_submit=True
    ):

        st.subheader(
            "👤 Personal Details"
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            name = st.text_input(
                "Full Name *"
            )

        with c2:

            dob = st.date_input(
                "Date of Birth",
                value=date(
                    2005,
                    1,
                    1
                ),
                min_value=date(
                    1950,
                    1,
                    1
                ),
                max_value=date.today()
            )

        with c3:

            gender = st.selectbox(
                "Gender",
                GENDERS
            )

        c1, c2 = st.columns(2)

        with c1:

            student_class = st.text_input(
                "Class *",
                placeholder="12th"
            )

        with c2:

            course = st.selectbox(
                "Course",
                COURSES
            )

        st.subheader(
            "📞 Contact Details"
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            phone = st.text_input(
                "Phone *",
                max_chars=10
            )

        with c2:

            email = st.text_input(
                "Email *"
            )

        with c3:

            city = st.text_input(
                "City *",
                placeholder="Mathura"
            )

        address = st.text_area(
            "Address *"
        )

        c1, c2 = st.columns(2)

        with c1:

            state = st.text_input(
                "State",
                value="Uttar Pradesh"
            )

        with c2:

            pincode = st.text_input(
                "Pincode",
                max_chars=6
            )

        st.subheader(
            "👨‍👩‍👦 Parent Details"
        )

        c1, c2 = st.columns(2)

        with c1:

            parent_name = st.text_input(
                "Parent / Guardian Name"
            )

        with c2:

            parent_phone = st.text_input(
                "Parent Phone",
                max_chars=10
            )

        semester = st.selectbox(
            "Semester",
            SEMESTERS
        )

        st.subheader(
            "💰 Fee Details"
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            fee_amount = st.number_input(
                "Total Fee",
                min_value=0.0,
                step=500.0
            )

        with c2:

            fee_paid = st.number_input(
                "Paid Fee",
                min_value=0.0,
                step=500.0
            )

        with c3:

            fee_status = st.selectbox(
                "Fee Status",
                FEE_STATUS
            )

        st.subheader(
            "📊 Academic Details"
        )

        attendance = st.number_input(
            "Attendance %",
            min_value=0.0,
            max_value=100.0,
            value=75.0
        )

        m1, m2, m3, m4, m5 = st.columns(5)

        with m1:
            subject1 = st.number_input(
                "Subject 1",
                0.0,
                100.0,
                0.0
            )

        with m2:
            subject2 = st.number_input(
                "Subject 2",
                0.0,
                100.0,
                0.0
            )

        with m3:
            subject3 = st.number_input(
                "Subject 3",
                0.0,
                100.0,
                0.0
            )

        with m4:
            subject4 = st.number_input(
                "Subject 4",
                0.0,
                100.0,
                0.0
            )

        with m5:
            subject5 = st.number_input(
                "Subject 5",
                0.0,
                100.0,
                0.0
            )

        st.subheader(
            "📷 Photo"
        )

        photo = st.file_uploader(
            "Upload Student Photo",
            type=[
                "jpg",
                "jpeg",
                "png"
            ]
        )

        submit = st.form_submit_button(
            "💾 Save Student",
            use_container_width=True
        )

    if submit:

        if not name.strip():

            st.error(
                "Name is required."
            )

        elif not student_class.strip():

            st.error(
                "Class is required."
            )

        elif not valid_phone(phone):

            st.error(
                "Enter valid 10 digit phone number."
            )

        elif not valid_email(email):

            st.error(
                "Enter valid email."
            )

        elif not city.strip():

            st.error(
                "City is required."
            )

        elif not address.strip():

            st.error(
                "Address is required."
            )

        elif parent_phone.strip() and not valid_phone(
            parent_phone
        ):

            st.error(
                "Invalid parent phone number."
            )

        elif fee_paid > fee_amount:

            st.error(
                "Paid fee cannot be greater than total fee."
            )

        else:

            existing = df[
                df["phone"].astype(str)
                == phone.strip()
            ]

            if not existing.empty:

                st.warning(
                    "A student with this phone already exists."
                )

            else:

                student_id = generate_student_id()

                photo_path = save_photo(
                    photo,
                    student_id
                )

                registration_date = (
                    datetime.now()
                    .strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                data = [
                    student_id,
                    name.strip(),
                    dob.strftime("%Y-%m-%d"),
                    calculate_age(dob.strftime("%Y-%m-%d")),
                    student_class.strip(),
                    gender,
                    course,
                    phone.strip(),
                    email.strip(),
                    address.strip(),
                    city.strip(),
                    state.strip(),
                    pincode.strip(),
                    parent_name.strip(),
                    parent_phone.strip(),
                    semester,
                    fee_amount,
                    fee_paid,
                    fee_status,
                    attendance,
                    subject1,
                    subject2,
                    subject3,
                    subject4,
                    subject5,
                    photo_path,
                    registration_date
                ]

                add_student(data)

                st.success(
                    f"✅ {name} added successfully!"
                )

                st.info(
                    f"Student ID: **{student_id}**"
                )

                st.balloons()


# ============================================================
# ALL STUDENTS
# ============================================================

elif page == "👨‍🎓 All Students":

    st.title("👨‍🎓 All Students")

    if df.empty:

        st.info(
            "No student records."
        )

    else:

        st.write(
            f"Total Students: **{len(df)}**"
        )

        display_columns = [
            "student_id",
            "name",
            "age",
            "student_class",
            "gender",
            "course",
            "phone",
            "city",
            "attendance",
            "fee_status"
        ]

        st.dataframe(
            df[display_columns],
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# SEARCH & FILTER
# ============================================================

elif page == "🔍 Search & Filter":

    st.title("🔍 Search & Advanced Filters")

    if df.empty:

        st.info(
            "No records available."
        )

    else:

        search = st.text_input(
            "Search Name / ID / Phone / Email"
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            selected_course = st.selectbox(
                "Course",
                ["All"] + sorted(
                    df["course"]
                    .dropna()
                    .unique()
                    .tolist()
                )
            )

        with c2:

            selected_gender = st.selectbox(
                "Gender",
                ["All"] + GENDERS
            )

        with c3:

            selected_city = st.selectbox(
                "City",
                ["All"] + sorted(
                    df["city"]
                    .dropna()
                    .unique()
                    .tolist()
                )
            )

        with c4:

            selected_fee = st.selectbox(
                "Fee Status",
                ["All"] + FEE_STATUS
            )

        result = df.copy()

        if search.strip():

            q = search.lower()

            result = result[
                result[
                    [
                        "student_id",
                        "name",
                        "phone",
                        "email"
                    ]
                ]
                .astype(str)
                .apply(
                    lambda x:
                    x.str.lower().str.contains(
                        q,
                        na=False
                    )
                )
                .any(axis=1)
            ]

        if selected_course != "All":

            result = result[
                result["course"]
                == selected_course
            ]

        if selected_gender != "All":

            result = result[
                result["gender"]
                == selected_gender
            ]

        if selected_city != "All":

            result = result[
                result["city"]
                == selected_city
            ]

        if selected_fee != "All":

            result = result[
                result["fee_status"]
                == selected_fee
            ]

        st.write(
            f"Found: **{len(result)}** students"
        )

        st.dataframe(
            result,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# EDIT STUDENT
# ============================================================

elif page == "✏️ Edit Student":

    st.title("✏️ Edit Student")

    if df.empty:

        st.info(
            "No students available."
        )

    else:

        student_id = st.selectbox(
            "Select Student",
            df["student_id"].tolist()
        )

        student = get_student(
            student_id
        )

        if student is not None:

            with st.form(
                "edit_student"
            ):

                name = st.text_input(
                    "Name",
                    value=str(student["name"])
                )

                dob_value = date.today()

                try:
                    dob_value = datetime.strptime(
                        str(student["dob"]),
                        "%Y-%m-%d"
                    ).date()
                except:
                    pass

                dob = st.date_input(
                    "Date of Birth",
                    value=dob_value
                )

                c1, c2 = st.columns(2)

                with c1:

                    gender = st.selectbox(
                        "Gender",
                        GENDERS,
                        index=(
                            GENDERS.index(
                                student["gender"]
                            )
                            if student["gender"]
                            in GENDERS
                            else 0
                        )
                    )

                with c2:

                    course = st.selectbox(
                        "Course",
                        COURSES,
                        index=(
                            COURSES.index(
                                student["course"]
                            )
                            if student["course"]
                            in COURSES
                            else 0
                        )
                    )

                student_class = st.text_input(
                    "Class",
                    value=str(
                        student["student_class"]
                    )
                )

                c1, c2 = st.columns(2)

                with c1:

                    phone = st.text_input(
                        "Phone",
                        value=str(
                            student["phone"]
                        )
                    )

                with c2:

                    email = st.text_input(
                        "Email",
                        value=str(
                            student["email"]
                        )
                    )

                address = st.text_area(
                    "Address",
                    value=str(
                        student["address"]
                    )
                )

                c1, c2, c3 = st.columns(3)

                with c1:

                    city = st.text_input(
                        "City",
                        value=str(
                            student["city"]
                        )
                    )

                with c2:

                    state = st.text_input(
                        "State",
                        value=str(
                            student["state"]
                        )
                    )

                with c3:

                    pincode = st.text_input(
                        "Pincode",
                        value=str(
                            student["pincode"]
                        )
                    )

                c1, c2 = st.columns(2)

                with c1:

                    parent_name = st.text_input(
                        "Parent Name",
                        value=str(
                            student["parent_name"]
                        )
                    )

                with c2:

                    parent_phone = st.text_input(
                        "Parent Phone",
                        value=str(
                            student["parent_phone"]
                        )
                    )

                semester = st.selectbox(
                    "Semester",
                    SEMESTERS,
                    index=(
                        SEMESTERS.index(
                            student["semester"]
                        )
                        if student["semester"]
                        in SEMESTERS
                        else 0
                    )
                )

                c1, c2, c3 = st.columns(3)

                with c1:

                    fee_amount = st.number_input(
                        "Total Fee",
                        min_value=0.0,
                        value=float(
                            student["fee_amount"]
                        )
                    )

                with c2:

                    fee_paid = st.number_input(
                        "Paid Fee",
                        min_value=0.0,
                        value=float(
                            student["fee_paid"]
                        )
                    )

                with c3:

                    fee_status = st.selectbox(
                        "Fee Status",
                        FEE_STATUS,
                        index=(
                            FEE_STATUS.index(
                                student["fee_status"]
                            )
                            if student["fee_status"]
                            in FEE_STATUS
                            else 0
                        )
                    )

                attendance = st.number_input(
                    "Attendance %",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(
                        student["attendance"]
                    )
                )

                st.subheader(
                    "Marks"
                )

                m1, m2, m3, m4, m5 = st.columns(5)

                with m1:
                    subject1 = st.number_input(
                        "Subject 1",
                        0.0,
                        100.0,
                        float(student["subject1"])
                    )

                with m2:
                    subject2 = st.number_input(
                        "Subject 2",
                        0.0,
                        100.0,
                        float(student["subject2"])
                    )

                with m3:
                    subject3 = st.number_input(
                        "Subject 3",
                        0.0,
                        100.0,
                        float(student["subject3"])
                    )

                with m4:
                    subject4 = st.number_input(
                        "Subject 4",
                        0.0,
                        100.0,
                        float(student["subject4"])
                    )

                with m5:
                    subject5 = st.number_input(
                        "Subject 5",
                        0.0,
                        100.0,
                        float(student["subject5"])
                    )

                new_photo = st.file_uploader(
                    "Replace Photo",
                    type=[
                        "jpg",
                        "jpeg",
                        "png"
                    ]
                )

                update = st.form_submit_button(
                    "🔄 Update Student",
                    use_container_width=True
                )

            if update:

                if not valid_phone(phone):

                    st.error(
                        "Invalid phone number."
                    )

                elif not valid_email(email):

                    st.error(
                        "Invalid email."
                    )

                elif fee_paid > fee_amount:

                    st.error(
                        "Paid fee cannot exceed total fee."
                    )

                else:

                    old_photo = student["photo"]

                    if new_photo:

                        delete_photo(
                            old_photo
                        )

                        photo_path = save_photo(
                            new_photo,
                            student_id
                        )

                    else:

                        photo_path = old_photo

                    data = [
                        name.strip(),
                        dob.strftime(
                            "%Y-%m-%d"
                        ),
                        calculate_age(
                            dob.strftime(
                                "%Y-%m-%d"
                            )
                        ),
                        student_class.strip(),
                        gender,
                        course,
                        phone.strip(),
                        email.strip(),
                        address.strip(),
                        city.strip(),
                        state.strip(),
                        pincode.strip(),
                        parent_name.strip(),
                        parent_phone.strip(),
                        semester,
                        fee_amount,
                        fee_paid,
                        fee_status,
                        attendance,
                        subject1,
                        subject2,
                        subject3,
                        subject4,
                        subject5,
                        photo_path
                    ]

                    update_student(
                        student_id,
                        data
                    )

                    st.success(
                        "✅ Student updated successfully!"
                    )


# ============================================================
# DELETE
# ============================================================

elif page == "🗑️ Delete Student":

    st.title("🗑️ Delete Student")

    if df.empty:

        st.info(
            "No records."
        )

    else:

        student_id = st.selectbox(
            "Select Student",
            df["student_id"].tolist()
        )

        student = get_student(
            student_id
        )

        if student is not None:

            st.warning(
                f"Student: {student['name']}"
            )

            st.write(
                f"ID: **{student['student_id']}**"
            )

            confirm = st.checkbox(
                "I confirm permanent deletion."
            )

            if st.button(
                "🗑️ Delete",
                type="primary"
            ):

                if confirm:

                    delete_student(
                        student_id
                    )

                    st.success(
                        "Student deleted successfully."
                    )

                    st.rerun()

                else:

                    st.error(
                        "Please confirm deletion."
                    )


# ============================================================
# STUDENT PROFILE
# ============================================================

elif page == "👤 Student Profile":

    st.title("👤 Student Profile")

    if df.empty:

        st.info(
            "No students available."
        )

    else:

        student_id = st.selectbox(
            "Select Student",
            df["student_id"].tolist()
        )

        student = get_student(
            student_id
        )

        if student is not None:

            c1, c2 = st.columns(
                [1, 3]
            )

            with c1:

                if (
                    student["photo"]
                    and os.path.exists(
                        student["photo"]
                    )
                ):

                    st.image(
                        student["photo"],
                        width=180
                    )

                else:

                    st.info(
                        "No Photo"
                    )

            with c2:

                st.header(
                    student["name"]
                )

                st.write(
                    f"**Student ID:** {student['student_id']}"
                )

                st.write(
                    f"**Course:** {student['course']}"
                )

                st.write(
                    f"**Class:** {student['student_class']}"
                )

                st.write(
                    f"**Phone:** {student['phone']}"
                )

                st.write(
                    f"**Email:** {student['email']}"
                )

            st.markdown("---")

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Age",
                student["age"]
            )

            c2.metric(
                "Attendance",
                f"{student['attendance']}%"
            )

            c3.metric(
                "Fee Status",
                student["fee_status"]
            )

            st.subheader(
                "📍 Address"
            )

            st.write(
                f"{student['address']}, "
                f"{student['city']}, "
                f"{student['state']} - "
                f"{student['pincode']}"
            )

            st.subheader(
                "👨‍👩‍👦 Parent"
            )

            st.write(
                f"Name: {student['parent_name']}"
            )

            st.write(
                f"Phone: {student['parent_phone']}"
            )

            st.subheader(
                "📊 Academic Result"
            )

            percentage = calculate_percentage(
                student
            )

            grade = calculate_grade(
                percentage
            )

            a, b = st.columns(2)

            a.metric(
                "Percentage",
                f"{percentage}%"
            )

            b.metric(
                "Grade",
                grade
            )


# ============================================================
# MARKS & ATTENDANCE
# ============================================================

elif page == "📊 Marks & Attendance":

    st.title(
        "📊 Marks & Attendance Management"
    )

    if df.empty:

        st.info(
            "No student data."
        )

    else:

        student_id = st.selectbox(
            "Select Student",
            df["student_id"].tolist()
        )

        student = get_student(
            student_id
        )

        percentage = calculate_percentage(
            student
        )

        grade = calculate_grade(
            percentage
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Attendance",
            f"{student['attendance']}%"
        )

        c2.metric(
            "Percentage",
            f"{percentage}%"
        )

        c3.metric(
            "Grade",
            grade
        )

        st.markdown("---")

        marks_df = pd.DataFrame({
            "Subject": [
                "Subject 1",
                "Subject 2",
                "Subject 3",
                "Subject 4",
                "Subject 5"
            ],
            "Marks": [
                student["subject1"],
                student["subject2"],
                student["subject3"],
                student["subject4"],
                student["subject5"]
            ]
        })

        st.dataframe(
            marks_df,
            use_container_width=True,
            hide_index=True
        )

        st.bar_chart(
            marks_df.set_index(
                "Subject"
            )
        )

        if float(student["attendance"]) < 75:

            st.warning(
                "⚠️ Attendance is below 75%."
            )

        if grade == "F":

            st.error(
                "⚠️ Student needs academic improvement."
            )


# ============================================================
# FEE MANAGEMENT
# ============================================================

elif page == "💰 Fee Management":

    st.title(
        "💰 Fee Management"
    )

    if df.empty:

        st.info(
            "No student records."
        )

    else:

        total_fee = pd.to_numeric(
            df["fee_amount"],
            errors="coerce"
        ).fillna(0).sum()

        paid_fee = pd.to_numeric(
            df["fee_paid"],
            errors="coerce"
        ).fillna(0).sum()

        remaining = (
            total_fee
            - paid_fee
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Total Fee",
            f"₹{total_fee:,.0f}"
        )

        c2.metric(
            "Paid",
            f"₹{paid_fee:,.0f}"
        )

        c3.metric(
            "Remaining",
            f"₹{remaining:,.0f}"
        )

        st.markdown("---")

        fee_table = df[
            [
                "student_id",
                "name",
                "course",
                "fee_amount",
                "fee_paid",
                "fee_status"
            ]
        ].copy()

        fee_table["Remaining"] = (
            pd.to_numeric(
                fee_table["fee_amount"],
                errors="coerce"
            ).fillna(0)
            -
            pd.to_numeric(
                fee_table["fee_paid"],
                errors="coerce"
            ).fillna(0)
        )

        st.dataframe(
            fee_table,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# STUDENT ID CARD
# ============================================================

elif page == "🪪 Student ID Card":

    st.title(
        "🪪 Student ID Card"
    )

    if df.empty:

        st.info(
            "No students available."
        )

    else:

        student_id = st.selectbox(
            "Select Student",
            df["student_id"].tolist()
        )

        student = get_student(
            student_id
        )

        st.markdown(
            """
            <style>
            .id-card {
                border: 2px solid #333;
                border-radius: 15px;
                padding: 25px;
                max-width: 650px;
                margin: auto;
            }
            .id-title {
                text-align: center;
                font-size: 28px;
                font-weight: bold;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        photo_html = ""

        if (
            student["photo"]
            and os.path.exists(
                student["photo"]
            )
        ):

            import base64

            with open(
                student["photo"],
                "rb"
            ) as f:

                image_data = base64.b64encode(
                    f.read()
                ).decode()

            photo_html = (
                f'<img src="data:image/jpeg;base64,'
                f'{image_data}" width="130">'
            )

        st.markdown(
            f"""
            <div class="id-card">
                <div class="id-title">
                    🎓 STUDENT ID CARD
                </div>
                <hr>
                <center>{photo_html}</center>
                <h2>{student['name']}</h2>
                <p><b>ID:</b> {student['student_id']}</p>
                <p><b>Course:</b> {student['course']}</p>
                <p><b>Class:</b> {student['student_class']}</p>
                <p><b>Phone:</b> {student['phone']}</p>
                <p><b>City:</b> {student['city']}</p>
                <p><b>Semester:</b> {student['semester']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.info(
            "Browser ke Print option se ID card print/save as PDF kiya ja sakta hai."
        )


# ============================================================
# FEE RECEIPT
# ============================================================

elif page == "🧾 Fee Receipt":

    st.title(
        "🧾 Fee Receipt"
    )

    if df.empty:

        st.info(
            "No students available."
        )

    else:

        student_id = st.selectbox(
            "Select Student",
            df["student_id"].tolist()
        )

        student = get_student(
            student_id
        )

        remaining = (
            float(student["fee_amount"])
            -
            float(student["fee_paid"])
        )

        st.markdown("---")

        st.subheader(
            "🎓 STUDENT FEE RECEIPT"
        )

        c1, c2 = st.columns(2)

        with c1:

            st.write(
                f"**Student Name:** {student['name']}"
            )

            st.write(
                f"**Student ID:** {student['student_id']}"
            )

            st.write(
                f"**Course:** {student['course']}"
            )

        with c2:

            st.write(
                f"**Date:** {datetime.now().strftime('%d-%m-%Y')}"
            )

            st.write(
                f"**Class:** {student['student_class']}"
            )

            st.write(
                f"**Status:** {student['fee_status']}"
            )

        st.markdown("---")

        receipt_df = pd.DataFrame({
            "Description": [
                "Total Fee",
                "Paid Fee",
                "Remaining Fee"
            ],
            "Amount": [
                f"₹{float(student['fee_amount']):,.2f}",
                f"₹{float(student['fee_paid']):,.2f}",
                f"₹{remaining:,.2f}"
            ]
        })

        st.table(
            receipt_df
        )

        st.success(
            "Receipt ready. Use browser Print → Save as PDF."
        )


# ============================================================
# REPORTS
# ============================================================

elif page == "📈 Reports":

    st.title(
        "📈 Reports & Analytics"
    )

    if df.empty:

        st.info(
            "No data available."
        )

    else:

        st.subheader(
            "📚 Course Report"
        )

        course_data = (
            df["course"]
            .value_counts()
            .rename_axis("Course")
            .reset_index(
                name="Students"
            )
        )

        st.dataframe(
            course_data,
            use_container_width=True,
            hide_index=True
        )

        st.bar_chart(
            course_data.set_index(
                "Course"
            )
        )

        st.markdown("---")

        st.subheader(
            "🏙️ City Report"
        )

        city_data = (
            df["city"]
            .value_counts()
            .rename_axis("City")
            .reset_index(
                name="Students"
            )
        )

        st.dataframe(
            city_data,
            use_container_width=True,
            hide_index=True
        )

        st.bar_chart(
            city_data.set_index(
                "City"
            )
        )

        st.markdown("---")

        st.subheader(
            "👤 Gender Report"
        )

        gender_data = (
            df["gender"]
            .value_counts()
        )

        st.bar_chart(
            gender_data
        )

        st.markdown("---")

        st.subheader(
            "💰 Fee Status Report"
        )

        fee_data = (
            df["fee_status"]
            .value_counts()
        )

        st.bar_chart(
            fee_data
        )


# ============================================================
# BACKUP & RESTORE
# ============================================================

elif page == "💾 Backup & Restore":

    st.title(
        "💾 Backup & Restore"
    )

    st.subheader(
        "Create Backup"
    )

    if st.button(
        "📦 Create Full Backup"
    ):

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_name = (
            f"student_backup_{timestamp}.zip"
        )

        backup_path = os.path.join(
            BACKUP_FOLDER,
            backup_name
        )

        with zipfile.ZipFile(
            backup_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_file:

            if os.path.exists(DB_FILE):

                zip_file.write(
                    DB_FILE
                )

            if os.path.exists(
                PHOTO_FOLDER
            ):

                for root, dirs, files in os.walk(
                    PHOTO_FOLDER
                ):

                    for file in files:

                        path = os.path.join(
                            root,
                            file
                        )

                        zip_file.write(
                            path
                        )

        with open(
            backup_path,
            "rb"
        ) as f:

            st.download_button(
                "⬇️ Download Backup",
                data=f.read(),
                file_name=backup_name,
                mime="application/zip"
            )

        st.success(
            "Backup created successfully."
        )

    st.markdown("---")

    st.subheader(
        "Restore Backup"
    )

    uploaded_backup = st.file_uploader(
        "Upload ZIP Backup",
        type=["zip"]
    )

    if uploaded_backup:

        if st.button(
            "♻️ Restore Backup"
        ):

            try:

                temp_dir = "restore_temp"

                if os.path.exists(
                    temp_dir
                ):

                    shutil.rmtree(
                        temp_dir
                    )

                os.makedirs(
                    temp_dir
                )

                zip_path = os.path.join(
                    temp_dir,
                    "backup.zip"
                )

                with open(
                    zip_path,
                    "wb"
                ) as f:

                    f.write(
                        uploaded_backup.getbuffer()
                    )

                with zipfile.ZipFile(
                    zip_path,
                    "r"
                ) as zip_file:

                    zip_file.extractall(
                        temp_dir
                    )

                restored_db = os.path.join(
                    temp_dir,
                    DB_FILE
                )

                if os.path.exists(
                    restored_db
                ):

                    shutil.copy2(
                        restored_db,
                        DB_FILE
                    )

                restored_photos = os.path.join(
                    temp_dir,
                    PHOTO_FOLDER
                )

                if os.path.exists(
                    restored_photos
                ):

                    os.makedirs(
                        PHOTO_FOLDER,
                        exist_ok=True
                    )

                    for file in os.listdir(
                        restored_photos
                    ):

                        shutil.copy2(
                            os.path.join(
                                restored_photos,
                                file
                            ),
                            os.path.join(
                                PHOTO_FOLDER,
                                file
                            )
                        )

                shutil.rmtree(
                    temp_dir
                )

                st.success(
                    "Backup restored successfully."
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"Restore failed: {e}"
                )


# ============================================================
# EXPORT DATA
# ============================================================

elif page == "📥 Export Data":

    st.title(
        "📥 Export Student Data"
    )

    if df.empty:

        st.info(
            "No data available."
        )

    else:

        st.subheader(
            "📄 CSV"
        )

        csv_data = df.to_csv(
            index=False
        ).encode(
            "utf-8"
        )

        st.download_button(
            "⬇️ Download CSV",
            csv_data,
            "students.csv",
            "text/csv",
            use_container_width=True
        )

        st.markdown("---")

        st.subheader(
            "📊 Excel"
        )

        excel_buffer = io.BytesIO()

        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl"
        ) as writer:

            df.to_excel(
                writer,
                index=False,
                sheet_name="Students"
            )

        st.download_button(
            "⬇️ Download Excel",
            excel_buffer.getvalue(),
            "students.xlsx",
            (
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            use_container_width=True
        )

        st.markdown("---")

        st.subheader(
            "📱 WhatsApp"
        )

        student_id = st.selectbox(
            "Select Student for WhatsApp",
            df["student_id"].tolist(),
            key="whatsapp_student"
        )

        student = get_student(
            student_id
        )

        message = (
            f"Student Details%0A"
            f"Name: {student['name']}%0A"
            f"Student ID: {student['student_id']}%0A"
            f"Course: {student['course']}%0A"
            f"Class: {student['student_class']}%0A"
            f"Fee Status: {student['fee_status']}"
        )

        phone = str(
            student["phone"]
        )

        whatsapp_url = (
            f"https://wa.me/91{phone}"
            f"?text={message}"
        )

        st.markdown(
            f"""
            <a href="{whatsapp_url}" target="_blank">
                <button style="
                    padding:12px 25px;
                    border-radius:8px;
                    border:none;
                    cursor:pointer;
                    font-size:16px;
                ">
                📱 Open WhatsApp
                </button>
            </a>
            """,
            unsafe_allow_html=True
        )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.markdown("---")

st.sidebar.caption(
    "🎓 Complete Student Management System"
)

st.sidebar.caption(
    "© 2026"
)