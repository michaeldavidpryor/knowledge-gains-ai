import os
import uuid
import datetime
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from .schema import Program
from .openai_client import embed_text

load_dotenv()
sb: Client = create_client(
    os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)


# ---------- wizard answers ----------
def save_answers(user_id: str, answer_dict: dict):
    existing = (
        sb.table("wizard_answers")
        .select("id, answers")
        .eq("user_id", user_id)
        .single()
        .execute()
        .data
    )
    if existing:
        # Merge new answers with existing ones
        current_answers = existing["answers"] or {}
        current_answers.update(answer_dict)
        sb.table("wizard_answers").update({"answers": current_answers}).eq(
            "user_id", user_id
        ).execute()
    else:
        sb.table("wizard_answers").insert(
            {"id": str(uuid.uuid4()), "user_id": user_id, "answers": answer_dict}
        ).execute()


# ---------- uploaded file vectors ----------
def store_uploaded_file(user_id: str, filename: str, text: str) -> str:
    embedding = embed_text(text)
    fid = str(uuid.uuid4())
    sb.table("file_vectors").insert(
        {
            "id": fid,
            "user_id": user_id,
            "filename": filename,
            "file_text": text,
            "embedding": embedding,
            "ts": datetime.datetime.now(datetime.UTC).isoformat(),
        }
    ).execute()
    return fid


def latest_file_text(user_id: str) -> Optional[str]:
    res = (
        sb.table("file_vectors")
        .select("file_text")
        .eq("user_id", user_id)
        .order("ts", desc=True)
        .limit(1)
        .execute()
        .data
    )
    return res[0]["file_text"] if res else None


# ---------- program persistence ----------
def save_program(user_id: str, program: Program, routine_id: str | None = None) -> str:
    if routine_id is None:
        routine_id = str(uuid.uuid4())
        sb.table("routines").insert(
            {
                "id": routine_id,
                "user_id": user_id,
                "title": program.title,
                "routine_json": program.model_dump_json(),
                "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }
        ).execute()
    else:
        sb.table("routines").update(
            {
                "title": program.title,
                "routine_json": program.model_dump_json(),
            }
        ).eq("id", routine_id).execute()
    return routine_id


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
    sb.table("progress_logs").insert(
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "routine_id": routine_id,
            "week": week,
            "day": day,
            "exercise_name": exercise_name,
            "set_number": set_number,
            "weight": weight,
            "reps": reps,
            "ts": datetime.datetime.now(datetime.UTC).isoformat(),
        }
    ).execute()


def count_logged_sets(user_id: str, routine_id: str, week: int, day: int) -> int:
    res = (
        sb.table("progress_logs")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("routine_id", routine_id)
        .eq("week", week)
        .eq("day", day)
        .execute()
    )
    return res.count or 0


def mark_day_finished(user_id: str, routine_id: str, week: int, day: int):
    sb.table("completed_days").insert(
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "routine_id": routine_id,
            "week": week,
            "day": day,
            "ts": datetime.datetime.now(datetime.UTC).isoformat(),
        }
    ).execute()
