"""
Ollama LLM client with Phoenix/OpenTelemetry instrumentation using OpenInference conventions.
"""

import json
import logging
from typing import List, Dict, Optional, Any
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, SpanKind

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

# OpenInference semantic conventions
from openinference.semconv.trace import (
    SpanAttributes,
    OpenInferenceMimeTypeValues,
    OpenInferenceSpanKindValues,
)

logger = logging.getLogger(__name__)


class Message:
    """Chat message"""
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class OllamaClient:
    """Client for Ollama API with Phoenix tracing"""

    def __init__(
        self,
        host: str = None,
        model: str = None,
        timeout: int = None
    ):
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout

        self.client = httpx.Client(timeout=self.timeout)
        self.tracer = trace.get_tracer(__name__)

        logger.info(f"Initialized Ollama client: {self.host}, model: {self.model}")

    def _build_api_url(self, endpoint: str) -> str:
        """Build full API URL"""
        return f"{self.host}{endpoint}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        span_name: str = "ollama.chat"
    ) -> str:
        """
        Send chat request to Ollama API with OpenInference tracing.

        Args:
            messages: List of chat messages
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            span_name: Name for the trace span

        Returns:
            Generated response text
        """
        with self.tracer.start_as_current_span(
            span_name,
            kind=SpanKind.CLIENT
        ) as span:
            try:
                # Set OpenInference span kind
                span.set_attribute(
                    SpanAttributes.OPENINFERENCE_SPAN_KIND,
                    OpenInferenceSpanKindValues.LLM.value
                )

                # Set LLM attributes using OpenInference conventions
                span.set_attribute(SpanAttributes.LLM_MODEL_NAME, self.model)
                span.set_attribute(SpanAttributes.LLM_INVOCATION_PARAMETERS, json.dumps({
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }))

                # Set input messages
                for idx, msg in enumerate(messages):
                    span.set_attribute(
                        f"{SpanAttributes.LLM_INPUT_MESSAGES}.{idx}.message.role",
                        msg.role
                    )
                    span.set_attribute(
                        f"{SpanAttributes.LLM_INPUT_MESSAGES}.{idx}.message.content",
                        msg.content
                    )

                # Prepare request payload
                payload = {
                    "model": self.model,
                    "messages": [msg.to_dict() for msg in messages],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                    }
                }

                if max_tokens:
                    payload["options"]["num_predict"] = max_tokens

                # Make request
                url = self._build_api_url("/api/chat")
                logger.debug(f"Sending request to {url}")

                response = self.client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                response.raise_for_status()
                result = response.json()

                # Extract response text
                assistant_message = result.get("message", {}).get("content", "")

                # Set output message using OpenInference conventions
                span.set_attribute(
                    f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.0.message.role",
                    "assistant"
                )
                span.set_attribute(
                    f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.0.message.content",
                    assistant_message
                )

                # Set output value for Phoenix UI visibility
                span.set_attribute(SpanAttributes.OUTPUT_VALUE, assistant_message)

                # Set token counts if available
                if "prompt_eval_count" in result:
                    span.set_attribute(
                        SpanAttributes.LLM_TOKEN_COUNT_PROMPT,
                        result["prompt_eval_count"]
                    )
                if "eval_count" in result:
                    span.set_attribute(
                        SpanAttributes.LLM_TOKEN_COUNT_COMPLETION,
                        result["eval_count"]
                    )
                    span.set_attribute(
                        SpanAttributes.LLM_TOKEN_COUNT_TOTAL,
                        result.get("prompt_eval_count", 0) + result["eval_count"]
                    )

                span.set_status(Status(StatusCode.OK))
                logger.info(f"LLM response received ({len(assistant_message)} chars)")

                return assistant_message

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error from Ollama: {e}")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
            except Exception as e:
                logger.error(f"Error calling Ollama: {e}")
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def health_check(self) -> bool:
        """Check if Ollama is reachable and model is available"""
        try:
            # Try to list models
            url = self._build_api_url("/api/tags")
            response = self.client.get(url, timeout=5)
            response.raise_for_status()

            models = response.json().get("models", [])
            model_names = [m.get("name") for m in models]

            if self.model in model_names:
                logger.info(f"Ollama health check OK, model '{self.model}' found")
                return True
            else:
                logger.warning(f"Model '{self.model}' not found. Available: {model_names}")
                return False

        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def close(self):
        """Close HTTP client"""
        self.client.close()


# Convenience function
def create_message(role: str, content: str) -> Message:
    """Create a chat message"""
    return Message(role=role, content=content)
