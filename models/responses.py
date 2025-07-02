from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class InformationRequest(BaseModel):
    type: Literal["information_request"] = "information_request"
    missing_info: List[str]
    questions: str
    current_info: Dict[str, Any]


class ProgramMetadata(BaseModel):
    generated_at: str
    user_request: str
    agent_info: Dict[str, Any]


class Program(BaseModel):
    program_name: str
    program_description: str
    total_weeks: int
    days_per_week: int
    equipment_required: str
    weeks: List[Any]
    progression_notes: Optional[str]
    deload_info: Optional[str]
    # Additional dynamic keys allowed
    metadata: Optional[ProgramMetadata]


class ProgramGenerated(BaseModel):
    type: Literal["program_generated"] = "program_generated"
    status: Literal["success"] = "success"
    program_id: str
    program: Dict[str, Any]
    redirect: str


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str
    details: Optional[Any]


ResponseTypes = InformationRequest | ProgramGenerated | ErrorResponse