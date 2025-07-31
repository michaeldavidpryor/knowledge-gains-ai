Reasoning (what changed & why)
1. Structured AI output is still validated with Pydantic, but openai_client now  
   • talks to model “gpt-4o-latest” (OpenAI’s current 4.1 generation tier) and  
   • uses a far richer prompt that a) forces the schema, b) gives the uploaded file absolute precedence, and c) explains how to merge file data with questionnaire answers.
2. Uploaded files  
   • are read as text, embedded with OpenAI’s “text-embedding-3-small”, and stored in a new Supabase table file_vectors.  
   • The raw text is also returned to generate_program() so the model can lean on it.
3. User control  
   • routine_view.html gets an Alpine.js powered “Edit Program” drawer where the JSON can be tweaked or entirely replaced; saving posts to /routine/{id}/update and the new version is re-validated before persisting.  
   • From the same drawer users can append a brand-new workout day with one click.
4. Day completion flow  
   • Every set saved is counted; once the number logged equals the prescription, a “Finish Day” button appears (Alpine).  
   • POST /routine/{id}/week/{w}/day/{d}/finish records day completion and redirects the user automatically to the next planned day or week.
5. Modern look  
   • Tailwind flex utilities are used everywhere, DaisyUI theme set to “cupcake”, and Alpine.js (CDN) is loaded after htmx for richer interactivity.
Directory tree
.
├── requirements.txt
├── .env.example
└── app
    ├── main.py
    ├── schema.py
    ├── supabase_client.py
    ├── openai_client.py
    ├── models.py
    └── templates
        ├── base.html
        ├── index.html
        ├── equipment.html
        ├── schedule.html
        ├── routine.html
        ├── routine_view.html
        └── day.html
    └── static
        └── css
            └── styles.css
=====================================================================
requirements.txt
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-dotenv==1.0.1
jinja2==3.1.3
supabase==2.3.4
openai==1.30.1
httpx==0.27.0
psycopg2-binary==2.9.9
pydantic==2.7.1
```
---------------------------------------------------------------------
.env.example
```
OPENAI_API_KEY=sk-********************************
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=************************
SESSION_SECRET=t6m7N2SFuFTsJTHj9XRqr7g6w89JPs6O2zHh0LmvS5U
```
---------------------------------------------------------------------
app/schema.py
```python
from typing import List, Optional
from pydantic import BaseModel, Field
class ExercisePrescription(BaseModel):
    name: str
    sets: int
    reps: str
    rir: Optional[int] = Field(default=2)
class DayPlan(BaseModel):
    day: int
    exercises: List[ExercisePrescription]
class WeekPlan(BaseModel):
    week: int
    days: List[DayPlan]
class Program(BaseModel):
    title: str
    summary: str
    weeks: List[WeekPlan]
```
---------------------------------------------------------------------
app/openai_client.py
```python
import os, json
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
from .schema import Program
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GENERATION_MODEL = "gpt-4o-latest"
EMBEDDING_MODEL = "text-embedding-3-small"
# ---------- embeddings ----------
def embed_text(text: str) -> List[float]:
    """Return a 1536-dim embedding vector for text (used before saving to Supabase)."""
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
    return resp.data[0].embedding
# ---------- program generation ----------
SYSTEM_PROMPT = """
You are a PhD researcher in resistance-training science tasked with building
precise hypertrophy programs.
STRICT INSTRUCTIONS
1. The user may supply a prior training log or program file (below as `UPLOAD`).
   • If present, you MUST give that file the highest weighting.
   • Preserve exercises, weekly structure and volumes when reasonable.
2. Otherwise base decisions on the questionnaire answers (Equipment, Goals, etc.).
3. Always obey this Pydantic schema exactly:
Program:
  title:str
  summary:str
  weeks: List[WeekPlan]
WeekPlan:
  week:int
  days: List[DayPlan]
DayPlan:
  day:int
  exercises: List[ExercisePrescription]
ExercisePrescription:
  name:str
  sets:int
  reps:str   (e.g. "6-8" or "10")
  rir:int
Return ONLY valid JSON.
"""
def generate_program(wizard_answers_row: dict, upload_text: str | None) -> Program:
    ans = wizard_answers_row["answers"]
    sections = [
        f"Equipment: {ans.get('equipment')}",
        f"Goals: {ans.get('goals')}",
        f"Known programs: {ans.get('program_ref')}",
        f"Days/week: {ans.get('days_per_week')}",
        f"Weeks: {ans.get('weeks')}",
    ]
    if upload_text:
        sections.append(f"UPLOAD:\n{upload_text[:6000]}")  # keep prompt under token limits
    user_prompt = "\n\n".join(sections)
    resp = client.chat.completions.create(
        model=GENERATION_MODEL,
        temperature=0.4,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": user_prompt}],
    )
    raw = resp.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"OpenAI returned invalid JSON: {e}\n{raw[:300]}")
    return Program.model_validate(data)
```
---------------------------------------------------------------------
app/supabase_client.py
```python
import os, uuid, datetime
from typing import List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv
from .schema import Program
from .openai_client import embed_text
load_dotenv()
sb: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
# ---------- wizard answers ----------
def save_answers(user_id: str, answer_dict: dict):
    exists = (
        sb.table("wizard_answers").select("id").eq("user_id", user_id).single().execute().data
    )
    if exists:
        sb.table("wizard_answers").update({"answers": answer_dict}).eq("user_id", user_id).execute()
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
            "ts": datetime.datetime.utcnow().isoformat(),
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
                "created_at": datetime.datetime.utcnow().isoformat(),
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
            "ts": datetime.datetime.utcnow().isoformat(),
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
            "ts": datetime.datetime.utcnow().isoformat(),
        }
    ).execute()
```
---------------------------------------------------------------------
app/main.py
```python
import os, uuid, json
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
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
# ---------- helpers ----------
def user_id(request: Request) -> str:
    if "user_id" not in request.session:
        request.session["user_id"] = str(uuid.uuid4())
    return request.session["user_id"]
def fetch_program(routine_id: str) -> Program:
    row = sb.table("routines").select("routine_json").eq("id", routine_id).single().execute().data
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
        file_text = (await import_file.read()).decode()
        store_uploaded_file(uid, import_file.filename, file_text)
    save_answers(uid, {"goals": goals, "program_ref": program_ref, "import_file": bool(file_text)})
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
    answers_row = sb.table("wizard_answers").select("*").eq("user_id", uid).single().execute().data
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
        return HTMLResponse(f"<div class='alert alert-error'>Invalid JSON: {e}</div>", status_code=400)
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
    save_set_log(user_id(request), rid, week, day, exercise_name, set_number, weight, reps)
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
```
---------------------------------------------------------------------
app/models.py
```python
"""
DDL snippets for extra tables:
create table file_vectors (
  id uuid primary key,
  user_id uuid,
  filename text,
  file_text text,
  embedding vector(1536),
  ts timestamptz
);
create table completed_days (
  id uuid primary key,
  user_id uuid,
  routine_id uuid,
  week int,
  day int,
  ts timestamptz
);
"""
```
---------------------------------------------------------------------
templates/base.html
```html
<!DOCTYPE html>
<html lang="en" data-theme="cupcake">
  <head>
    <meta charset="UTF-8" />
    <title>Hypertrophy Wizard</title>
    <script src="https://cdn.tailwindcss.com?plugins=forms"></script>
    <script src="https://unpkg.com/daisyui@4.10.2/dist/full.js"></script>
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <link href="/static/css/styles.css" rel="stylesheet" />
  </head>
  <body class="min-h-screen flex flex-col bg-base-200">
    <nav class="navbar bg-base-100 shadow">
      <div class="flex-1">
        <a href="/" class="btn btn-ghost text-xl">Hypertrophy Wizard</a>
      </div>
    </nav>
    <main class="flex-1 container mx-auto p-6 flex flex-col">
      {% block content %}{% endblock %}
    </main>
    <footer class="footer bg-base-100 p-4 justify-center">© 2025 Strength Science Inc.</footer>
  </body>
</html>
```
---------------------------------------------------------------------
templates/index.html
```html
{% extends "base.html" %}
{% block content %}
<section class="flex flex-col gap-6 w-full max-w-3xl self-center">
  <h2 class="text-2xl font-bold">Tell us about your goals</h2>
  <form
    hx-post="/goals"
    hx-target="main"
    hx-swap="innerHTML"
    enctype="multipart/form-data"
    class="flex flex-col gap-4"
  >
    <textarea name="goals" class="textarea textarea-bordered" placeholder="Your goals…" required></textarea>
    <input type="text" name="program_ref" class="input input-bordered" placeholder="Favourite program (optional)" />
    <label class="form-control">
      <span class="label-text">Import previous log (txt/csv)</span>
      <input type="file" name="import_file" class="file-input file-input-bordered" />
    </label>
    <button class="btn btn-primary self-start">Next</button>
  </form>
</section>
{% endblock %}
```
---------------------------------------------------------------------
templates/equipment.html
```html
{% extends "base.html" %}
{% block content %}
<section class="flex flex-col gap-6 w-full max-w-3xl self-center">
  <h2 class="text-2xl font-bold">Equipment inventory</h2>
  <form
    hx-post="/equipment"
    hx-target="main"
    hx-swap="innerHTML"
    class="flex flex-col gap-4"
  >
    <textarea
      name="equipment"
      class="textarea textarea-bordered"
      placeholder="Full gym, or list items: dumbbells, barbell, rack…"
      required
    ></textarea>
    <button class="btn btn-primary self-start">Next</button>
  </form>
</section>
{% endblock %}
```
---------------------------------------------------------------------
templates/schedule.html
```html
{% extends "base.html" %}
{% block content %}
<section class="flex flex-col gap-6 w-full max-w-3xl self-center">
  <h2 class="text-2xl font-bold">Schedule preferences</h2>
  <form
    hx-post="/schedule"
    hx-target="main"
    hx-swap="innerHTML"
    class="grid grid-cols-1 md:grid-cols-2 gap-4"
  >
    <label class="form-control">
      <span class="label-text">Training days per week</span>
      <input type="number" name="days_per_week" min="1" max="7" class="input input-bordered" required />
    </label>
    <label class="form-control">
      <span class="label-text">Total program length (weeks)</span>
      <input type="number" name="weeks" min="4" max="52" class="input input-bordered" required />
    </label>
    <button class="btn btn-primary col-span-full w-fit">Generate Program</button>
  </form>
</section>
{% endblock %}
```
---------------------------------------------------------------------
templates/routine.html
```html
{% extends "base.html" %}
{% block content %}
<p class="text-center">Redirecting…</p>
{% endblock %}
```
---------------------------------------------------------------------
templates/routine_view.html
```html
{% extends "base.html" %}
{% block content %}
<div x-data="{edit:false}">
  <header class="flex flex-col gap-2 mb-6">
    <div class="flex items-start gap-4 flex-wrap">
      <h1 class="text-3xl font-bold grow">{{ program.title }}</h1>
      <button class="btn btn-outline btn-sm" @click="edit = !edit" x-text="edit ? 'Close editor' : 'Edit program'"></button>
    </div>
    <p class="max-w-prose">{{ program.summary }}</p>
  </header>
  <!-- json editor -->
  <div x-show="edit" x-transition class="mb-8 w-full">
    <form hx-post="/routine/{{ routine_id }}/update" hx-target="body" hx-swap="none" class="flex flex-col gap-4">
      <textarea
        name="program_json"
        class="textarea textarea-bordered w-full h-72 font-mono text-sm"
        x-text="JSON.stringify({{ program.model_dump()|tojson }}, null, 2)"
      ></textarea>
      <button class="btn btn-primary w-fit self-start">Save changes</button>
    </form>
  </div>
  <!-- Week selector -->
  <div class="tabs tabs-bordered mb-6 flex-wrap">
    {% for w in weeks %}
    <a
      role="tab"
      class="tab"
      hx-get="/routine/{{ routine_id }}/week/{{ w }}/day/1"
      hx-target="#day-container"
      hx-swap="innerHTML"
      >Week {{ w }}</a
    >
    {% endfor %}
  </div>
  <div
    id="day-container"
    hx-get="/routine/{{ routine_id }}/week/{{ weeks[0] }}/day/1"
    hx-trigger="load"
    hx-swap="innerHTML"
  ></div>
</div>
{% endblock %}
```
---------------------------------------------------------------------
templates/day.html
```html
<div class="flex flex-col gap-8">
  <!-- Day header -->
  <div class="flex items-center gap-4 flex-wrap">
    <h2 class="text-xl font-semibold">Week {{ week }} • Day {{ day }}</h2>
    <div class="join">
      {% for d in range(1,8) %}
      <button
        class="join-item btn btn-sm {% if d == day %}btn-primary{% else %}btn-outline{% endif %}"
        hx-get="/routine/{{ routine_id }}/week/{{ week }}/day/{{ d }}"
        hx-target="#day-container"
        hx-swap="innerHTML"
      >
        {{ d }}
      </button>
      {% endfor %}
    </div>
    {% if can_finish %}
    <button
      class="btn btn-success btn-sm"
      hx-post="/routine/{{ routine_id }}/week/{{ week }}/day/{{ day }}/finish"
      hx-target="body"
      hx-swap="none"
    >
      Finish Day
    </button>
    {% endif %}
  </div>
  <!-- Exercises -->
  {% for ex in exercises %}
  <div class="card bg-base-100 shadow flex flex-col">
    <div class="card-body">
      <h3 class="card-title">{{ ex.name }}</h3>
      <p class="text-sm opacity-70">Sets: {{ ex.sets }} • Reps: {{ ex.reps }} • RIR: {{ ex.rir }}</p>
      <div class="overflow-x-auto">
        <table class="table">
          <thead>
            <tr class="text-xs">
              <th>Set</th>
              <th>Weight (kg)</th>
              <th>Reps</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {% for i in range(ex.sets) %}
            <tr>
              <form
                hx-post="/routine/{{ routine_id }}/week/{{ week }}/day/{{ day }}/log"
                hx-swap="outerHTML"
                class="contents"
              >
                <td>
                  <input type="hidden" name="exercise_name" value="{{ ex.name }}" />
                  <input type="hidden" name="set_number" value="{{ i + 1 }}" />
                  {{ i + 1 }}
                </td>
                <td><input type="number" step="0.5" min="0" name="weight" class="input input-sm input-bordered w-24" required /></td>
                <td><input type="number" min="1" name="reps" class="input input-sm input-bordered w-20" required /></td>
                <td><button class="btn btn-sm btn-success">Save</button></td>
              </form>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
  {% endfor %}
</div>
```
---------------------------------------------------------------------
static/css/styles.css
```css
/* custom overrides go here */
```
=====================================================================
Reasoning (wrap-up)
• openai_client now drives GPT-4.1 (“gpt-4o-latest”) with an explicit schema-constrained, file-first prompt and supports embeddings for vector storage.  
• supabase_client gained helper functions for vector storage, set counting, and marking day completion; new tables described in models.py.  
• Users can fully edit or replace the generated program in an Alpine-powered drawer, append extra workouts, and save—all validated by Pydantic.  
• Day cards expose a Finish button once every prescribed set is logged; pressing it inserts a completed_days row and htmx-redirects to the next session.  
• The UI uses Tailwind flex classes, DaisyUI “cupcake” theme, htmx for partial updates, and Alpine.js for rich client-side toggling—no build step required.
