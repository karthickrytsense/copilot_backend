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


def _extract_name_from_conversation(messages) -> str | None:
    """Uses LLM to extract name from anywhere in the conversation."""
    conversation = "\n".join([f"{m.type}: {m.content}" for m in messages])
    prompt = f"""
Extract the person's full name from this conversation.

Look for patterns like:
- "I'm John", "I am John Smith", "My name is John"
- "This is John", "Hi, John here"
- Name given directly when asked

Conversation:
{conversation}

Rules:
- Return ONLY the name, nothing else.
- Do NOT return company names.
- If no name is found, return the word: null
"""
    response = llm.invoke([SystemMessage(content=prompt)])
    result = response.content.strip()
    return None if result.lower() == "null" or not result else result


def _is_project_description_valid(description: str) -> bool:
    """Checks if project description has enough detail."""
    if not description:
        return False
    vague_phrases = [
        "interested in", "want to do a project", "need help",
        "looking for", "want to build something", "project with rytsense"
    ]
    desc_lower = description.lower()
    if any(phrase in desc_lower for phrase in vague_phrases):
        return False
    return len(description.split()) >= 10


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

    last_bot_message = next(
        (m.content for m in reversed(messages) if m.type == "ai"), ""
    )
    last_user_message = messages[-1].content.strip() if messages else ""

    # 1. Direct mapping only for project_description
    # When the bot asked for project details, directly store the user's reply
    project_desc_keywords = ["about your project", "more about your project", "tell me more"]
    direct_project_desc = None
    if (
        not lead_info.project_description
        and any(kw in last_bot_message.lower() for kw in project_desc_keywords)
        and last_user_message
    ):
        direct_project_desc = last_user_message

    # 2. LLM extraction for all other fields
    update_prompt = f"""
You are extracting lead information from a conversation.

Current Lead Info already known (do not overwrite with None):
Name: {lead_info.name}
Email: {lead_info.email}
Phone: {lead_info.phone}
Company: {lead_info.company}
Project Description: {lead_info.project_description}

Instructions:
- Extract any NEW information from the conversation that fills a missing field.
- For "name": extract the person's full name if they mention it. Do NOT use company name as name.
- For "phone": extract any 10+ digit number as phone.
- For "project_description": extract any description of the project the user mentions.
- Only extract what is clearly stated. Leave unknown fields as null.
"""
    extractor_llm = llm.with_structured_output(LeadInfo)
    extracted_info = extractor_llm.invoke([SystemMessage(content=update_prompt)] + messages)

    # 3. Merge — direct_project_desc is the final fallback for project_description
    merged_info = LeadInfo(
        name=extracted_info.name or lead_info.name,
        email=extracted_info.email or lead_info.email,
        phone=extracted_info.phone or lead_info.phone,
        company=extracted_info.company or lead_info.company,
        project_description=extracted_info.project_description or lead_info.project_description or direct_project_desc,
    )

    # 5. If name still missing, try dedicated name extraction from full conversation
    if not merged_info.name:
        extracted_name = _extract_name_from_conversation(messages)
        if extracted_name:
            merged_info = LeadInfo(
                name=extracted_name,
                email=merged_info.email,
                phone=merged_info.phone,
                company=merged_info.company,
                project_description=merged_info.project_description,
            )

    # 6. Calculate missing fields
    missing_fields = [field for field in required if not getattr(merged_info, field)]

    if not missing_fields:
        return {"lead_info": merged_info}

    # 7. Ask for the next missing field
    next_field = missing_fields[0]
    field_questions = {
        "name": "Could I get your full name, please?",
        "email": "Could you share your email address so we can reach you?",
        "phone": "Could I have your phone number, please?",
        "company": "What is the name of your company?",
        "project_description": (
            "Could you tell me more about your project? "
            "For example — what is it about, who are the target users, and what scale are you expecting?"
        )
    }
    question = field_questions.get(next_field, f"Could you please provide your {next_field}?")
    return {"lead_info": merged_info, "messages": [AIMessage(content=question)]}


def submit_node(state: AgentState):
    """Once all info is collected, submit to local CSV."""
    print("*" * 30, "submit_node")
    print("CURRENT STATE:", state)
    print("*" * 30)
    lead_info = state.get("lead_info")
    
    if lead_info:
        data = lead_info.model_dump()
        result_msg = submit_lead(data)
        return {
            "messages": [AIMessage(content="Thank you! Your information has been securely gathered. Would you like to schedule a meeting with our team? Please pick a date and time that works for you.")],
            "intent": "general",
            "show_calendar": True
        }
    return {"messages": [AIMessage(content="Something went wrong while submitting your info.")], "show_calendar": False}


def career_redirect_node(state: AgentState):
    """Redirects to careers."""
    print("*" * 30, "career_redirect_node")
    print("CURRENT STATE:", state)
    print("*" * 30)
    return {"messages": [AIMessage(content=f"It sounds like you're interested in joining our team! Please visit our [careers page](https://rytsensetech.com/company/career/) to see open positions. Best of luck!")]}

def general_qa_node(state: AgentState):
    """Placeholder for RAG answers."""
    print("*" * 30, "general_qa_node")
    print("CURRENT STATE:", state)
    print("*" * 30)
    last_message = state["messages"][-1].content
    prompt = f"{PERSONA}\n\nAnswer this general query politely, stating we are a software agency. Query: {last_message}"
    response = llm.invoke([SystemMessage(content=prompt)])
    return {"messages": [response]}
