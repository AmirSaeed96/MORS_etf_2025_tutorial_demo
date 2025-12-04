"""Database models for conversation storage"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ConversationMessage(Base):
    """Model for storing conversation messages"""

    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Additional metadata (RAG info, etc.)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "metadata": self.message_metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
