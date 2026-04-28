from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from models.state import AgentState
from agents.nodes import (
    intent_detector_node,
    lead_collector_node,
    submit_node,
    career_redirect_node,
    general_qa_node,
    should_switch_intent
)
from tools.lead_tools import get_lead_requirements

def route_from_start(state: AgentState):
    print("🚦 ROUTE FROM START:", state)

    current_intent = state.get("intent")
    lead_info = state.get("lead_info")

    # 1. TRAP: If currently traversing the Lead flow and there are missing fields
    if current_intent == "lead" and lead_info:
        required = get_lead_requirements()
        missing = [field for field in required if not getattr(lead_info, field)]

        if missing:
            # Only allow escape if they explicitly interrupt the flow (e.g. "actually I am looking for a job")
            if should_switch_intent(state):
                 print("🔄 Intent switch detected → letting detector re-run")
                 return "intent_detector"
            return "lead_collector"

    # 2. DEFAULT: If they are general chatting, or just finished a lead form earlier,
    # we MUST evaluate every new message they type dynamically by going to intent_detector!
    return "intent_detector"

def route_from_intent(state: AgentState):
    intent = state.get("intent")
    if intent == "lead":
        return "lead_collector"
    elif intent == "career":
        return "career_redirect"
    else:
        return "general_qa"

def route_from_lead_collector(state: AgentState):
    lead_info = state.get("lead_info")
    if not lead_info:
        return END

    required = get_lead_requirements()
    missing = [field for field in required if not getattr(lead_info, field)]

    if not missing:
        # All required parameters filled, finalize submission
        return "submit_lead"
    else:
        # A question was formulated to ask the user, so halt the graph returning the response
        return END

def build_graph():
    builder = StateGraph(AgentState)

    # 1. Register Nodes
    builder.add_node("intent_detector", intent_detector_node)
    builder.add_node("lead_collector", lead_collector_node)
    builder.add_node("submit_lead", submit_node)
    builder.add_node("career_redirect", career_redirect_node)
    builder.add_node("general_qa", general_qa_node)

    # 2. Build Edges & Routing Logic
    builder.add_conditional_edges(
        START,
        route_from_start,
        {
            "lead_collector": "lead_collector",
            "intent_detector": "intent_detector",
            "career_redirect": "career_redirect",
            "general_qa": "general_qa"
        }
    )

    builder.add_conditional_edges(
        "intent_detector",
        route_from_intent,
        {
            "lead_collector": "lead_collector",
            "career_redirect": "career_redirect",
            "general_qa": "general_qa"
        }
    )

    builder.add_conditional_edges(
        "lead_collector",
        route_from_lead_collector,
        {
            "submit_lead": "submit_lead",
            END: END
        }
    )

    # Closing edges
    builder.add_edge("career_redirect", END)
    builder.add_edge("general_qa", END)
    builder.add_edge("submit_lead", END)

    # Compile with MemorySaver to ensure session states are maintained by thread_id
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    return graph

agent_graph = build_graph()