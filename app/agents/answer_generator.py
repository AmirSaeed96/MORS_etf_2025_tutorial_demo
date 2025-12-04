"""
Answer generator agent that creates draft responses.
Handles both RAG and non-RAG paths.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind

from openinference.semconv.trace import (
    SpanAttributes,
    OpenInferenceSpanKindValues,
)

from app.llm.ollama_client import OllamaClient, Message
from app.rag.retriever import RetrievedDocument

logger = logging.getLogger(__name__)


@dataclass
class GeneratedAnswer:
    """Generated answer with metadata"""
    content: str
    used_rag: bool
    context_docs: Optional[List[RetrievedDocument]] = None
    route_path: str = "unknown"


class AnswerGeneratorAgent:
    """Agent that generates draft answers"""

    def __init__(self, llm_client: OllamaClient):
        self.llm_client = llm_client
        self.tracer = trace.get_tracer(__name__)

    def generate(
        self,
        query: str,
        conversation_history: List[dict],
        route_path: str,
        context_docs: Optional[List[RetrievedDocument]] = None
    ) -> GeneratedAnswer:
        """
        Generate answer based on route path.

        Args:
            query: User query
            conversation_history: Chat history
            route_path: 'rag' or 'no_rag'
            context_docs: Retrieved documents (if RAG path)

        Returns:
            Generated answer
        """
        with self.tracer.start_as_current_span(
            "agent.answer_generator",
            kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Set OpenInference span kind for agent
                span.set_attribute(
                    SpanAttributes.OPENINFERENCE_SPAN_KIND,
                    OpenInferenceSpanKindValues.AGENT.value
                )
                span.set_attribute(SpanAttributes.INPUT_VALUE, query)
                span.set_attribute(f"{SpanAttributes.METADATA}.route", route_path)
                span.set_attribute(f"{SpanAttributes.METADATA}.has_context", context_docs is not None)

                if route_path == "rag" and context_docs:
                    answer_text = self._generate_with_rag(
                        query, conversation_history, context_docs
                    )
                    used_rag = True
                else:
                    answer_text = self._generate_without_rag(
                        query, conversation_history
                    )
                    used_rag = False
                    context_docs = None

                span.set_attribute(SpanAttributes.OUTPUT_VALUE, answer_text)
                span.set_status(Status(StatusCode.OK))

                return GeneratedAnswer(
                    content=answer_text,
                    used_rag=used_rag,
                    context_docs=context_docs,
                    route_path=route_path
                )

            except Exception as e:
                logger.error(f"Answer generation error: {e}")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def _generate_with_rag(
        self,
        query: str,
        conversation_history: List[dict],
        context_docs: List[RetrievedDocument]
    ) -> str:
        """Generate answer using RAG context"""
        # Format context
        context_parts = ["CONTEXT FROM WIKIPEDIA:\n"]
        for i, doc in enumerate(context_docs[:5], 1):  # Limit to top 5
            context_parts.append(f"\nSource {i}: {doc.title}")
            context_parts.append(f"{doc.content}\n")

        context_text = "\n".join(context_parts)

        # Build system prompt
        system_prompt = """You are a helpful quantum physics assistant. Answer questions based ONLY on the provided Wikipedia context.

Instructions:
- Use ONLY information from the provided context to answer
- If the context doesn't contain enough information, say so clearly
- Be concise but accurate
- Cite sources when possible (mention article titles)
- If you're uncertain, express that uncertainty
- Do not make up or infer information not in the context"""

        # Build user prompt
        user_prompt = f"""{context_text}

QUESTION: {query}

Please provide a clear answer based on the context above."""

        # Build messages
        messages = [Message("system", system_prompt)]

        # Add conversation history (last N turns)
        for msg in conversation_history[-6:]:  # Last 3 exchanges
            messages.append(Message(msg["role"], msg["content"]))

        # Add current query
        messages.append(Message("user", user_prompt))

        # Generate
        answer = self.llm_client.chat(
            messages=messages,
            temperature=0.3,  # Lower temperature for factual accuracy
            span_name="llm.generate_with_rag"
        )

        return answer

    def _generate_without_rag(
        self,
        query: str,
        conversation_history: List[dict]
    ) -> str:
        """Generate answer without RAG (using model knowledge only)"""
        system_prompt = """You are a knowledgeable quantum physics assistant. Answer questions about quantum mechanics and related topics using your knowledge.

Instructions:
- Provide clear, accurate explanations
- Be honest about uncertainty or limitations
- Use examples when helpful
- Keep responses concise but informative"""

        # Build messages
        messages = [Message("system", system_prompt)]

        # Add conversation history
        for msg in conversation_history[-6:]:
            messages.append(Message(msg["role"], msg["content"]))

        # Add current query
        messages.append(Message("user", query))

        # Generate
        answer = self.llm_client.chat(
            messages=messages,
            temperature=0.7,
            span_name="llm.generate_without_rag"
        )

        return answer
