from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from pgvector.sqlalchemy import Vector

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # For now, a simple user identifier. In a real app, this could be
    # an ID from Firebase Auth, Auth0, or a username, email, etc.
    user_identifier = Column(String, unique=True, index=True, nullable=False) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat_sessions = relationship("ChatSession", back_populates="user")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True) # New
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Add a title for the session, can be auto-generated from first user message
    title = Column(String, nullable=True) 


    user = relationship("User", back_populates="chat_sessions") # New
    messages = relationship("Message", back_populates="session", lazy="selectin", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    sender = Column(String, index=True, nullable=False)  # "user" or "llm"
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True) # Assuming Gemini embedding-001 (768 dimensions)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")