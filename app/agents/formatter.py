"""
Formatter agent that creates final formatted response with TL;DR.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind

from openinference.semconv.trace import (
    SpanAttributes,
    OpenInferenceSpanKindValues,
)

from app.llm.ollama_client import OllamaClient, Message
from app.agents.reviewer import ReviewVerdict
from app.rag.retriever import RetrievedDocument

logger = logging.getLogger(__name__)


@dataclass
class FormattedResponse:
    """Final formatted response"""
    content: str
    tldr: str
    sources: List[dict]
    metadata: dict


class FormatterAgent:
    """Agent that formats final responses with TL;DR"""

    def __init__(self, llm_client: OllamaClient):
        self.llm_client = llm_client
        self.tracer = trace.get_tracer(__name__)

    def format(
        self,
        draft_answer: str,
        review_verdict: ReviewVerdict,
        used_rag: bool,
        route_path: str,
        context_docs: Optional[List[RetrievedDocument]] = None
    ) -> FormattedResponse:
        """
        Format final response with TL;DR and metadata.

        Args:
            draft_answer: Draft answer text
            review_verdict: Review verdict
            used_rag: Whether RAG was used
            route_path: Router path taken
            context_docs: Context documents (if RAG)

        Returns:
            Formatted response
        """
        with self.tracer.start_as_current_span(
            "agent.formatter",
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
                span.set_attribute(f"{SpanAttributes.METADATA}.review_label", review_verdict.label)

                # Build main content
                content_parts = []

                # Add answer
                content_parts.append(draft_answer)

                # Add review warning if needed
                if review_verdict.label != "good":
                    content_parts.append("\n\n---")
                    content_parts.append(
                        f"\n**Note:** This response may contain inaccuracies. "
                        f"Review: {review_verdict.rationale}"
                    )

                # Add sources if RAG was used
                sources = []
                if used_rag and context_docs:
                    content_parts.append("\n\n---\n")
                    content_parts.append("### Sources from Wikipedia\n")

                    # Deduplicate by title
                    seen_titles = set()
                    for doc in context_docs:
                        if doc.title not in seen_titles:
                            content_parts.append(f"- [{doc.title}]({doc.url})")
                            sources.append({
                                "title": doc.title,
                                "url": doc.url
                            })
                            seen_titles.add(doc.title)

                main_content = "\n".join(content_parts)

                # Generate TL;DR
                tldr = self._generate_tldr(draft_answer)

                # Add TL;DR to content
                full_content = f"{main_content}\n\n---\n**TL;DR:** {tldr}"

                # Build metadata
                metadata = {
                    "used_rag": used_rag,
                    "route_path": route_path,
                    "review_label": review_verdict.label,
                    "review_confidence": review_verdict.confidence,
                    "num_sources": len(sources)
                }

                span.set_attribute("format.tldr_length", len(tldr))
                span.set_attribute("format.total_length", len(full_content))
                span.set_status(Status(StatusCode.OK))

                return FormattedResponse(
                    content=full_content,
                    tldr=tldr,
                    sources=sources,
                    metadata=metadata
                )

            except Exception as e:
                logger.error(f"Formatting error: {e}")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                # Return basic formatted response
                return FormattedResponse(
                    content=draft_answer,
                    tldr="Error generating summary",
                    sources=[],
                    metadata={"error": str(e)}
                )

    def _generate_tldr(self, answer: str) -> str:
        """Generate TL;DR summary"""
        # Simpler, more direct prompt
        system_prompt = "You are a helpful assistant that creates brief summaries."
        user_prompt = f"""Create a brief 1-2 sentence summary of this answer:

{answer}

Summary:"""

        messages = [
            Message("system", system_prompt),
            Message("user", user_prompt)
        ]

        try:
            tldr = self.llm_client.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=200,  # Increased for more room
                span_name="llm.generate_tldr"
            )
            # Clean up
            tldr = tldr.strip()

            # Remove common prefixes
            prefixes = ["tl;dr:", "summary:", "tldr:"]
            for prefix in prefixes:
                if tldr.lower().startswith(prefix):
                    tldr = tldr[len(prefix):].strip()

            # If still empty, use fallback
            if not tldr:
                logger.warning("TL;DR generation returned empty string, using fallback")
                sentences = answer.split('. ')
                return sentences[0][:150] + "..." if len(sentences[0]) > 150 else sentences[0]

            return tldr
        except Exception as e:
            logger.warning(f"TL;DR generation failed: {e}")
            # Fallback: take first sentence
            sentences = answer.split('. ')
            return sentences[0][:150] + "..." if len(sentences[0]) > 150 else sentences[0]
