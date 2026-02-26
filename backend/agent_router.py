"""
Agent Router — LangGraph orchestration pipeline.

Pipeline:
  STT text → detect_intent → route_agent → [appointment_agent | ...] → finalize_response

The router uses Claude to classify intent, then dispatches to the appropriate
specialized agent. The result is a plain-text response ready for TTS.
"""
import json
import logging
from typing import Annotated, Optional
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from typing_extensions import TypedDict
from config import settings
from models.schemas import IntentType, Intent

logger = logging.getLogger(__name__)

# ─── Shared graph state ───────────────────────────────────────────────────────

class RouterState(TypedDict):
    session_id: str
    user_text: str
    intent: Optional[dict]
    conversation_history: list[dict]
    agent_response: str
    final_response: str
    goal_achieved: bool
    error: Optional[str]


# ─── Intent detection ─────────────────────────────────────────────────────────

INTENT_SYSTEM_PROMPT = """You are an intent classifier for a healthcare admin voice agent.

Classify the user's request into exactly one of these intents:
- schedule_appointment   — book a new appointment
- cancel_appointment     — cancel an existing appointment
- reschedule_appointment — change date/time of an existing appointment
- check_appointments     — view/list upcoming appointments
- patient_lookup         — find/look up patient information
- general_query          — general question about the system or healthcare admin
- unknown                — cannot determine intent

Also extract relevant entities (patient_name, date, time, provider, appointment_id, reason).

Respond ONLY with valid JSON matching this schema:
{
  "type": "<intent_type>",
  "confidence": <0.0-1.0>,
  "entities": {
    "patient_name": "<name or null>",
    "date": "<YYYY-MM-DD or null>",
    "time": "<HH:MM or null>",
    "provider": "<name or null>",
    "appointment_id": "<id or null>",
    "reason": "<reason or null>"
  },
  "summary": "<one-line summary of what the user wants>"
}"""


async def detect_intent(state: RouterState) -> RouterState:
    """Classify user intent and extract entities using Claude."""
    try:
        llm = ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            api_key=settings.anthropic_api_key,
            temperature=0,
        )
        response = await llm.ainvoke([
            SystemMessage(content=INTENT_SYSTEM_PROMPT),
            HumanMessage(content=state["user_text"]),
        ])
        raw = response.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        intent_data = json.loads(raw)
        logger.info("Intent detected: %s (%.2f)", intent_data.get("type"), intent_data.get("confidence", 0))
        return {**state, "intent": intent_data, "error": None}

    except Exception as e:
        logger.error("Intent detection failed: %s", e)
        fallback = {
            "type": "general_query",
            "confidence": 0.3,
            "entities": {},
            "summary": state["user_text"],
        }
        return {**state, "intent": fallback, "error": str(e)}


# ─── Agent router ─────────────────────────────────────────────────────────────

APPOINTMENT_INTENTS = {
    IntentType.SCHEDULE_APPOINTMENT,
    IntentType.CANCEL_APPOINTMENT,
    IntentType.RESCHEDULE_APPOINTMENT,
    IntentType.CHECK_APPOINTMENTS,
}


def route_to_agent(state: RouterState) -> str:
    """Conditional edge: decide which agent node to invoke."""
    intent_type = state.get("intent", {}).get("type", "unknown")
    if intent_type in {i.value for i in APPOINTMENT_INTENTS}:
        return "appointment_agent"
    if intent_type == IntentType.PATIENT_LOOKUP.value:
        return "appointment_agent"   # Appointment agent has search_patient tool
    return "general_response"


# ─── Appointment agent node ───────────────────────────────────────────────────

async def appointment_agent_node(state: RouterState) -> RouterState:
    """Invoke the appointment scheduling agent."""
    from agents.appointment_agent import run_appointment_agent
    try:
        response = await run_appointment_agent(
            user_text=state["user_text"],
            conversation_history=state["conversation_history"],
        )
        return {**state, "agent_response": response, "goal_achieved": True}
    except Exception as e:
        logger.error("Appointment agent error: %s", e)
        return {
            **state,
            "agent_response": "",
            "goal_achieved": False,
            "error": str(e),
        }


# ─── General / fallback response ──────────────────────────────────────────────

GENERAL_SYSTEM_PROMPT = """You are a helpful healthcare administrative assistant.
Answer concisely and professionally. You help hospital staff manage patient appointments,
records, and admin tasks. If asked about something outside your scope, politely say so."""


async def general_response_node(state: RouterState) -> RouterState:
    """Handle general queries and unknown intents with a direct Claude response."""
    try:
        llm = ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            api_key=settings.anthropic_api_key,
            temperature=0.3,
        )
        messages = [SystemMessage(content=GENERAL_SYSTEM_PROMPT)]
        for turn in state["conversation_history"][-4:]:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["text"]))
        messages.append(HumanMessage(content=state["user_text"]))

        response = await llm.ainvoke(messages)
        return {**state, "agent_response": response.content, "goal_achieved": True}
    except Exception as e:
        logger.error("General response error: %s", e)
        return {
            **state,
            "agent_response": "I'm sorry, I encountered an issue processing your request. Please try again.",
            "goal_achieved": False,
            "error": str(e),
        }


# ─── Response closure / goal confirmation ─────────────────────────────────────

async def finalize_response(state: RouterState) -> RouterState:
    """
    Step 9: Response closure — confirm goal was achieved.
    Formats the agent output into a clean, TTS-ready response.
    """
    agent_resp = state.get("agent_response", "")

    if state.get("error") and not agent_resp:
        final = (
            "I'm sorry, I encountered a technical issue and couldn't complete your request. "
            "Please try again or contact support if the problem persists."
        )
        return {**state, "final_response": final, "goal_achieved": False}

    # Append a brief goal-confirmation closing when goal is achieved
    if state.get("goal_achieved") and agent_resp:
        intent_type = state.get("intent", {}).get("type", "")
        closings = {
            "schedule_appointment": " Is there anything else I can help you with?",
            "cancel_appointment": " The appointment has been cancelled. Is there anything else?",
            "reschedule_appointment": " The appointment has been rescheduled. Is there anything else?",
            "check_appointments": " Let me know if you need more details.",
            "patient_lookup": " Let me know if you need anything else.",
        }
        closing = closings.get(intent_type, "")
        # Only append if not already ending with a question
        if agent_resp.strip() and not agent_resp.strip().endswith("?"):
            agent_resp = agent_resp.strip() + closing

    return {**state, "final_response": agent_resp}


# ─── Build the router graph ───────────────────────────────────────────────────

def _build_router():
    graph = StateGraph(RouterState)

    graph.add_node("detect_intent", detect_intent)
    graph.add_node("appointment_agent", appointment_agent_node)
    graph.add_node("general_response", general_response_node)
    graph.add_node("finalize_response", finalize_response)

    graph.set_entry_point("detect_intent")
    graph.add_conditional_edges(
        "detect_intent",
        route_to_agent,
        {
            "appointment_agent": "appointment_agent",
            "general_response": "general_response",
        },
    )
    graph.add_edge("appointment_agent", "finalize_response")
    graph.add_edge("general_response", "finalize_response")
    graph.add_edge("finalize_response", END)

    return graph.compile()


_router_graph = None


def get_router_graph():
    global _router_graph
    if _router_graph is None:
        _router_graph = _build_router()
    return _router_graph


# ─── Public entry point ───────────────────────────────────────────────────────

_session_histories: dict[str, list[dict]] = {}


async def process_request(user_text: str, session_id: str) -> str:
    """
    Full pipeline: user text → intent → agent → response text.

    Args:
        user_text: Transcribed user speech
        session_id: Session identifier for conversation history

    Returns:
        Response text ready for TTS synthesis
    """
    history = _session_histories.setdefault(session_id, [])

    initial_state: RouterState = {
        "session_id": session_id,
        "user_text": user_text,
        "intent": None,
        "conversation_history": history.copy(),
        "agent_response": "",
        "final_response": "",
        "goal_achieved": False,
        "error": None,
    }

    router = get_router_graph()
    result = await router.ainvoke(initial_state)

    final_response = result.get("final_response") or result.get("agent_response", "I'm sorry, I could not process that.")

    # Update session history
    history.append({"role": "user", "text": user_text})
    history.append({"role": "assistant", "text": final_response})

    # Keep history bounded
    if len(history) > 20:
        _session_histories[session_id] = history[-20:]

    return final_response
