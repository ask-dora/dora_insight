from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
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
    integrations = relationship("UserIntegration", back_populates="user")
    integrations = relationship("UserIntegration", back_populates="user", cascade="all, delete-orphan")

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

class UserIntegration(Base):
    __tablename__ = "user_integrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    integration_type = Column(String(50), nullable=False)  # 'github', 'slack', etc.
    access_token = Column(Text, nullable=True)  # Encrypted OAuth token
    refresh_token = Column(Text, nullable=True)  # Encrypted refresh token
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    integration_user_id = Column(String, nullable=True)  # GitHub user ID
    integration_username = Column(String, nullable=True)  # GitHub username    connected_at = Column(DateTime(timezone=True), server_default=func.now())
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    integration_metadata = Column(JSONB, nullable=True)  # Additional integration-specific data

    user = relationship("User", back_populates="integrations")

    class Config:
        orm_mode = True