from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

# -----------------
# API Models
# -----------------
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str

class SessionResponse(BaseModel):
    session_id: str

#-----------------
# State Models
#-----------------
class LeadInfo(BaseModel):
    name: Optional[str] = Field(default=None, description="The full name of the lead.")
    email: Optional[str] = Field(default=None, description="The email address of the lead.")
    phone: Optional[str] = Field(default=None, description="The phone number of the lead.")
    company: Optional[str] = Field(default=None, description="The company the lead works for.")
    project_description: Optional[str] = Field(default=None, description="A description of the project.")

class AgentState(TypedDict):
    """
    Represents the internal state of the LangGraph agent for a single session thread.
    The messages list is automatically populated/updated by LangGraph's checkpointer.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    lead_info: LeadInfo
