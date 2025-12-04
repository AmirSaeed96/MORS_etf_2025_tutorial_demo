"""
Router agent that decides whether to use RAG or not.
Uses LLM to intelligently route based on query intent.
"""

import logging
import json
from typing import Literal, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind

from openinference.semconv.trace import (
    SpanAttributes,
    OpenInferenceSpanKindValues,
)

logger = logging.getLogger(__name__)

RoutePath = Literal["rag", "no_rag"]


class RouterAgent:
    """Router agent with intelligent LLM-based routing"""

    def __init__(self, llm_client=None, rag_probability: float = 0.5):
        """
        Initialize router agent.

        Args:
            llm_client: LLM client for intelligent routing
            rag_probability: Fallback probability (if LLM fails)
        """
        self.llm_client = llm_client
        self.rag_probability = rag_probability
        self.tracer = trace.get_tracer(__name__)

    def route(
        self,
        query: str,
        conversation_history: Optional[list] = None,
        override: Optional[RoutePath] = None
    ) -> RoutePath:
        """
        Intelligently decide whether to use RAG or not.

        Args:
            query: User query
            conversation_history: Chat history
            override: Optional override ('rag' or 'no_rag')

        Returns:
            Route path: 'rag' or 'no_rag'
        """
        with self.tracer.start_as_current_span(
            "agent.router",
            kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Set OpenInference span kind for agent
                span.set_attribute(
                    SpanAttributes.OPENINFERENCE_SPAN_KIND,
                    OpenInferenceSpanKindValues.AGENT.value
                )
                span.set_attribute(SpanAttributes.INPUT_VALUE, query)

                # Handle override
                if override:
                    path = override
                    span.set_attribute(f"{SpanAttributes.METADATA}.override", True)
                    span.set_attribute(SpanAttributes.OUTPUT_VALUE, path)
                    logger.info(f"Router override: {path}")
                elif not self.llm_client:
                    # Fallback to RAG if no LLM client
                    path = "rag"
                    span.set_attribute(f"{SpanAttributes.METADATA}.fallback", True)
                    span.set_attribute(SpanAttributes.OUTPUT_VALUE, path)
                    logger.info(f"Router fallback (no LLM): {path}")
                else:
                    # Use LLM to make intelligent routing decision
                    path = self._intelligent_route(query, conversation_history, span)

                span.set_status(Status(StatusCode.OK))
                return path

            except Exception as e:
                logger.error(f"Router error: {e}")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                # Fallback to RAG
                return "rag"

    def _intelligent_route(
        self,
        query: str,
        conversation_history: Optional[list],
        parent_span
    ) -> RoutePath:
        """
        Use LLM to intelligently route the query.

        Routing logic:
        - Quantum physics questions → RAG (retrieve from knowledge base)
        - Conversation/summary questions → no RAG (use chat history)
        - General questions → no RAG (use model knowledge)
        """
        from app.llm.ollama_client import Message

        # Build routing prompt
        prompt = f"""You are a routing agent. Analyze this user query and decide whether to use RAG (knowledge retrieval) or not.

USER QUERY: {query}

ROUTING RULES:
1. If the query asks about quantum physics concepts, theories, or experiments → use RAG
2. If the query asks about the conversation history, summaries, or "what did we discuss" → do NOT use RAG
3. If the query is general chitchat or non-quantum topics → do NOT use RAG

Respond with ONLY a JSON object:
{{
    "use_rag": true or false,
    "reason": "brief explanation"
}}

JSON:"""

        try:
            # Call LLM
            response = self.llm_client.chat(
                messages=[Message("user", prompt)],
                temperature=0.1,
                span_name="llm.router_decision"
            )

            # Parse response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                use_rag = result.get("use_rag", True)
                reason = result.get("reason", "")

                path = "rag" if use_rag else "no_rag"

                # Set attributes
                parent_span.set_attribute(f"{SpanAttributes.METADATA}.routing_reason", reason)
                parent_span.set_attribute(f"{SpanAttributes.METADATA}.llm_decision", True)
                parent_span.set_attribute(SpanAttributes.OUTPUT_VALUE, path)

                logger.info(f"Router decision (LLM): {path} - {reason}")
                return path
            else:
                raise ValueError("Failed to parse LLM response")

        except Exception as e:
            logger.warning(f"LLM routing failed: {e}, defaulting to RAG")
            parent_span.set_attribute(f"{SpanAttributes.METADATA}.llm_failed", True)
            parent_span.set_attribute(SpanAttributes.OUTPUT_VALUE, "rag")
            return "rag"
