import os
import logging
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow
from agents.graph import agent_graph
from models.state import ChatRequest, ChatResponse, SessionResponse, BookMeetingRequest, BookMeetingResponse
from tools.calendar_tools import create_calendar_event
from langchain_core.messages import HumanMessage
from config import settings

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

        # Read show_calendar from persisted state so it stays True across multiple messages
        # until the meeting is booked
        current_state = agent_graph.get_state(config)
        show_calendar = current_state.values.get("show_calendar", False) if current_state else False

        if messages:
             last_msg = messages[-1].content
             logger.info(f"[Session: {request.session_id}] BOT Reply: {last_msg} | show_calendar: {show_calendar}")
             return ChatResponse(response=last_msg, show_calendar=show_calendar)
        else:
             logger.warning(f"[Session: {request.session_id}] BOT Reply: (No response generated)")
             return ChatResponse(response="I'm not sure how to respond.")

    except Exception as e:
        logger.error(f"[Session: {request.session_id}] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rytsense/v1/book-meeting", response_model=BookMeetingResponse)
async def book_meeting_endpoint(request: BookMeetingRequest):
    """
    Books a Google Calendar meeting after the lead selects date/time from the frontend calendar UI.
    Fetches lead name and email from session state, creates the calendar event.
    Google Calendar automatically sends invite emails to both the lead and the owner.
    """
    try:
        logger.info(f"[Session: {request.session_id}] BOOK MEETING: {request.date} {request.time} ({request.timezone})")

        config = {"configurable": {"thread_id": request.session_id}}
        state = agent_graph.get_state(config)

        if not state or not state.values:
            raise HTTPException(status_code=404, detail="Session not found.")

        lead_info = state.values.get("lead_info")

        if not lead_info or not lead_info.email or not lead_info.name:
            raise HTTPException(status_code=400, detail="Lead info incomplete. Cannot book meeting.")

        result = create_calendar_event(
            lead_name=lead_info.name,
            lead_email=lead_info.email,
            date=request.date,
            time=request.time,
            lead_timezone=request.timezone,
        )

        logger.info(f"[Session: {request.session_id}] MEETING BOOKING: success={result['success']}")

        # Clear lead_info and show_calendar from session state after booking
        if result["success"]:
            from models.state import LeadInfo
            agent_graph.update_state(config, {"lead_info": LeadInfo(), "show_calendar": False})

        return BookMeetingResponse(
            success=result["success"],
            message=result["message"],
            event_link=result.get("event_link", ""),
            meet_link=result.get("meet_link", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Session: {request.session_id}] BOOK MEETING ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


SCOPES = ["https://www.googleapis.com/auth/calendar"]
REDIRECT_URI = "http://172.29.71.77:8080/auth/google/callback"


@router.get("/auth/google")
async def google_auth():
    """
    Step 1: Redirect user to Google OAuth2 login page.
    Open this URL in the browser of whoever needs to authorize (e.g. ramkumar@rytsensetech.com).
    """
    if not settings.GOOGLE_WEB_CLIENT_ID or not settings.GOOGLE_WEB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GOOGLE_WEB_CLIENT_ID and GOOGLE_WEB_CLIENT_SECRET not set in .env")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_WEB_CLIENT_ID,
                "client_secret": settings.GOOGLE_WEB_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return RedirectResponse(auth_url)


@router.get("/auth/google/callback")
async def google_auth_callback(code: str):
    """
    Step 2: Google redirects here after login.
    Exchanges the code for a refresh token and displays it.
    """
    if not settings.GOOGLE_WEB_CLIENT_ID or not settings.GOOGLE_WEB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GOOGLE_WEB_CLIENT_ID and GOOGLE_WEB_CLIENT_SECRET not set in .env")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_WEB_CLIENT_ID,
                "client_secret": settings.GOOGLE_WEB_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    flow.fetch_token(code=code)
    refresh_token = flow.credentials.refresh_token

    logger.info(f"[Auth] New refresh token generated: {refresh_token[:10]}...")

    return HTMLResponse(f"""
        <html>
        <body style="font-family: sans-serif; padding: 40px;">
            <h2>Authorization Successful!</h2>
            <p>Copy the refresh token below and add it to your <code>.env</code> file:</p>
            <pre style="background:#f4f4f4; padding:16px; border-radius:8px; word-break:break-all;">
GOOGLE_OAUTH_REFRESH_TOKEN={refresh_token}
            </pre>
            <p>Then restart the server.</p>
        </body>
        </html>
    """)
