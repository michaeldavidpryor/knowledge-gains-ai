import os
import uuid
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from .schema import Program
from .openai_client import generate_program
from .supabase_client import (
    save_answers,
    save_program,
    save_set_log,
    count_logged_sets,
    mark_day_finished,
    store_uploaded_file,
    latest_file_text,
    sb,
)

load_dotenv()
app = FastAPI(title="Hypertrophy-Wizard")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)


# ---------- helpers ----------
def user_id(request: Request) -> str:
    if "user_id" not in request.session:
        request.session["user_id"] = str(uuid.uuid4())
    return request.session["user_id"]


def fetch_program(routine_id: str) -> Program:
    row = (
        sb.table("routines")
        .select("routine_json")
        .eq("id", routine_id)
        .single()
        .execute()
        .data
    )
    return Program.model_validate_json(row["routine_json"])


# ---------- wizard ----------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/goals", response_class=HTMLResponse)
async def handle_goals(
    request: Request,
    goals: str = Form(...),
    program_ref: str | None = Form(None),
    import_file: UploadFile | None = File(None),
):
    uid = user_id(request)
    file_text = None
    if import_file:
        file_bytes = await import_file.read()
        try:
            file_text = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            file_text = file_bytes.decode('utf-8', errors='ignore')
        # Remove null bytes which PostgreSQL can't handle
        file_text = file_text.replace('\x00', '')
        # Truncate to ~50K chars to avoid token limits (roughly 200K tokens)
        if len(file_text) > 50000:
            file_text = file_text[:50000] + "\n\n[FILE TRUNCATED - Original file was too large]"
        store_uploaded_file(uid, import_file.filename, file_text)
    save_answers(
        uid,
        {"goals": goals, "program_ref": program_ref, "import_file": bool(file_text)},
    )
    return templates.TemplateResponse("equipment.html", {"request": request})


@app.post("/equipment", response_class=HTMLResponse)
async def handle_equipment(request: Request, equipment: str = Form(...)):
    save_answers(user_id(request), {"equipment": equipment})
    return templates.TemplateResponse("schedule.html", {"request": request})


@app.post("/schedule", response_class=HTMLResponse)
async def handle_schedule(
    request: Request,
    days_per_week: int = Form(...),
    weeks: int = Form(...),
):
    uid = user_id(request)
    save_answers(uid, {"days_per_week": days_per_week, "weeks": weeks})
    answers_row = (
        sb.table("wizard_answers")
        .select("*")
        .eq("user_id", uid)
        .single()
        .execute()
        .data
    )
    upload_txt = latest_file_text(uid)
    program = generate_program(answers_row, upload_txt)
    rid = save_program(uid, program)
    return RedirectResponse(f"/routine/{rid}", status_code=302)


# ---------- dashboard ----------
@app.get("/routine/{rid}", response_class=HTMLResponse)
def routine_dash(request: Request, rid: str):
    prog = fetch_program(rid)
    weeks = [w.week for w in prog.weeks]
    return templates.TemplateResponse(
        "routine_view.html",
        {
            "request": request,
            "routine_id": rid,
            "program": prog,
            "weeks": weeks,
        },
    )


@app.get("/routine/{rid}/week/{week}/day/{day}", response_class=HTMLResponse)
def routine_day(request: Request, rid: str, week: int, day: int):
    prog = fetch_program(rid)
    week_obj = next(w for w in prog.weeks if w.week == week)
    day_obj = next(d for d in week_obj.days if d.day == day)
    total_sets = sum(ex.sets for ex in day_obj.exercises)
    done_sets = count_logged_sets(user_id(request), rid, week, day)
    can_finish = done_sets >= total_sets
    return templates.TemplateResponse(
        "day.html",
        {
            "request": request,
            "routine_id": rid,
            "week": week,
            "day": day,
            "exercises": day_obj.exercises,
            "can_finish": can_finish,
        },
    )


# ---------- program editing ----------
@app.post("/routine/{rid}/update", response_class=HTMLResponse)
async def update_program(request: Request, rid: str, program_json: str = Form(...)):
    try:
        prog = Program.model_validate_json(program_json)
    except Exception as e:
        return HTMLResponse(
            f"<div class='alert alert-error'>Invalid JSON: {e}</div>", status_code=400
        )
    save_program(user_id(request), prog, routine_id=rid)
    return RedirectResponse(f"/routine/{rid}", status_code=302)


# ---------- logging ----------
@app.post("/routine/{rid}/week/{week}/day/{day}/log", response_class=HTMLResponse)
async def log_set(
    request: Request,
    rid: str,
    week: int,
    day: int,
    exercise_name: str = Form(...),
    set_number: int = Form(...),
    weight: float = Form(...),
    reps: int = Form(...),
):
    save_set_log(
        user_id(request), rid, week, day, exercise_name, set_number, weight, reps
    )
    return HTMLResponse("<td colspan='4' class='text-center text-success'>✅</td>")


@app.post("/routine/{rid}/week/{week}/day/{day}/finish", response_class=HTMLResponse)
def finish_day(request: Request, rid: str, week: int, day: int):
    mark_day_finished(user_id(request), rid, week, day)
    # figure out next page
    prog = fetch_program(rid)
    next_day, next_week = day + 1, week
    week_obj = next((w for w in prog.weeks if w.week == week), None)
    if not week_obj or next_day > len(week_obj.days):
        next_week += 1
        next_day = 1
    if next_week > len(prog.weeks):
        url = f"/routine/{rid}"  # back to dashboard
    else:
        url = f"/routine/{rid}/week/{next_week}/day/{next_day}"
    resp = HTMLResponse("OK")
    resp.headers["HX-Redirect"] = url
    return resp
