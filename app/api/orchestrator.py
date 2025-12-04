"""
Chat orchestrator that coordinates the agent workflow with OpenInference tracing.
"""

import logging
from typing import Optional, List
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind

from app.llm.ollama_client import OllamaClient
from app.rag.retriever import QuantumWikiRetriever
from app.agents.router import RouterAgent
from app.agents.answer_generator import AnswerGeneratorAgent
from app.agents.reviewer import AccuracyReviewerAgent
from app.agents.formatter import FormatterAgent
from app.database.conversation_store import ConversationStore
from app.config import settings

# OpenInference semantic conventions
from openinference.semconv.trace import (
    SpanAttributes,
    OpenInferenceSpanKindValues,
)

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """Orchestrates the multi-agent RAG workflow"""

    def __init__(
        self,
        llm_client: OllamaClient,
        retriever: QuantumWikiRetriever,
        conversation_store: ConversationStore
    ):
        self.llm_client = llm_client
        self.retriever = retriever
        self.conversation_store = conversation_store

        # Initialize agents with LLM client for intelligent routing
        self.router = RouterAgent(llm_client=llm_client, rag_probability=0.5)
        self.answer_generator = AnswerGeneratorAgent(llm_client)
        self.reviewer = AccuracyReviewerAgent(llm_client)
        self.formatter = FormatterAgent(llm_client)

        self.tracer = trace.get_tracer(__name__)

        logger.info("Chat orchestrator initialized")

    def process_message(
        self,
        conversation_id: str,
        user_message: str,
        override_routing: Optional[str] = None
    ) -> dict:
        """
        Process a user message through the agent workflow.

        Args:
            conversation_id: Conversation identifier
            user_message: User's message
            override_routing: Optional routing override ('rag' or 'no_rag')

        Returns:
            Response dictionary with content and metadata
        """
        with self.tracer.start_as_current_span(
            "chat.process_message",
            kind=SpanKind.SERVER
        ) as span:
            try:
                # Set OpenInference span kind for chain/agent workflow
                span.set_attribute(
                    SpanAttributes.OPENINFERENCE_SPAN_KIND,
                    OpenInferenceSpanKindValues.CHAIN.value
                )

                # Set session and input attributes
                span.set_attribute(SpanAttributes.SESSION_ID, conversation_id)
                span.set_attribute(SpanAttributes.INPUT_VALUE, user_message)
                span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "text/plain")

                # Get conversation history
                conversation_history = self.conversation_store.get_conversation_history(
                    conversation_id,
                    limit=settings.max_chat_history
                )

                # Step 1: Router decides path
                logger.info(f"[{conversation_id}] Router deciding path...")
                override = override_routing if override_routing != "auto" else None
                route_path = self.router.route(
                    query=user_message,
                    conversation_history=conversation_history,
                    override=override
                )
                logger.info(f"[{conversation_id}] Route: {route_path}")

                # Step 2: Retrieve context if RAG path
                context_docs = None
                if route_path == "rag":
                    logger.info(f"[{conversation_id}] Retrieving context...")
                    context_docs = self.retriever.retrieve(
                        query=user_message,
                        conversation_history=conversation_history
                    )
                    logger.info(f"[{conversation_id}] Retrieved {len(context_docs)} documents")

                # Step 3: Generate answer
                logger.info(f"[{conversation_id}] Generating answer...")
                generated_answer = self.answer_generator.generate(
                    query=user_message,
                    conversation_history=conversation_history,
                    route_path=route_path,
                    context_docs=context_docs
                )
                logger.info(f"[{conversation_id}] Answer generated ({len(generated_answer.content)} chars)")

                # Step 4: Review answer
                logger.info(f"[{conversation_id}] Reviewing answer...")
                review_verdict = self.reviewer.review(
                    query=user_message,
                    draft_answer=generated_answer.content,
                    used_rag=generated_answer.used_rag,
                    context_docs=context_docs
                )
                logger.info(
                    f"[{conversation_id}] Review: {review_verdict.label} "
                    f"(confidence: {review_verdict.confidence})"
                )

                # Step 5: Format response
                logger.info(f"[{conversation_id}] Formatting response...")
                formatted_response = self.formatter.format(
                    draft_answer=generated_answer.content,
                    review_verdict=review_verdict,
                    used_rag=generated_answer.used_rag,
                    route_path=route_path,
                    context_docs=context_docs
                )
                logger.info(f"[{conversation_id}] Response formatted with TL;DR")

                # Store messages
                self.conversation_store.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_message
                )

                self.conversation_store.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=formatted_response.content,
                    metadata=formatted_response.metadata
                )

                # Build response
                response = {
                    "content": formatted_response.content,
                    "metadata": {
                        "used_rag": generated_answer.used_rag,
                        "review_label": review_verdict.label,
                        "router_path": route_path,
                        "context_sources": formatted_response.sources,
                        "review_confidence": review_verdict.confidence,
                        "tldr": formatted_response.tldr
                    }
                }

                # Set output value using OpenInference conventions
                span.set_attribute(SpanAttributes.OUTPUT_VALUE, formatted_response.content)
                span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "text/plain")

                # Set metadata attributes
                span.set_attribute(f"{SpanAttributes.METADATA}.route_path", route_path)
                span.set_attribute(f"{SpanAttributes.METADATA}.used_rag", generated_answer.used_rag)
                span.set_attribute(f"{SpanAttributes.METADATA}.review_label", review_verdict.label)
                span.set_attribute(f"{SpanAttributes.METADATA}.review_confidence", review_verdict.confidence)

                span.set_status(Status(StatusCode.OK))

                logger.info(f"[{conversation_id}] Message processed successfully")
                return response

            except Exception as e:
                logger.error(f"[{conversation_id}] Error processing message: {e}")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
