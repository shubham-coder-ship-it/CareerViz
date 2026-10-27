###### AI Resume Analyzer - Streamlit Application ######


###### Packages Used ######
import streamlit as st # core package used in this project
import pandas as pd
import base64
import time,datetime
import sqlite3
import json
import os
import secrets
from dotenv import load_dotenv

# pre stored data for prediction purposes

# Front-end presentation layer (CSS theme, top nav, hero, loading animations,
# admin tables) — purely visual, no backend logic
from theme import inject_theme, render_navbar, render_admin_table, render_comments_table, render_kpi_row, chart_bar_counts, chart_donut, chart_score_donut, chart_line_over_time, render_stat_row, render_value_card, render_feedback_received, group_other, mask_ip, chart_heatmap, chart_training_metrics, render_model_network_viz, render_model_comparison_card
# Load environment variables from .env (see .env.example)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))


###### Preprocessing functions ######


# Generates a link allowing the data in a given panda dataframe to be downloaded in csv format
from services import migrate, verify_password, require_admin
def get_csv_download_link(df,filename,text):
    csv = df.to_csv(index=False)
    ## bytes conversions
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href




###### Database Stuffs (SQLite - no server required) ######


DB_PATH = os.getenv('RESUME_DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resume_analyzer.db'))

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def get_connection():
    """Return a new SQLite connection (thread-safe, file-based)."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't already exist."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS user_data (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        sec_token TEXT NOT NULL,
        ip_add TEXT,
        host_name TEXT,
        dev_user TEXT,
        os_name_ver TEXT,
        latlong TEXT,
        city TEXT,
        state TEXT,
        country TEXT,
        act_name TEXT NOT NULL,
        act_mail TEXT NOT NULL,
        act_mob TEXT NOT NULL,
        Name TEXT NOT NULL,
        Email_ID TEXT NOT NULL,
        resume_score TEXT NOT NULL,
        Timestamp TEXT NOT NULL,
        Page_no TEXT NOT NULL,
        Predicted_Field TEXT NOT NULL,
        User_level TEXT NOT NULL,
        Actual_skills TEXT NOT NULL,
        Recommended_skills TEXT NOT NULL,
        Recommended_courses TEXT NOT NULL,
        pdf_name TEXT NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_feedback (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        feed_name TEXT NOT NULL,
        feed_email TEXT NOT NULL,
        feed_score TEXT NOT NULL,
        comments TEXT,
        Timestamp TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()


# inserting miscellaneous data, fetched results, prediction and recommendation into user_data table
def insert_data(sec_token,ip_add,host_name,dev_user,os_name_ver,latlong,city,state,country,act_name,act_mail,act_mob,name,email,res_score,timestamp,no_of_pages,reco_field,cand_level,skills,recommended_skills,courses,pdf_name):
    conn = get_connection()
    c = conn.cursor()
    # Named-column insert (rather than a fixed positional VALUES list) so
    # this keeps working even though init_ml_tables() adds extra columns
    # to user_data via ALTER TABLE. New rows start life as 'NEW' --
    # un-reviewed training data -- for the human-in-the-loop ML workflow.
    insert_sql = """INSERT INTO user_data (
        sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state, country,
        act_name, act_mail, act_mob, Name, Email_ID, resume_score, Timestamp, Page_no,
        Predicted_Field, User_level, Actual_skills, Recommended_skills, Recommended_courses,
        pdf_name, training_status
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    rec_values = (str(sec_token),str(ip_add),host_name,dev_user,os_name_ver,str(latlong),city,state,country,act_name,act_mail,act_mob,name,email,str(res_score),timestamp,str(no_of_pages),reco_field,cand_level,skills,recommended_skills,courses,pdf_name,'NEW')
    c.execute(insert_sql, rec_values)
    conn.commit()
    conn.close()


# inserting feedback data into user_feedback table
def insertf_data(feed_name,feed_email,feed_score,comments,Timestamp):
    conn = get_connection()
    c = conn.cursor()
    insertfeed_sql = """INSERT INTO user_feedback(feed_name,feed_email,feed_score,comments,Timestamp) VALUES (?,?,?,?,?)"""
    rec_values = (feed_name, feed_email, feed_score, comments, Timestamp)
    c.execute(insertfeed_sql, rec_values)
    conn.execute('UPDATE user_feedback SET analysis_id=? WHERE ID=?', (st.session_state.get('_saved_analysis_id'), c.lastrowid))
    conn.commit()
    conn.close()


# deleting one or more rows by ID from either admin-managed table.
# table name is never taken from user input — only these two literals are
# ever passed in from App.py's own admin-section code.
_DELETABLE_TABLES = {'user_data', 'user_feedback'}

def delete_records(table, ids):
    require_admin()
    """Permanently delete the given IDs from `table`. Returns rows deleted."""
    if table not in _DELETABLE_TABLES or not ids:
        return 0
    ids = [int(i) for i in ids]
    conn = get_connection()
    c = conn.cursor()
    placeholders = ','.join('?' for _ in ids)
    c.execute(f'DELETE FROM {table} WHERE ID IN ({placeholders})', ids)
    conn.commit()
    deleted = c.rowcount
    conn.close()
    return deleted


# Column names can't be parameterized in SQL, so any column an edit form
# is allowed to write to is validated against this fixed allow-list —
# never built from user/frontend input. Deliberately excludes
# auto-generated/analysis-output columns (score, skills, tokens,
# timestamps, IP, geolocation) — only the identifying/profile-ish fields
# an admin would plausibly need to correct are editable.
_EDITABLE_COLUMNS = {
    'user_data': {'act_name', 'act_mail', 'act_mob', 'Predicted_Field', 'User_level', 'Actual_skills', 'resume_score', 'city', 'state', 'country'},
    'user_feedback': {'feed_name', 'feed_email', 'feed_score', 'comments'},
}


def update_record(table, record_id, fields):
    require_admin()
    """
    Update one row's whitelisted columns by ID. `fields` is a
    {db_column: new_value} dict; any key not in _EDITABLE_COLUMNS[table]
    is silently dropped rather than risking an injected column name.
    Returns True if a row was actually updated.
    """
    if table not in _EDITABLE_COLUMNS or not record_id:
        return False
    allowed = _EDITABLE_COLUMNS[table]
    safe_fields = {k: v for k, v in fields.items() if k in allowed}
    if not safe_fields:
        return False
    conn = get_connection()
    c = conn.cursor()
    if table == 'user_data':
        # Editing a row is the human-in-the-loop labeling/correction step
        # the ML workflow depends on, so every edit stamps last_modified.
        # If the row had already been used in a past training run, flip it
        # back to EDITED so it's picked up as "changed since last trained"
        # rather than silently staying marked USED with stale data.
        safe_fields = dict(safe_fields)
        safe_fields['last_modified'] = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')
        current = c.execute('SELECT training_status FROM user_data WHERE ID = ?', (int(record_id),)).fetchone()
        if current and current[0] == 'USED':
            safe_fields['training_status'] = 'EDITED'
    set_clause = ', '.join(f'{col} = ?' for col in safe_fields)
    values = list(safe_fields.values()) + [int(record_id)]
    c.execute(f'UPDATE {table} SET {set_clause} WHERE ID = ?', values)
    conn.commit()
    updated = c.rowcount > 0
    conn.close()
    return updated


from database import get_connection

###### Setting Page Configuration (favicon, Logo, Title) ######

logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Logo', 'recommend.png')
if os.path.exists(logo_path):
    st.set_page_config(
       page_title="CareerViz",
       page_icon=logo_path,
    )
else:
    st.set_page_config(
       page_title="CareerViz",
       page_icon='📄',
    )


###### Main function run() ######



@st.cache_resource(show_spinner=False)
def initialize_database(path):
    from database import initialize
    initialize()
    return path


def run():
    initialize_database(DB_PATH)

    # Global stylesheet (front-end only)
    inject_theme()
    from visual_refresh import inject_refresh
    inject_refresh()

    # Verification is public and bypasses private analysis/admin rendering.
    if 'verify' in st.query_params:
        from certificate_verification import render_verification_page
        with get_connection() as verification_conn:
            render_verification_page(verification_conn)
        return

    # Top navigation (replaces the old sidebar selectbox, same 4 destinations
    # plus a MORE menu). Returns one of: User / Feedback / Admin / About.
    choice = render_navbar()


    ###### CODE FOR CLIENT SIDE (USER) ######

    if choice == 'User':
        st.session_state.setdefault('_analysis_owner', secrets.token_urlsafe(32))
        from user_page import render_user_page
        render_user_page(get_connection)
        with st.expander("Resume format examples"):
            from resume_examples import render_examples
            render_examples()


    ###### CODE FOR FEEDBACK SIDE ######
    elif choice == 'Feedback':

        # timestamp
        ts = time.time()
        cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
        timestamp = str(cur_date+'_'+cur_time)

        # Feedback Form
        with st.form("my_form"):
            st.write("Feedback form")
            feed_name = st.text_input('Name')
            feed_email = st.text_input('Email')
            feed_score = st.slider('Rate Us From 1 - 5', 1, 5)
            comments = st.text_input('Comments')
            Timestamp = timestamp
            submitted = st.form_submit_button("Submit")
            if submitted:
                # Security input validation
                clean_name = feed_name.strip()
                clean_email = feed_email.strip()
                clean_comments = comments.strip()[:1000]

                if not clean_name:
                    st.error("Please provide your name before submitting.")
                elif clean_email and ('@' not in clean_email or '.' not in clean_email):
                    st.error("Please enter a valid email address.")
                else:
                    ## Calling insertf_data to add dat into user feedback
                    insertf_data(clean_name, clean_email, str(feed_score), clean_comments, Timestamp)
                    ## Success Message
                    st.success("Thanks! Your Feedback was recorded.")
                    ## On Successful Submit — a feedback-specific animation
                    ## instead of the generic celebratory balloons
                    render_feedback_received()


        # query to fetch data from user feedback table
        conn = get_connection()
        plotfeed_data = pd.read_sql_query('SELECT * FROM user_feedback', conn)
        conn.close()


        # fetching feed_score from the query and getting the unique values and total value count
        st.subheader("**Past User Rating's**")
        if not plotfeed_data.empty:
            # reindex across all 5 ratings so a rating nobody gave yet still
            # shows honestly as 0 / 0% in the legend, rather than vanishing
            rating_counts = plotfeed_data.feed_score.astype(int).value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)
            rating_counts.index = [f'{i} \u2605' for i in rating_counts.index]
            st.plotly_chart(
                chart_donut(rating_counts, 'Rating Distribution (1\u20135)', hover_label='Rating'),
                theme=None, key='chart_feedback_ratings',
            )
        else:
            st.markdown('<div class="ara-empty">No feedback available yet.</div>', unsafe_allow_html=True)

        #  Fetching Comment History
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 'Anonymous', comments FROM user_feedback WHERE published=1")
        plfeed_cmt_data = cursor.fetchall()
        conn.close()

        render_comments_table([(row[0], row[1]) for row in plfeed_cmt_data])


    ###### CODE FOR ABOUT PAGE ######
    elif choice == 'About':
        st.header('About CareerViz')
        st.markdown("""
CareerViz uses your supplied reference dataset to compare resume skills with career
fields. There is no model training, scaling, activation or dataset configuration.

**User:** upload an original PDF, DOCX or PNG/JPG resume, fill missing contact details, and click
Analyze Resume. Read your score breakdown, career matches and improvement tips.
The score uses the same transparent content rubric for every resume. Career matching
uses skill patterns in the reference dataset, with term rules when evidence is limited.

**Admin:** sign in to see reference data, career-field charts and saved user analyses.
Use Pin and moderate feedback to organize or review comments for publication.
Use Verify certificate to check a certificate code. No technical setup is required.

**Resume format examples:** browse complete fictional resumes and downloadable formats.
Include your name, contact links, a focused summary, relevant skills, education,
experience/internships or projects, achievements and relevant certifications.
Use real dates and measurable results; never copy fictional achievements as your own.
The score filters also show weaker drafts so you can understand what is missing.

**Scoring (review-v3):** projects 25, experience 20, demonstrated skills 15,
education 10, summary/targeting 10, formatting 10, certifications 5 and supporting
evidence 5 points. Detailed contributions, genuine outcomes and non-placeholder
links matter more than section presence. Guided training is not treated as equivalent
to evidenced work outcomes. The score uses reproducible text signals and cannot
verify claims or reproduce a subjective reviewer exactly. Scores are assessments, not
universal ATS approval, accreditation or employment guarantees.

Reference resumes stay private; the public examples use fictional details.
Certificate links need PUBLIC_APP_URL configured for access beyond this computer.
""")

    ###### CODE FOR ADMIN SIDE (ADMIN) ######
    else:
        from simple_admin import render_admin
        render_admin(get_connection)

if __name__ == '__main__':
    run()
