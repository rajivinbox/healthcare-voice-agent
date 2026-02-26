from pydantic import BaseModel
from typing import Optional, List, Any
from enum import Enum


class IntentType(str, Enum):
    SCHEDULE_APPOINTMENT = "schedule_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CHECK_APPOINTMENTS = "check_appointments"
    PATIENT_LOOKUP = "patient_lookup"
    GENERAL_QUERY = "general_query"
    UNKNOWN = "unknown"


class Intent(BaseModel):
    type: IntentType
    confidence: float
    entities: dict[str, Any] = {}
    summary: str = ""


class ConversationTurn(BaseModel):
    role: str           # "user" | "assistant"
    text: str
    intent: Optional[Intent] = None


class AgentState(BaseModel):
    session_id: str
    user_text: str
    intent: Optional[Intent] = None
    conversation_history: List[ConversationTurn] = []
    agent_output: str = ""
    final_response: str = ""
    goal_achieved: bool = False
    error: Optional[str] = None


class TextRequest(BaseModel):
    text: str
    session_id: Optional[str] = None


class ProcessResponse(BaseModel):
    session_id: str
    user_text: str
    response_text: str
    intent: Optional[str] = None
    goal_achieved: bool = False


class Patient(BaseModel):
    patient_id: str
    first_name: str
    last_name: str
    dob: str
    phone: str
    email: str
    insurance: str
    provider: str


class Appointment(BaseModel):
    appointment_id: str
    patient_id: str
    patient_name: str
    provider: str
    datetime: str
    duration_minutes: int = 30
    reason: str
    status: str = "scheduled"   # scheduled | cancelled | completed
