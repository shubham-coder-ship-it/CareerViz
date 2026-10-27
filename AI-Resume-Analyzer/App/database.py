"""CareerViz database bootstrap; additive migration preserves existing records."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from dotenv import load_dotenv
from services import migrate
load_dotenv(Path(__file__).with_name('.env'))
DB_PATH = os.getenv('RESUME_DB_PATH', str(Path(__file__).with_name('resume_analyzer.db')))


@contextmanager
def transaction(conn):
    """Commit or rollback without closing the caller's connection."""
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
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

def ensure_history_columns():
    # Keep old saved-history fields readable without creating any training system.
    with get_connection() as conn:
        columns={row[1] for row in conn.execute('PRAGMA table_info(user_data)')}
        for name,kind in [('training_status',"TEXT DEFAULT 'NEW'"),('model_version_used','TEXT'),('last_modified','TEXT')]:
            if name not in columns:conn.execute('ALTER TABLE user_data ADD COLUMN '+name+' '+kind)


def initialize():
    init_db()
    ensure_history_columns()
    with get_connection() as conn:
        migrate(conn)
        if 'publication_consent' not in {r[1] for r in conn.execute('PRAGMA table_info(user_feedback)')}:
            conn.execute('ALTER TABLE user_feedback ADD COLUMN publication_consent INTEGER NOT NULL DEFAULT 0')
