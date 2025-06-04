from fastapi import FastAPI, Depends, HTTPException, Header, APIRouter # MODIFIED: Added APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional, Dict, Any

from .database import Base, engine, get_db_session, init_db
from .models import User, ChatSession, Message as DBMessage # Added User
from .rag_services import generate_embedding, get_relevant_context, generate_llm_response, get_github_data_for_llm, prepare_github_context_for_llm
from .integrations import router as integrations_router  # Import integrations router

from pydantic import BaseModel
from datetime import datetime, timedelta

# --- Pydantic Schemas ---
class UserBase(BaseModel):
    user_identifier: str

class UserCreate(UserBase):
    pass

class UserRead(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    session_id: Optional[int] = None
    # user_identifier: str # User identifier will be passed in header

class MessageRead(MessageBase):
    id: int
    session_id: int
    sender: str
    timestamp: datetime
    # embedding: Optional[List[float]] # Optionally include embedding in response

    class Config:
        orm_mode = True

class ChatSessionBase(BaseModel):
    title: Optional[str] = None

class ChatSessionCreate(ChatSessionBase):
    pass # user_id will be handled internally

class ChatSessionRead(ChatSessionBase): # Modified
    id: int
    user_id: int # Added
    created_at: datetime
    messages: List[MessageRead] = []
    title: Optional[str] = None # Ensure title is here

    class Config:
        orm_mode = True

# --- FastAPI App ---
app = FastAPI(title="Dora Insight RAG Backend")
router = APIRouter(prefix="/api") # ADDED: Create an APIRouter with /api prefix

# Include integrations router
app.include_router(integrations_router)

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

# Helper function to get or create user
async def get_or_create_user(user_identifier: str, db: AsyncSession) -> User:
    result = await db.execute(
        select(User).where(User.user_identifier == user_identifier)
    )
    user = result.scalar_one_or_none()
    if not user:
        user = User(user_identifier=user_identifier)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user

# @app.post("/chat/", response_model=ChatSessionRead, summary="Process a chat message for a user") # CHANGED to router
@router.post("/chat/", response_model=ChatSessionRead, summary="Process a chat message for a user")
async def process_chat_message(
    message_in: MessageCreate,
    db: AsyncSession = Depends(get_db_session),
    x_user_identifier: Optional[str] = Header(None, alias="X-User-Identifier"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Handles a user's chat message, associated with a user identifier.
    - Gets or creates the user based on X-User-Identifier or X-User-ID header.
    - Creates a new session for the user if session_id is not provided or if it doesn't belong to the user.
    - Generates embedding for the user's prompt.
    - Retrieves relevant context from past messages across all user sessions using vector similarity search.
    - Gets a response from the LLM using the prompt and context.
    - Saves user message and LLM response (with embeddings) to the database.
    - Returns the updated chat session with all messages.
    """
    
    # Use either header - support both for flexibility
    user_identifier = x_user_identifier or x_user_id
    
    if not user_identifier:
        raise HTTPException(status_code=400, detail="User identifier header (X-User-Identifier or X-User-ID) is required.")
    
    print(f"Processing chat message for user: {user_identifier}")
    
    user = await get_or_create_user(user_identifier, db)
    session: Optional[ChatSession] = None
    TOP_K_CONTEXT = 3
    # Consider messages from the last 30 days for performance optimization
    CONTEXT_DAYS_LOOKBACK = 30

    # 1. Get or Create Chat Session for the User
    if message_in.session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == message_in.session_id, ChatSession.user_id == user.id)
        )
        session = result.scalar_one_or_none()
        if not session:
            # If session not found for this user, or session_id is for another user, create a new one.
            # Or, you could raise an error: 
            # raise HTTPException(status_code=404, detail=f\"Chat session with id {message_in.session_id} not found for user {x_user_identifier}.\")
            # For now, let's create a new one if ID is provided but not valid for user
            session = ChatSession(user_id=user.id, title=message_in.content[:50]) # Use first 50 chars of prompt as title
            db.add(session)
            await db.flush() # To get session.id
    else:
        session = ChatSession(user_id=user.id, title=message_in.content[:50]) # Use first 50 chars of prompt as title
        db.add(session)
        await db.flush()

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
    await db.flush() # Ensure user message is in session and has an ID before fetching history    # 3. Retrieve Relevant Context using Vector Similarity Search
    relevant_db_messages: List[DBMessage] = []
    if user_prompt_embedding:
        # Search across all user's sessions for relevant context, not just current session
        # Include time-based filter for performance with very active users
        lookback_date = datetime.now() - timedelta(days=CONTEXT_DAYS_LOOKBACK)
        
        context_stmt = (
            select(DBMessage)
            .join(ChatSession, DBMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user.id) # Removed stray 's'
            .where(DBMessage.id != db_user_message.id) # Exclude the user message we just added
            .where(DBMessage.embedding.isnot(None)) # Only consider messages with embeddings
            .where(DBMessage.timestamp >= lookback_date) # Only consider recent messages for performance
            .order_by(DBMessage.embedding.l2_distance(user_prompt_embedding))
            .limit(TOP_K_CONTEXT)
        )
        result = await db.execute(context_stmt)
        relevant_db_messages = result.scalars().all()    # Format messages for the get_relevant_context function
    past_messages_for_context: List[Dict[str, Any]] = [
        {
            "content": msg.content, 
            "embedding": msg.embedding, 
            "sender": msg.sender,
            "session_id": msg.session_id,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
        }
        for msg in relevant_db_messages
    ]
    
    relevant_context_str = await get_relevant_context(user_prompt_embedding, past_messages_for_context)    # 4. Get LLM Response with GitHub MCP context if available
    print(f"Generating LLM response with GitHub MCP context for user: {user_identifier}")
    llm_response_text = await generate_llm_response(user_prompt_text, relevant_context_str, user_identifier=user_identifier)
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
    await db.refresh(session) 
    
    # Ensure title is part of the response if it was set
    if not session.title and message_in.content:
        session.title = message_in.content[:50] # Fallback title if somehow missed
        db.add(session) # Add to session if it was just created
        await db.commit()
        await db.refresh(session)


    final_session_result = await db.execute(
        select(ChatSession).where(ChatSession.id == session.id)
    )
    final_session = final_session_result.scalar_one()
    
    return final_session


# @app.get("/users/{user_identifier}/sessions/", response_model=List[ChatSessionRead], summary="List all chat sessions for a specific user") # CHANGED to router
@router.get("/users/{user_identifier}/sessions/", response_model=List[ChatSessionRead], summary="List all chat sessions for a specific user")
async def list_user_chat_sessions(user_identifier: str, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db_session)):
    user = await get_or_create_user(user_identifier, db) # Ensures user exists
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()
    if not sessions:
        return [] # Return empty list if no sessions, instead of 404
    return sessions

# @app.get("/sessions/{session_id}", response_model=ChatSessionRead, summary="Get a specific chat session for a user") # CHANGED to router
@router.get("/sessions/{session_id}", response_model=ChatSessionRead, summary="Get a specific chat session for a user")
async def get_chat_session(
    session_id: int, 
    db: AsyncSession = Depends(get_db_session),
    x_user_identifier: Optional[str] = Header(None, alias="X-User-Identifier"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")):
   
    # Use either header - support both for flexibility
    user_identifier = x_user_identifier or x_user_id
    
    if not user_identifier:
        raise HTTPException(status_code=400, detail="User identifier header (X-User-Identifier or X-User-ID) is required.")
    
    user = await get_or_create_user(user_identifier, db)

    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session not found for user {x_user_identifier}")
    return session

# Remove or update the old generic /sessions/ endpoint if it's no longer needed
# For now, I'll comment it out to avoid conflict.
# @app.get(\"/sessions/\", response_model=List[ChatSessionRead], summary=\"List all chat sessions\")
# async def list_chat_sessions(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db_session)):\n#     result = await db.execute(\n#         select(ChatSession).order_by(ChatSession.created_at.desc()).offset(skip).limit(limit)\n#     )\n#     sessions = result.scalars().all()\n#     return sessions

app.include_router(router) # ADDED: Include the router in the main app

# GitHub MCP test endpoint for direct testing
@router.post("/github/mcp-test", summary="Test the GitHub MCP integration directly")
async def test_github_mcp(
    query_type: str,
    user_identifier: str = Header(..., alias="X-User-ID"),
    repo: Optional[str] = None, 
    owner: Optional[str] = None, 
    issue_number: Optional[int] = None, 
    limit: int = 10
):
    """
    Test endpoint to directly invoke the GitHub MCP functionality.
    This is useful for debugging and testing the MCP implementation.
    """
    print(f"MCP Test request: user={user_identifier}, query_type={query_type}, repo={repo}, owner={owner}")
    
    # Using our updated get_github_data_for_llm function which now uses the modular structure
    result = await get_github_data_for_llm(
        user_identifier=user_identifier,
        query_type=query_type,
        repo=repo,
        owner=owner,
        issue_number=issue_number,
        limit=limit
    )
    
    return result
