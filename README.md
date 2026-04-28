# Lead Capture Chatbot - Project Approach & Architecture

## Overview
This project is an intelligent lead capture chatbot built using a modern, asynchronous AI stack (FastAPI, LangGraph, LangChain, OpenAI). The system is designed to classify user intents (e.g., lead, career, general) and dynamically collect lead information (name, email, phone, company, project description) through a conversational interface.

To ensure a robust and maintainable development cycle, the project is structured in phases. 

---

## 🏗️ Phased Development Approach

### **Phase 1: Core Lead Capture System (Current Focus)**
In this initial phase, we are building the fundamental StateGraph, basic API structure, and saving lead submissions into a local CSV file.

**Key Components in Phase 1:**
- **StateGraph (LangGraph):** A stateful conversation graph that manages transitions between `Intent Detection` and `Lead Collection`.
- **Intent Classification:** The system will classify user inputs into three categories: `lead`, `career`, or `general`.
    - If `career` -> Redirect to the careers page.
    - If `general` -> General default fallback (RAG integration will come in later phases).
    - If `lead` -> Enter the lead collection workflow.
- **Conversational Lead Gathering:** The agent will use OpenAI tool calling to check which fields are missing (name, email, phone, company, project description) and ask the user for them conversationally over multiple turns without overwhelming them.
- **Local CSV Storage:** When all lead parameters are gathered, trigger the `submit_lead` tool to append the collected lead accurately into a local CSV file (e.g. `leads.csv`). Google Sheets integration will follow validation.
- **In-Memory State:** We will use LangGraph's native thread-level memory (`MemorySaver` checkpointer). This means we do not need LangChain's `ConversationBufferMemory`. When a request comes in with a specific `session_id`, it maps to a LangGraph `thread_id`. A new `session_id` automatically gets a fresh, empty memory state, while an existing one resumes conversationally.
- **FastAPI Endpoints:**
    - `POST /chat` — Send a message and session ID, evaluate state, and return the agent response.
    - `GET /session/{session_id}` — Retrieve the current chat history and collected lead state.

### **Phase 2: Database Persistence (Next Phase)**
Once the graph logic from Phase 1 is verified, we will introduce a database layer to allow persistent sessions.
- **MongoDB Integration (Motor Async):** Store chat sessions, user histories, detected intents, and progressively upsert lead states turn-by-turn.

### **Phase 3: RAG & Google Sheets Integrations (Future Phase)**
- **Qdrant Vector Store:** Introduce Qdrant and OpenAI embeddings (`text-embedding-3-small`) to answer `general` intent questions accurately using company context (services, FAQs, etc.).
- **Google Sheets API:** Migrate the local CSV lead submission to append directly to a designated Google Sheet using a service account.

---

## 📁 Proposed Project Structure
```text
copilot_backend/
├── agents/             # LangGraph state definitions, nodes, and graph compilation
├── tools/              # LangChain/OpenAI tools (get_lead_requirements, submit_lead)
├── scripts/
│   └── routes.py       # FastAPI endpoint definitions (/chat, /session)
├── models/             # Pydantic models for request/response schemas and state
├── config/             # Environment variable management (.env parsing)
├── database/           # MongoDB and Qdrant connection managers (Phases 2 & 3)
├── .env.example        # Example environment variables
├── requirements.txt    # Python dependencies
└── run.py              # Application entry point to run uvicorn programmatically
```

## 🚀 How to Run Locally (Phase 1)
*Instructions will be finalized once Phase 1 code is generated.*

1. **Clone & Setup Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Configure Secrets:**
   Copy `.env.example` to `.env` and fill in your `OPENAI_API_KEY`.
3. **Run the Server:**
   ```bash
   python run.py
   ```
4. **Test the API:**
   Navigate to `http://localhost:8000/docs` to use the Swagger UI to test the `/chat` endpoint.