import os
import sqlite3
import json
import uuid
import datetime
from typing import Optional
from contextlib import contextmanager
from .schema import Program

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge_gains.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database with required tables"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # wizard_answers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wizard_answers (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                answers TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # file_vectors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_vectors (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_text TEXT NOT NULL,
                embedding TEXT,
                ts TEXT NOT NULL
            )
        """)
        
        # routines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routines (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                routine_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # progress_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progress_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                routine_id TEXT NOT NULL,
                week INTEGER NOT NULL,
                day INTEGER NOT NULL,
                exercise_name TEXT NOT NULL,
                set_number INTEGER NOT NULL,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                ts TEXT NOT NULL
            )
        """)
        
        # completed_days table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS completed_days (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                routine_id TEXT NOT NULL,
                week INTEGER NOT NULL,
                day INTEGER NOT NULL,
                ts TEXT NOT NULL
            )
        """)
        
        conn.commit()


# Initialize database on import
init_db()


# ---------- wizard answers ----------
def save_answers(user_id: str, answer_dict: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if user already has answers
        cursor.execute(
            "SELECT id, answers FROM wizard_answers WHERE user_id = ?",
            (user_id,)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Merge new answers with existing ones
            current_answers = json.loads(existing["answers"]) if existing["answers"] else {}
            current_answers.update(answer_dict)
            cursor.execute(
                "UPDATE wizard_answers SET answers = ? WHERE user_id = ?",
                (json.dumps(current_answers), user_id)
            )
        else:
            # Insert new record
            cursor.execute(
                "INSERT INTO wizard_answers (id, user_id, answers) VALUES (?, ?, ?)",
                (str(uuid.uuid4()), user_id, json.dumps(answer_dict))
            )
        
        conn.commit()


def get_wizard_answers(user_id: str) -> Optional[dict]:
    """Get wizard answers for a user"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT answers FROM wizard_answers WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row["answers"])
        return None


# ---------- uploaded file vectors ----------
def store_uploaded_file(user_id: str, filename: str, text: str) -> str:
    fid = str(uuid.uuid4())
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO file_vectors (id, user_id, filename, file_text, embedding, ts)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                fid,
                user_id,
                filename,
                text,
                None,  # No embedding for now
                datetime.datetime.now(datetime.UTC).isoformat(),
            )
        )
        conn.commit()
    return fid


def latest_file_text(user_id: str) -> Optional[str]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT file_text FROM file_vectors 
               WHERE user_id = ? 
               ORDER BY ts DESC 
               LIMIT 1""",
            (user_id,)
        )
        row = cursor.fetchone()
        return row["file_text"] if row else None


# ---------- program persistence ----------
def save_program(user_id: str, program: Program, routine_id: str | None = None) -> str:
    if routine_id is None:
        routine_id = str(uuid.uuid4())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO routines (id, user_id, title, routine_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    routine_id,
                    user_id,
                    program.title,
                    program.model_dump_json(),
                    datetime.datetime.now(datetime.UTC).isoformat(),
                )
            )
            conn.commit()
    else:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE routines 
                   SET title = ?, routine_json = ? 
                   WHERE id = ?""",
                (program.title, program.model_dump_json(), routine_id)
            )
            conn.commit()
    return routine_id


def get_routine(routine_id: str) -> Optional[dict]:
    """Get routine by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT routine_json FROM routines WHERE id = ?",
            (routine_id,)
        )
        row = cursor.fetchone()
        if row:
            return {"routine_json": row["routine_json"]}
        return None


# ---------- logging ----------
def save_set_log(
    user_id: str,
    routine_id: str,
    week: int,
    day: int,
    exercise_name: str,
    set_number: int,
    weight: float,
    reps: int,
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO progress_logs 
               (id, user_id, routine_id, week, day, exercise_name, set_number, weight, reps, ts)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                user_id,
                routine_id,
                week,
                day,
                exercise_name,
                set_number,
                weight,
                reps,
                datetime.datetime.now(datetime.UTC).isoformat(),
            )
        )
        conn.commit()


def count_logged_sets(user_id: str, routine_id: str, week: int, day: int) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COUNT(*) as count FROM progress_logs 
               WHERE user_id = ? AND routine_id = ? AND week = ? AND day = ?""",
            (user_id, routine_id, week, day)
        )
        row = cursor.fetchone()
        return row["count"] if row else 0


def mark_day_finished(user_id: str, routine_id: str, week: int, day: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO completed_days (id, user_id, routine_id, week, day, ts)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                user_id,
                routine_id,
                week,
                day,
                datetime.datetime.now(datetime.UTC).isoformat(),
            )
        )
        conn.commit()


# Mock Supabase client for compatibility
class MockSupabaseClient:
    """Mock Supabase client that uses SQLite backend"""
    
    def table(self, table_name: str):
        return MockTable(table_name)


class MockTable:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self._filters = {}
        self._select_fields = "*"
    
    def select(self, fields: str = "*", count: str = None):
        self._select_fields = fields
        self._count = count
        return self
    
    def eq(self, field: str, value):
        self._filters[field] = value
        return self
    
    def single(self):
        self._single = True
        return self
    
    def execute(self):
        if self.table_name == "wizard_answers":
            if "user_id" in self._filters:
                answers = get_wizard_answers(self._filters["user_id"])
                if answers:
                    return MockResponse({"answers": answers})
        elif self.table_name == "routines":
            if "id" in self._filters:
                routine = get_routine(self._filters["id"])
                if routine:
                    return MockResponse(routine)
        
        return MockResponse(None)


class MockResponse:
    def __init__(self, data):
        self.data = data


# Create mock Supabase client instance
sb = MockSupabaseClient()
