import os
import json
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
from .schema import Program

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GENERATION_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"


# ---------- embeddings ----------
def embed_text(text: str) -> List[float]:
    """Return a 1536-dim embedding vector for text (used before saving to Supabase)."""
    # Truncate text to fit embedding model limits (~8K tokens = ~6K chars)
    if len(text) > 6000:
        text = text[:6000]
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
2. Otherwise base decisions on the questionnaire answer of Goals.
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
        sections.append(
            f"UPLOAD:\n{upload_text[:3000]}"
        )  # keep prompt under token limits
    user_prompt = "\n\n".join(sections)
    resp = client.chat.completions.create(
        model=GENERATION_MODEL,
        temperature=0.4,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    # Strip markdown code blocks if present
    if raw.startswith("```json"):
        raw = raw[7:]  # Remove ```json
    if raw.endswith("```"):
        raw = raw[:-3]  # Remove ```
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"OpenAI returned invalid JSON: {e}\n{raw[:300]}")
    return Program.model_validate(data)
