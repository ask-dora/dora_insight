from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
from pgvector.sqlalchemy import Vector

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) # <--- ADDED
    # other columns...

    messages = relationship("Message", back_populates="session", lazy="selectin") # <--- MODIFIED lazy loading

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    sender = Column(String, index=True, nullable=False)  # "user" or "llm"
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True) # Assuming Gemini embedding-001 (768 dimensions)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")