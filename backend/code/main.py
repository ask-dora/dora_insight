from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware # <--- Import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional, Dict, Any

from .database import Base, engine, get_db_session, init_db
from .models import ChatSession, Message as DBMessage # Renamed to avoid Pydantic model conflict
from .rag_services import generate_embedding, get_relevant_context, generate_llm_response

from pydantic import BaseModel
from datetime import datetime

# --- Pydantic Schemas ---
class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    session_id: Optional[int] = None # session_id is optional for starting a new chat

class MessageRead(MessageBase):
    id: int
    session_id: int
    sender: str
    timestamp: datetime
    # embedding: Optional[List[float]] # Optionally include embedding in response

    class Config:
        orm_mode = True

class ChatSessionRead(BaseModel):
    id: int
    created_at: datetime
    messages: List[MessageRead] = []

    class Config:
        orm_mode = True

# --- FastAPI App ---
app = FastAPI(title="Dora Insight RAG Backend")

# CORS Middleware Configuration
# origins that are allowed to make cross-origin requests.
# For development, [\"*\"] allows all. For production, specify your frontend domain(s).
origins = [
    "http://localhost",         # Common for local dev
    "http://localhost:5173",    # Default Vite dev server port
    "http://127.0.0.1",
    "http://127.0.0.1:5173",
    # Add any other origins your frontend might be served from during development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
async def on_startup():
    """Create database tables and ensure pgvector extension is enabled on startup."""
    await init_db() # <--- Call init_db here
    # The original Base.metadata.create_all is now called within init_db,
    # so we don't need to call it directly here anymore if init_db handles it.
    # If init_db only creates the extension, uncomment the line below.
    # For now, assuming init_db handles table creation as well.
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

@app.post("/chat/", response_model=ChatSessionRead, summary="Process a chat message")
async def process_chat_message(
    message_in: MessageCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Handles a user\'s chat message.
    - Creates a new session if session_id is not provided.
    - Generates embedding for the user\'s prompt.
    - Retrieves relevant context from past messages in the session using vector similarity search.
    - Gets a response from the LLM using the prompt and context.
    - Saves user message and LLM response (with embeddings) to the database.
    - Returns the updated chat session with all messages.
    """
    session: Optional[ChatSession] = None
    TOP_K_CONTEXT = 3 # Number of relevant messages to fetch for context

    # 1. Get or Create Chat Session
    if message_in.session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == message_in.session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail=f"Chat session with id {message_in.session_id} not found.")
    else:
        session = ChatSession()
        db.add(session)
        await db.flush() # To get session.id

    # 2. Process User Message
    user_prompt_text = message_in.content
    user_prompt_embedding = await generate_embedding(user_prompt_text)

    db_user_message = DBMessage(
        session_id=session.id,
        sender="user",
        content=user_prompt_text,
        embedding=user_prompt_embedding
    )
    db.add(db_user_message)
    await db.flush() # Ensure user message is in session and has an ID before fetching history

    # 3. Retrieve Relevant Context using Vector Similarity Search
    relevant_db_messages: List[DBMessage] = []
    if user_prompt_embedding:
        # Find messages in the same session, excluding the current one, order by similarity
        context_stmt = (
            select(DBMessage)
            .where(DBMessage.session_id == session.id)
            .where(DBMessage.id != db_user_message.id) # Exclude the user message we just added
            .where(DBMessage.embedding.isnot(None)) # Only consider messages with embeddings
            .order_by(DBMessage.embedding.l2_distance(user_prompt_embedding))
            .limit(TOP_K_CONTEXT)
        )
        result = await db.execute(context_stmt)
        relevant_db_messages = result.scalars().all()

    # Format messages for the get_relevant_context function
    past_messages_for_context: List[Dict[str, Any]] = [
        {"content": msg.content, "embedding": msg.embedding, "sender": msg.sender}
        for msg in relevant_db_messages
    ]
    
    relevant_context_str = await get_relevant_context(user_prompt_embedding, past_messages_for_context)

    # 4. Get LLM Response
    llm_response_text = await generate_llm_response(user_prompt_text, relevant_context_str)
    llm_response_embedding = await generate_embedding(llm_response_text)

    db_llm_message = DBMessage(
        session_id=session.id,
        sender="llm",
        content=llm_response_text,
        embedding=llm_response_embedding
    )
    db.add(db_llm_message)
    
    # 5. Commit session and messages
    await db.commit()
    await db.refresh(session) # Refresh to get all messages including the new ones with their IDs

    # Re-fetch the session with all its messages for the response
    # This ensures that the relationships are loaded correctly after commit.
    final_session_result = await db.execute(
        select(ChatSession).where(ChatSession.id == session.id)
    )
    final_session = final_session_result.scalar_one()
    
    return final_session


@app.get("/sessions/{session_id}", response_model=ChatSessionRead, summary="Get a specific chat session")
async def get_chat_session(session_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session

@app.get("/sessions/", response_model=List[ChatSessionRead], summary="List all chat sessions")
async def list_chat_sessions(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(ChatSession).order_by(ChatSession.created_at.desc()).offset(skip).limit(limit)
    )
    sessions = result.scalars().all()
    return sessions
