import os
import logging
import uuid
from fastapi import APIRouter, HTTPException
from agents.graph import agent_graph
from models.state import ChatRequest, ChatResponse, SessionResponse
from langchain_core.messages import HumanMessage

router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("copilot_chat")

@router.get("/rytsense/v1/session", response_model=SessionResponse)
async def create_session():
    """Generates a unique session ID for a new chat thread."""
    new_id = str(uuid.uuid4())
    logger.info(f"Generated new session ID: {new_id}")
    return SessionResponse(session_id=new_id)

@router.post("/rytsense/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main endpoint for copilot interactions.
    LangGraph will track memory via `thread_id` matched to the `session_id`.
    """
    try:
        logger.info(f"[Session: {request.session_id}] USER Input: {request.message}")
        
        config = {"configurable": {"thread_id": request.session_id}}
        
        result = agent_graph.invoke(
            {"messages": [HumanMessage(content=request.message)]}, 
            config=config
        )
        
        messages = result.get("messages", [])
        if messages:
             last_msg = messages[-1].content
             logger.info(f"[Session: {request.session_id}] BOT Reply: {last_msg}")
             return ChatResponse(response=last_msg)
        else:
             logger.warning(f"[Session: {request.session_id}] BOT Reply: (No response generated)")
             return ChatResponse(response="I'm not sure how to respond.")
             
    except Exception as e:
        logger.error(f"[Session: {request.session_id}] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
