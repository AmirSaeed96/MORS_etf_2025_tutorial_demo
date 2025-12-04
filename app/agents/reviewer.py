"""
Accuracy reviewer agent that checks answers for hallucinations and correctness.
"""

import json
import logging
from typing import Optional, List, Literal
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

ReviewLabel = Literal["good", "needs_revision", "bad"]


@dataclass
class ReviewVerdict:
    """Review verdict from accuracy checker"""
    label: ReviewLabel
    rationale: str
    suggestions: str
    confidence: float


class AccuracyReviewerAgent:
    """Agent that reviews answers for accuracy"""

    def __init__(self, llm_client: OllamaClient):
        self.llm_client = llm_client
        self.tracer = trace.get_tracer(__name__)

    def review(
        self,
        query: str,
        draft_answer: str,
        used_rag: bool,
        context_docs: Optional[List[RetrievedDocument]] = None
    ) -> ReviewVerdict:
        """
        Review answer for accuracy.

        Args:
            query: Original user query
            draft_answer: Generated answer to review
            used_rag: Whether RAG was used
            context_docs: Context documents (if RAG was used)

        Returns:
            Review verdict
        """
        with self.tracer.start_as_current_span(
            "agent.reviewer",
            kind=SpanKind.INTERNAL
        ) as span:
            try:
                # Set OpenInference span kind for agent
                span.set_attribute(
                    SpanAttributes.OPENINFERENCE_SPAN_KIND,
                    OpenInferenceSpanKindValues.AGENT.value
                )
                span.set_attribute(SpanAttributes.INPUT_VALUE, draft_answer)
                span.set_attribute(f"{SpanAttributes.METADATA}.used_rag", used_rag)
                span.set_attribute(f"{SpanAttributes.METADATA}.has_context", context_docs is not None)

                if used_rag and context_docs:
                    verdict = self._review_with_context(
                        query, draft_answer, context_docs
                    )
                else:
                    verdict = self._review_without_context(
                        query, draft_answer
                    )

                span.set_attribute("review.label", verdict.label)
                span.set_attribute("review.confidence", verdict.confidence)
                span.set_status(Status(StatusCode.OK))

                logger.info(f"Review verdict: {verdict.label} (confidence: {verdict.confidence})")
                return verdict

            except Exception as e:
                logger.error(f"Review error: {e}")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                # Return safe fallback
                return ReviewVerdict(
                    label="needs_revision",
                    rationale="Review failed due to error",
                    suggestions="Please verify the response manually",
                    confidence=0.0
                )

    def _review_with_context(
        self,
        query: str,
        draft_answer: str,
        context_docs: List[RetrievedDocument]
    ) -> ReviewVerdict:
        """Review answer against provided context"""
        # Format context
        context_text = "\n\n".join([
            f"Source: {doc.title}\n{doc.content}"
            for doc in context_docs[:3]
        ])

        review_prompt = f"""You are an accuracy reviewer for quantum physics explanations.

TASK: Review the answer below for accuracy and support from the provided context.

CONTEXT:
{context_text}

QUESTION: {query}

ANSWER TO REVIEW:
{draft_answer}

INSTRUCTIONS:
1. Check if the answer is supported by the context
2. Identify any claims NOT supported by the context
3. Rate the answer as:
   - "good": Well supported, accurate
   - "needs_revision": Some unsupported claims or minor issues
   - "bad": Mostly unsupported or contains clear errors

Provide your review in this JSON format:
{{
    "label": "good|needs_revision|bad",
    "rationale": "Brief explanation of your assessment",
    "suggestions": "Specific improvements (if needed)",
    "confidence": 0.0-1.0
}}

REVIEW (JSON only):"""

        messages = [Message("user", review_prompt)]

        response = self.llm_client.chat(
            messages=messages,
            temperature=0.1,  # Low temperature for consistent evaluation
            span_name="llm.review_with_context"
        )

        # Parse JSON response
        verdict = self._parse_verdict(response)
        return verdict

    def _review_without_context(
        self,
        query: str,
        draft_answer: str
    ) -> ReviewVerdict:
        """Review answer for general correctness (no context available)"""
        review_prompt = f"""You are an accuracy reviewer for quantum physics explanations.

TASK: Review the answer below for general correctness and common misconceptions.

QUESTION: {query}

ANSWER TO REVIEW:
{draft_answer}

INSTRUCTIONS:
1. Check for obvious errors or misconceptions
2. Verify that quantum physics concepts are used correctly
3. Rate the answer as:
   - "good": Appears correct, no obvious errors
   - "needs_revision": Some questionable claims
   - "bad": Contains clear errors or misconceptions

Provide your review in this JSON format:
{{
    "label": "good|needs_revision|bad",
    "rationale": "Brief explanation of your assessment",
    "suggestions": "Specific improvements (if needed)",
    "confidence": 0.0-1.0
}}

REVIEW (JSON only):"""

        messages = [Message("user", review_prompt)]

        response = self.llm_client.chat(
            messages=messages,
            temperature=0.1,
            span_name="llm.review_without_context"
        )

        verdict = self._parse_verdict(response)
        return verdict

    def _parse_verdict(self, response: str) -> ReviewVerdict:
        """Parse JSON verdict from LLM response"""
        try:
            # Try to extract JSON from response
            # Sometimes LLM adds extra text, so look for {...}
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
            else:
                data = json.loads(response)

            return ReviewVerdict(
                label=data.get("label", "needs_revision"),
                rationale=data.get("rationale", ""),
                suggestions=data.get("suggestions", ""),
                confidence=float(data.get("confidence", 0.5))
            )
        except Exception as e:
            logger.warning(f"Failed to parse review verdict: {e}")
            # Fallback verdict
            return ReviewVerdict(
                label="needs_revision",
                rationale="Could not parse review",
                suggestions="Manual verification recommended",
                confidence=0.5
            )
