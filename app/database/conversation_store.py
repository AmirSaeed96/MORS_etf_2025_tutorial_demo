"""Conversation storage manager"""

import logging
from typing import List, Optional
from pathlib import Path

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session

from app.database.models import Base, ConversationMessage

logger = logging.getLogger(__name__)


class ConversationStore:
    """Manages conversation history storage"""

    def __init__(self, db_path: str = "conversations.db"):
        """
        Initialize conversation store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_url = f"sqlite:///{self.db_path}"

        # Create engine
        self.engine = create_engine(
            self.db_url,
            connect_args={"check_same_thread": False},
            echo=False
        )

        # Create tables
        Base.metadata.create_all(self.engine)

        # Session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info(f"Conversation store initialized at {self.db_path}")

    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> ConversationMessage:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation identifier
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional metadata

        Returns:
            Created message
        """
        session = self.get_session()
        try:
            message = ConversationMessage(
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_metadata=metadata or {}
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            logger.debug(f"Added message to conversation {conversation_id}")
            return message
        finally:
            session.close()

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[dict]:
        """
        Get conversation history.

        Args:
            conversation_id: Conversation identifier
            limit: Optional limit on number of messages (most recent)

        Returns:
            List of messages as dictionaries
        """
        session = self.get_session()
        try:
            query = session.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id
            ).order_by(ConversationMessage.timestamp)

            if limit:
                # Get last N messages
                query = session.query(ConversationMessage).filter(
                    ConversationMessage.conversation_id == conversation_id
                ).order_by(desc(ConversationMessage.timestamp)).limit(limit)

                messages = query.all()
                messages.reverse()  # Restore chronological order
            else:
                messages = query.all()

            return [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": msg.message_metadata
                }
                for msg in messages
            ]
        finally:
            session.close()

    def delete_conversation(self, conversation_id: str):
        """Delete a conversation"""
        session = self.get_session()
        try:
            session.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation_id
            ).delete()
            session.commit()
            logger.info(f"Deleted conversation {conversation_id}")
        finally:
            session.close()

    def list_conversations(self) -> List[str]:
        """List all conversation IDs"""
        session = self.get_session()
        try:
            result = session.query(
                ConversationMessage.conversation_id
            ).distinct().all()
            return [row[0] for row in result]
        finally:
            session.close()
