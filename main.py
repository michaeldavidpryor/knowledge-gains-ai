"""
Knowledge Gains - Science-based Weightlifting App
Main FastAPI application with AI services and workout tracking
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
import uvicorn
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from supabase import create_client

# Import our specialized services
from services.file_processor import FileProcessorService
from services.web_search import WebSearchService
from services.workout_coordinator import WorkoutCoordinatorService

# Import new models
from models.responses import InformationRequest, ProgramGenerated, ErrorResponse, ResponseTypes

# Initialize FastAPI app
app = FastAPI(
    title="Knowledge Gains",
    description="Science-based weightlifting program generator with AI services",
    version="1.0.0",
)

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set"
    )

supabase = create_client(supabase_url, supabase_key)

# Initialize AI services
coordinator = WorkoutCoordinatorService()
file_processor = FileProcessorService()
web_search = WebSearchService()


# Pydantic models
class ProgramRequest(BaseModel):
    request: str
    equipment: Optional[str] = None
    duration_weeks: Optional[int] = None
    days_per_week: Optional[int] = None
    user_files: Optional[List[str]] = []


class WorkoutUpdate(BaseModel):
    workout_id: str
    exercise_name: str
    set_number: int
    weight_kg: Optional[float] = None
    reps_completed: Optional[int] = None
    completed: bool = False
    rpe: Optional[int] = None


class ExerciseModification(BaseModel):
    workout_id: str
    exercise_name: str
    modification_request: str


# User authentication (simplified - extend with proper Supabase auth)
def get_current_user(request: Request) -> Dict:
    # In production, extract from Supabase JWT token
    # For demo, using session or hardcoded user
    return {"id": "demo-user-id", "email": "demo@knowledgegains.com"}


# Routes


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with program request form"""
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "title": "Knowledge Gains - Science-based Weightlifting"},
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: Dict = Depends(get_current_user)):
    """User dashboard showing current program and progress"""

    # Get user's current program
    result = (
        supabase.table("workout_programs")
        .select("*")
        .eq("user_id", user["id"])
        .eq("is_active", True)
        .execute()
    )
    current_program = result.data[0] if result.data else None

    # Get recent workouts
    recent_workouts = []
    if current_program:
        workouts_result = (
            supabase.table("workouts")
            .select("*")
            .eq("program_id", current_program["id"])
            .order("workout_date", desc=True)
            .limit(5)
            .execute()
        )
        recent_workouts = workouts_result.data

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "Dashboard - Knowledge Gains",
            "current_program": current_program,
            "recent_workouts": recent_workouts,
            "user": user,
        },
    )


@app.get("/streaming-demo", response_class=HTMLResponse)
async def streaming_demo(request: Request):
    """Demo page for streaming AI responses"""
    return templates.TemplateResponse(
        "streaming_example.html",
        {"request": request, "title": "Streaming AI Demo - Knowledge Gains"}
    )


@app.post("/api/generate-program", response_model=ResponseTypes)
async def generate_program(
    background_tasks: BackgroundTasks,
    request: str = Form(...),
    equipment: Optional[str] = Form(None),
    duration_weeks: Optional[int] = Form(None),
    days_per_week: Optional[int] = Form(None),
    user: Dict = Depends(get_current_user),
):
    """Generate a new workout program using AI services"""

    # Prepare data for coordinator
    program_data = {
        "request": request,
        "equipment": equipment,
        "duration_weeks": duration_weeks,
        "days_per_week": days_per_week,
        "user_files": [],  # TODO: Add uploaded files
    }

    # Process with coordinator
    result = await coordinator.process(program_data)

    if result.get("type") == "information_request":
        # Return form for missing information
        return InformationRequest(
            missing_info=result["missing_info"],
            questions=result["questions"],
            current_info=result["current_info"],
        )

    elif result.get("type") == "program_generated":
        # Save program to database
        program = result["program"]

        # Store in Supabase
        program_record = {
            "user_id": user["id"],
            "name": program["program_name"],
            "description": program["program_description"],
            "duration_weeks": program["total_weeks"],
            "days_per_week": program["days_per_week"],
            "equipment_required": program["equipment_required"],
            "program_data": program,
            "generated_by_ai": True,
            "agent_version": "1.0",
        }

        db_result = supabase.table("workout_programs").insert(program_record).execute()
        program_id = db_result.data[0]["id"]

        # Generate individual workout records
        background_tasks.add_task(create_workout_instances, program_id, program)

        return ProgramGenerated(
            program_id=program_id,
            program=program,
            redirect=f"/program/{program_id}",
        )

    else:
        return ErrorResponse(message="Failed to generate program", details=result)


@app.get("/program/{program_id}", response_class=HTMLResponse)
async def view_program(
    request: Request, program_id: str, user: Dict = Depends(get_current_user)
):
    """View a specific workout program"""

    # Get program from database
    result = (
        supabase.table("workout_programs")
        .select("*")
        .eq("id", program_id)
        .eq("user_id", user["id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Program not found")

    program = result.data[0]

    return templates.TemplateResponse(
        "program_view.html",
        {
            "request": request,
            "title": f"{program['name']} - Knowledge Gains",
            "program": program,
            "user": user,
        },
    )


@app.get("/workout/{workout_id}", response_class=HTMLResponse)
async def workout_session(
    request: Request, workout_id: str, user: Dict = Depends(get_current_user)
):
    """Interactive workout session page"""

    # Get workout from database
    result = (
        supabase.table("workouts")
        .select("*")
        .eq("id", workout_id)
        .eq("user_id", user["id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Workout not found")

    workout = result.data[0]

    # Get previous sets for progression calculation
    previous_sets = []
    if workout["week_number"] > 1:
        prev_result = (
            supabase.table("exercise_sets")
            .select("*")
            .eq("user_id", user["id"])
            .execute()
        )
        previous_sets = prev_result.data

    return templates.TemplateResponse(
        "workout_session.html",
        {
            "request": request,
            "title": (f"{workout['workout_name']} - Knowledge Gains"),
            "workout": workout,
            "previous_sets": previous_sets,
            "user": user,
        },
    )


@app.post("/api/update-set")
async def update_set(update: WorkoutUpdate, user: Dict = Depends(get_current_user)):
    """Update a specific set during workout"""

    # Check if set record exists
    result = (
        supabase.table("exercise_sets")
        .select("*")
        .eq("workout_id", update.workout_id)
        .eq("exercise_name", update.exercise_name)
        .eq("set_number", update.set_number)
        .execute()
    )

    set_data = {
        "weight_kg": update.weight_kg,
        "reps_completed": update.reps_completed,
        "completed": update.completed,
        "rpe": update.rpe,
    }

    if result.data:
        # Update existing set
        supabase.table("exercise_sets").update(set_data).eq(
            "id", result.data[0]["id"]
        ).execute()
        set_id = result.data[0]["id"]
    else:
        # Create new set
        set_data.update({
            "workout_id": update.workout_id,
            "user_id": user["id"],
            "exercise_name": update.exercise_name,
            "set_number": update.set_number,
        })
        db_result = supabase.table("exercise_sets").insert(set_data).execute()
        set_id = db_result.data[0]["id"]

    # Check if this is a personal record
    if update.weight_kg and update.reps_completed:
        await check_personal_record(
            user["id"], update.exercise_name, update.weight_kg, update.reps_completed
        )

    return JSONResponse({
        "status": "success",
        "set_id": set_id,
        "message": "Set updated successfully",
    })


@app.post("/api/modify-exercise")
async def modify_exercise(
    modification: ExerciseModification, user: Dict = Depends(get_current_user)
):
    """Request modification of an exercise using AI"""

    # Get current workout data
    workout_result = (
        supabase.table("workouts")
        .select("*")
        .eq("id", modification.workout_id)
        .execute()
    )

    if not workout_result.data:
        raise HTTPException(status_code=404, detail="Workout not found")

    workout = workout_result.data[0]

    # Find the exercise in the workout
    exercises = workout["exercises"]
    target_exercise = None

    for exercise in exercises:
        if exercise["name"] == modification.exercise_name:
            target_exercise = exercise
            break

    if not target_exercise:
        raise HTTPException(status_code=404, detail="Exercise not found in workout")

    # Use coordinator to suggest modification
    result = await coordinator.modify_workout(
        target_exercise, modification.modification_request
    )

    if result["success"]:
        # Update workout in database
        modified_exercises = []
        for exercise in exercises:
            if exercise["name"] == modification.exercise_name:
                modified_exercises.append(result["modified_workout"])
            else:
                modified_exercises.append(exercise)

        # Update workout with modified exercises
        (
            supabase.table("workouts")
            .update({"exercises": modified_exercises})
            .eq("id", modification.workout_id)
            .execute()
        )

        # Log the modification
        mod_record = {
            "program_id": workout["program_id"],
            "user_id": user["id"],
            "workout_id": modification.workout_id,
            "modification_type": "exercise_substitution",
            "original_data": target_exercise,
            "modified_data": result["modified_workout"],
            "reason": modification.modification_request,
            "ai_suggested": True,
        }

        supabase.table("program_modifications").insert(mod_record).execute()

        return JSONResponse({
            "status": "success",
            "modified_exercise": result["modified_workout"],
            "message": "Exercise modified successfully",
        })

    else:
        return JSONResponse({
            "status": "error",
            "message": "Failed to modify exercise",
            "details": result,
        })


@app.post("/api/chat-stream")
async def chat_stream(
    request: Request,
    message: str = Form(...),
    user: Dict = Depends(get_current_user)
):
    """Stream AI responses in real-time for interactive coaching"""
    
    async def generate():
        # Use the coordinator's streaming capability
        system_prompt = """You are an expert strength training coach. 
        Provide helpful, science-based advice about weightlifting, programming, 
        technique, and recovery. Be concise but informative."""
        
        try:
            # Use the new streaming generator method
            full_prompt = f"{system_prompt}\n\n{message}"
            async for chunk in coordinator.send_message_stream_generator(full_prompt):
                # Format as Server-Sent Events
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )


@app.post("/api/analyze-form-stream")
async def analyze_form_stream(
    file: UploadFile = File(...),
    exercise_name: str = Form(...),
    user: Dict = Depends(get_current_user)
):
    """Stream real-time form analysis for uploaded videos/images"""
    
    # Save uploaded file temporarily
    upload_dir = Path("uploads") / user["id"] / "temp"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)
    
    async def generate():
        try:
            # Process with file processor service using streaming
            analysis_prompt = f"""Analyze this {exercise_name} form. 
            Provide real-time feedback on:
            1. Technique correctness
            2. Common mistakes to avoid
            3. Safety considerations
            4. Improvement suggestions
            
            File: {file.filename}"""
            
            full_prompt = (
                "You are an expert in biomechanics and exercise form analysis.\n\n"
                + analysis_prompt
            )
            async for chunk in file_processor.send_message_stream_generator(full_prompt):
                yield f"data: {chunk}\n\n"
                
            # Clean up temp file
            file_path.unlink(missing_ok=True)
            
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


@app.post("/api/upload-files")
async def upload_files(
    files: List[UploadFile] = File(...), user: Dict = Depends(get_current_user)
):
    """Upload fitness-related documents for AI processing"""

    uploaded_files = []

    for file in files:
        # Save file
        upload_dir = Path("uploads") / user["id"]
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / file.filename

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        # Store in database
        file_record = {
            "user_id": user["id"],
            "filename": file.filename,
            "file_path": str(file_path),
            "file_size": len(content),
            "file_type": file.content_type,
            "file_hash": str(hash(content)),  # Simple hash for demo
            "processing_status": "pending",
        }

        db_result = supabase.table("uploaded_files").insert(file_record).execute()
        uploaded_files.append(db_result.data[0])

    return JSONResponse({
        "status": "success",
        "files_uploaded": len(uploaded_files),
        "files": uploaded_files,
    })


# HTMX Components for real-time updates


@app.get("/components/workout-progress/{workout_id}")
async def workout_progress_component(
    workout_id: str, user: Dict = Depends(get_current_user)
):
    """HTMX component for workout progress"""

    # Get completed sets
    sets_result = (
        supabase.table("exercise_sets")
        .select("*")
        .eq("workout_id", workout_id)
        .eq("completed", True)
        .execute()
    )
    completed_sets = len(sets_result.data)

    # Get total sets from workout
    workout_result = (
        supabase.table("workouts").select("exercises").eq("id", workout_id).execute()
    )
    total_sets = 0

    if workout_result.data:
        exercises = workout_result.data[0]["exercises"]
        for exercise in exercises:
            total_sets += exercise.get("sets", 0)

    progress_percent = (completed_sets / total_sets * 100) if total_sets > 0 else 0

    return HTMLResponse(
        f"""
    <div class="progress w-full bg-gray-200 rounded-full h-2.5">
        <div class="progress-bar bg-primary h-2.5 rounded-full transition-all duration-300" 
             style="width: {progress_percent:.1f}%"></div>
    </div>
    <div class="text-sm text-gray-600 mt-1">
        {completed_sets}/{total_sets} sets completed ({progress_percent:.1f}%)
    </div>
    """
    )


@app.get("/components/exercise-card/{workout_id}/{exercise_name}")
async def exercise_card_component(
    workout_id: str, exercise_name: str, user: Dict = Depends(get_current_user)
):
    """HTMX component for individual exercise card"""

    # Get workout and exercise data
    workout_result = (
        supabase.table("workouts").select("*").eq("id", workout_id).execute()
    )
    workout = workout_result.data[0]

    # Find exercise in workout
    exercise = None
    for ex in workout["exercises"]:
        if ex["name"] == exercise_name:
            exercise = ex
            break

    if not exercise:
        return HTMLResponse("<div>Exercise not found</div>")

    # Get previous weights for progression
    prev_sets = (
        supabase.table("exercise_sets")
        .select("weight_kg")
        .eq("user_id", user["id"])
        .eq("exercise_name", exercise_name)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    last_weight = prev_sets.data[0]["weight_kg"] if prev_sets.data else 0

    # Calculate recommended weight based on progression
    week_number = workout["week_number"]
    recommended_weight = await coordinator.calculate_progression(
        last_weight, week_number, exercise_name, exercise.get("progression", "linear")
    )

    return templates.TemplateResponse(
        "components/exercise_card.html",
        {
            "exercise": exercise,
            "workout_id": workout_id,
            "recommended_weight": recommended_weight,
            "sets_range": range(1, exercise["sets"] + 1),
        },
    )


# Background tasks


async def create_workout_instances(program_id: str, program_data: Dict):
    """Create individual workout instances from program structure"""

    for week in program_data["weeks"]:
        week_number = week["week_number"]

        for workout in week["workouts"]:
            workout_record = {
                "program_id": program_id,
                "user_id": program_data.get("user_id"),  # Would be passed in
                "week_number": week_number,
                "day_number": workout["day"],
                "workout_name": workout["workout_name"],
                "exercises": workout["exercises"],
                "status": "planned",
            }

            supabase.table("workouts").insert(workout_record).execute()


async def check_personal_record(
    user_id: str, exercise_name: str, weight_kg: float, reps: int
):
    """Check and update personal records"""

    # Calculate estimated 1RM
    estimated_1rm = weight_kg * (1 + reps / 30.0)

    # Check if this is a new record
    prev_record = (
        supabase.table("progression_tracking")
        .select("estimated_1rm")
        .eq("user_id", user_id)
        .eq("exercise_name", exercise_name)
        .order("measurement_date", desc=True)
        .limit(1)
        .execute()
    )

    is_new_record = True
    if prev_record.data:
        is_new_record = estimated_1rm > prev_record.data[0]["estimated_1rm"]

    if is_new_record:
        record_data = {
            "user_id": user_id,
            "exercise_name": exercise_name,
            "max_weight_kg": weight_kg,
            "max_reps": reps,
            "estimated_1rm": estimated_1rm,
            "volume_progression": weight_kg * reps,
        }

        supabase.table("progression_tracking").insert(record_data).execute()


# Development server
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
