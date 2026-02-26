"""
Appointment Scheduling Agent.

A LangGraph ReAct agent that handles:
  - Booking appointments
  - Cancelling appointments
  - Rescheduling appointments
  - Checking appointment availability and schedule

Tools are backed by Excel (patient data) + Calendar (Google or in-memory demo).
"""
import json
import logging
from typing import Annotated
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
from config import settings
from tools import excel_tools, calendar_tools

logger = logging.getLogger(__name__)

# ─── Tool definitions ────────────────────────────────────────────────────────

@tool
def search_patient(query: str) -> str:
    """
    Search for patients by name, patient ID, phone number, or email.
    Use this to find the patient before booking or looking up appointments.

    Args:
        query: Name, ID, phone, or email to search for

    Returns:
        JSON list of matching patients with fields: patient_id, first_name, last_name, dob, phone, provider
    """
    results = excel_tools.search_patient(query)
    if not results:
        return json.dumps({"found": False, "message": f"No patient found matching '{query}'"})
    return json.dumps({"found": True, "count": len(results), "patients": results})


@tool
def list_appointments(
    date_from: str = "",
    date_to: str = "",
    patient_name: str = "",
    provider: str = "",
) -> str:
    """
    List upcoming appointments. Filter by date range, patient name, or provider.

    Args:
        date_from: Start date/time (YYYY-MM-DD or YYYY-MM-DDTHH:MM). Default: today
        date_to:   End date/time. Default: 7 days from now
        patient_name: Partial patient name to filter by (optional)
        provider:     Provider name to filter by (optional)

    Returns:
        JSON list of appointments
    """
    results = calendar_tools.list_appointments(
        date_from=date_from or None,
        date_to=date_to or None,
        patient_name=patient_name or None,
        provider=provider or None,
    )
    if not results:
        return json.dumps({"found": False, "message": "No appointments found for the given criteria"})
    return json.dumps({"found": True, "count": len(results), "appointments": results})


@tool
def check_availability(date: str, provider: str, duration_minutes: int = 30) -> str:
    """
    Check available appointment slots for a provider on a specific date.

    Args:
        date: Date in YYYY-MM-DD format
        provider: Provider name (e.g. "Dr. Smith")
        duration_minutes: Length of the appointment (default 30)

    Returns:
        JSON list of available time slots in YYYY-MM-DDTHH:MM format
    """
    slots = calendar_tools.check_availability(date, provider, duration_minutes)
    if not slots:
        return json.dumps({"available": False, "message": f"No availability for {provider} on {date}"})
    return json.dumps({"available": True, "slots": slots, "count": len(slots)})


@tool
def book_appointment(
    patient_id: str,
    patient_name: str,
    provider: str,
    appointment_datetime: str,
    reason: str,
    duration_minutes: int = 30,
) -> str:
    """
    Book a new appointment for a patient.

    Args:
        patient_id: Patient ID from search_patient results
        patient_name: Full patient name
        provider: Provider name (e.g. "Dr. Smith")
        appointment_datetime: Date and time in YYYY-MM-DDTHH:MM format
        reason: Reason for the visit
        duration_minutes: Duration of the appointment (default 30)

    Returns:
        JSON with the created appointment details including appointment_id
    """
    appt = calendar_tools.book_appointment(
        patient_id=patient_id,
        patient_name=patient_name,
        provider=provider,
        appointment_datetime=appointment_datetime,
        reason=reason,
        duration_minutes=duration_minutes,
    )
    return json.dumps({"success": True, "appointment": appt})


@tool
def cancel_appointment(appointment_id: str) -> str:
    """
    Cancel an existing appointment by its ID.

    Args:
        appointment_id: The appointment ID (e.g. APT001)

    Returns:
        JSON with the cancelled appointment details
    """
    appt = calendar_tools.cancel_appointment(appointment_id)
    return json.dumps({"success": True, "appointment": appt})


@tool
def reschedule_appointment(appointment_id: str, new_datetime: str) -> str:
    """
    Reschedule an existing appointment to a new date and time.

    Args:
        appointment_id: The appointment ID (e.g. APT001)
        new_datetime: New date and time in YYYY-MM-DDTHH:MM format

    Returns:
        JSON with the updated appointment details
    """
    appt = calendar_tools.reschedule_appointment(appointment_id, new_datetime)
    return json.dumps({"success": True, "appointment": appt})


# ─── Agent graph ─────────────────────────────────────────────────────────────

TOOLS = [
    search_patient,
    list_appointments,
    check_availability,
    book_appointment,
    cancel_appointment,
    reschedule_appointment,
]

SYSTEM_PROMPT = """You are a professional healthcare admin assistant specializing in appointment scheduling.
You help hospital staff book, cancel, reschedule, and look up patient appointments.

Guidelines:
- Always search for the patient first before booking to verify they exist and get their patient_id.
- Confirm key details before booking (patient name, date/time, provider, reason).
- When checking availability, use check_availability to find open slots.
- Be concise, professional, and accurate.
- Always confirm the outcome clearly at the end (appointment booked, cancelled, etc.).
- Use 24-hour time format internally but present times in 12-hour format to users.
- Today's context: you are operating in demo mode with sample patient and calendar data.
"""


class AgentMessageState(TypedDict):
    messages: Annotated[list, add_messages]


def _build_graph():
    llm = ChatAnthropic(
        model="claude-opus-4-6",
        api_key=settings.anthropic_api_key,
        temperature=0,
    ).bind_tools(TOOLS)

    tool_node = ToolNode(TOOLS)

    def call_model(state: AgentMessageState):
        messages = state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentMessageState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentMessageState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


_appointment_graph = None


def get_appointment_graph():
    global _appointment_graph
    if _appointment_graph is None:
        _appointment_graph = _build_graph()
    return _appointment_graph


# ─── Public interface ─────────────────────────────────────────────────────────

async def run_appointment_agent(
    user_text: str,
    conversation_history: list[dict],
) -> str:
    """
    Run the appointment agent on a user request.

    Args:
        user_text: The user's request (post-STT text)
        conversation_history: Prior turns as list of {"role": str, "text": str}

    Returns:
        Agent's final response text
    """
    from langchain_core.messages import SystemMessage

    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # Inject prior conversation context
    for turn in conversation_history[-6:]:  # last 3 exchanges
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["text"]))
        else:
            messages.append(AIMessage(content=turn["text"]))

    messages.append(HumanMessage(content=user_text))

    graph = get_appointment_graph()
    result = await graph.ainvoke({"messages": messages})

    # Extract the last AI message
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content if isinstance(msg.content, str) else str(msg.content)

    return "I'm sorry, I was unable to process your request. Please try again."
