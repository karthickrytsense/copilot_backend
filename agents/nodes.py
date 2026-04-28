from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from models.state import AgentState, LeadInfo
from tools.lead_tools import get_lead_requirements, submit_lead
from config import settings
from config.company_persona import PERSONA

# Initialize the OpenAI LLM explicitly
llm = ChatOpenAI(model="gpt-4o", api_key=settings.OPENAI_API_KEY, temperature=0.2)

def intent_detector_node(state: AgentState):
    """Classifies the user input into 'lead', 'career', or 'general'."""
    print("*"*30, "intent_detector_node")
    print("CURRENT STATE:", state)
    print("*"*30)

    # Only pass the last 4 messages to avoid getting anchored by previous lead collection
    recent_messages = state["messages"][-4:]
    conversation = "\n".join([f"{m.type}: {m.content}" for m in recent_messages])
    last_message = state["messages"][-1].content
    
    prompt = f"""
{PERSONA}

You are an intent detection routing assistant for a Rytsense Company.
Analyze the user's latest message, Conversation and return exactly ONE of the following words based on their intent:
1. "lead" - if they want to hire us, build a project, get a quote, or are asking about our services to become a client.
2. "career" - if they are asking about jobs, hiring, submitting resumes, or working for us.
3. "general" - if they are asking a general question, like where we are located or basic company info.
**Conversation: {conversation}**,
**User message: '{last_message}'**
Return ONLY the one-word intent.
"""
    
    response = llm.invoke([SystemMessage(content=prompt)])
    raw_intent = response.content.strip().lower()
    
    if "lead" in raw_intent:
        intent = "lead"
    elif "career" in raw_intent:
        intent = "career"
    else:
        intent = "general" # fallback routing
        
    print(f"[Intent Guard] LLM output: '{raw_intent}' -> Routed to: '{intent}'")
    return {"intent": intent}

def should_switch_intent(state: AgentState):
    last_msg = state["messages"][-1].content
    current_intent = state.get("intent")

    prompt = f"""
You are an intent guard.

Current intent: {current_intent}

User message: "{last_msg}"

Decide if the user EXPLICITLY changed their intent.

Rules:
- If current intent is "lead", and user is still talking about their project → answer NO
- Only say YES if user clearly switches topics (e.g., asks about jobs, careers, hiring)
- Do NOT switch for additional details about same topic

Answer ONLY: yes or no
"""

    response = llm.invoke([SystemMessage(content=prompt)])
    return response.content.strip().lower() == "yes"


def lead_collector_node(state: AgentState):
    """Analyzes missing fields and asks the user for the next piece of info."""
    print("*" * 30, "lead_collector_node")
    print("CURRENT STATE:", state)
    print("*" * 30)
    messages = state["messages"]
    lead_info = state.get("lead_info", LeadInfo())
    if lead_info is None:
        lead_info = LeadInfo()
    
    required = get_lead_requirements()
    missing_fields = []
    
    # 1. Update our knowledge base using structured output
    update_prompt = f"""
{PERSONA}

You are currently collecting information for a new project lead.
Extract any missing lead information from the conversation so far.
Only extract information that is explicitly stated. If you are not sure, leave it as null/None.
Current Lead Info known:
Name: {lead_info.name}
Email: {lead_info.email}
Phone: {lead_info.phone}
Company: {lead_info.company}
Project Description: {lead_info.project_description}
"""
    extractor_llm = llm.with_structured_output(LeadInfo)
    extracted_info = extractor_llm.invoke([SystemMessage(content=update_prompt)] + messages)
    
    # The LLM may only extract new things and return None for old fields, so we MUST merge.
    merged_info = LeadInfo(
        name=extracted_info.name or lead_info.name,
        email=extracted_info.email or lead_info.email,
        phone=extracted_info.phone or lead_info.phone,
        company=extracted_info.company or lead_info.company,
        project_description=extracted_info.project_description or lead_info.project_description
    )

    # Calculate what's still missing from the new state
    for field in required:
        if not getattr(merged_info, field):
            missing_fields.append(field)
            
    if not missing_fields:
        # Everything collected
        return {"lead_info": merged_info} 
        
    # 2. Ask for the first missing field
    ask_prompt = f"""
{PERSONA}

You are currently collecting information for a new project lead.
We currently need the following information from the user: {', '.join(missing_fields)}.
Ask the user conversationally for ONE of these missing pieces of information.
Do not ask for everything at once. Keep it natural and polite.

Important:
- Try to ask more about the Project information when you are asking for the **Project Description**
- Examples: What is the Project is about, Who are all the target customers for the projcts, How many Users May use the project.
"""
    response = llm.invoke([SystemMessage(content=ask_prompt)] + messages)
    return {"lead_info": merged_info, "messages": [response]}


def submit_node(state: AgentState):
    """Once all info is collected, submit to local CSV."""
    print("*" * 30, "submit_node")
    print("CURRENT STATE:", state)
    print("*" * 30)
    lead_info = state.get("lead_info")
    
    if lead_info:
        data = lead_info.model_dump()
        result_msg = submit_lead(data)
        # We append a system confirmation message and CLEAR the state so they don't get trapped further!
        return {
            "messages": [AIMessage(content=f"Thank you! Your information has been securely gathered. {result_msg} Our team will reach out soon!")],
            "intent": "general",
            "lead_info": LeadInfo() # Reset for the next time
        }
    return {"messages": [AIMessage(content="Something went wrong while submitting your info.")]}


def career_redirect_node(state: AgentState):
    """Redirects to careers."""
    print("*" * 30, "career_redirect_node")
    print("CURRENT STATE:", state)
    print("*" * 30)
    return {"messages": [AIMessage(content=f"It sounds like you're interested in joining our team! Please visit our careers page at https://example.com/careers to see open positions. Best of luck!")]}

def general_qa_node(state: AgentState):
    """Placeholder for RAG answers."""
    print("*" * 30, "general_qa_node")
    print("CURRENT STATE:", state)
    print("*" * 30)
    last_message = state["messages"][-1].content
    prompt = f"{PERSONA}\n\nAnswer this general query politely, stating we are a software agency. Query: {last_message}"
    response = llm.invoke([SystemMessage(content=prompt)])
    return {"messages": [response]}
