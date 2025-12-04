"""
Main FastAPI application with Phoenix instrumentation.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace

# Phoenix imports
try:
    from phoenix.otel import register
    PHOENIX_AVAILABLE = True
except ImportError:
    PHOENIX_AVAILABLE = False
    logging.warning("Phoenix not available - tracing disabled")

from app.config import settings
from app.llm.ollama_client import OllamaClient
from app.rag.retriever import QuantumWikiRetriever
from app.database.conversation_store import ConversationStore
from app.api.orchestrator import ChatOrchestrator
from app.api.schemas import ChatRequest, ChatResponse, HealthStatus, MessageMetadata, AssistantMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
llm_client: OllamaClient = None
retriever: QuantumWikiRetriever = None
conversation_store: ConversationStore = None
orchestrator: ChatOrchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global llm_client, retriever, conversation_store, orchestrator

    logger.info("Starting Quantum Wiki RAG application...")

    # Initialize Phoenix tracing
    if PHOENIX_AVAILABLE:
        try:
            logger.info("Registering Phoenix OTEL instrumentation...")
            tracer_provider = register(
                project_name=settings.phoenix_project_name,
                endpoint=settings.phoenix_collector_endpoint,
            )
            logger.info(f"Phoenix tracing enabled: {settings.phoenix_endpoint}")
        except Exception as e:
            logger.error(f"Failed to register Phoenix: {e}")
    else:
        logger.warning("Phoenix tracing disabled (not installed)")

    # Initialize components
    try:
        logger.info("Initializing LLM client...")
        llm_client = OllamaClient()

        logger.info("Initializing retriever...")
        retriever = QuantumWikiRetriever()

        logger.info("Initializing conversation store...")
        conversation_store = ConversationStore()

        logger.info("Initializing orchestrator...")
        orchestrator = ChatOrchestrator(
            llm_client=llm_client,
            retriever=retriever,
            conversation_store=conversation_store
        )

        logger.info("Application startup complete!")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")
    if llm_client:
        llm_client.close()


# Create FastAPI app
app = FastAPI(
    title="Quantum Wiki RAG",
    description="Phoenix-instrumented quantum physics RAG with agentic workflows",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Quantum Wiki RAG",
        "version": "1.0.0",
        "phoenix_enabled": PHOENIX_AVAILABLE,
        "phoenix_endpoint": settings.phoenix_endpoint if PHOENIX_AVAILABLE else None
    }


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint"""
    try:
        # Check Ollama
        ollama_ok = llm_client.health_check() if llm_client else False

        # Check ChromaDB/Retriever
        chroma_ok = retriever.health_check() if retriever else False

        # Check Phoenix (basic check)
        phoenix_ok = PHOENIX_AVAILABLE

        overall_status = "healthy" if (ollama_ok and chroma_ok) else "degraded"

        return HealthStatus(
            status=overall_status,
            ollama=ollama_ok,
            chromadb=chroma_ok,
            phoenix=phoenix_ok,
            message="All systems operational" if overall_status == "healthy" else "Some systems unavailable"
        )

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthStatus(
            status="unhealthy",
            ollama=False,
            chromadb=False,
            phoenix=False,
            message=str(e)
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint - processes user message through agentic RAG workflow.
    """
    try:
        logger.info(f"Chat request from conversation {request.conversation_id}")

        # Process message through orchestrator
        response = orchestrator.process_message(
            conversation_id=request.conversation_id,
            user_message=request.message,
            override_routing=request.override_routing if request.override_routing != "auto" else None
        )

        # Get current trace ID if available
        trace_id = None
        try:
            current_span = trace.get_current_span()
            if current_span and current_span.get_span_context().is_valid:
                trace_id = format(current_span.get_span_context().trace_id, '032x')
        except Exception:
            pass

        # Build response
        metadata = MessageMetadata(
            used_rag=response["metadata"]["used_rag"],
            review_label=response["metadata"]["review_label"],
            router_path=response["metadata"]["router_path"],
            trace_id=trace_id,
            context_sources=response["metadata"]["context_sources"],
            review_confidence=response["metadata"].get("review_confidence"),
            tldr=response["metadata"].get("tldr")
        )

        assistant_message = AssistantMessage(
            content=response["content"],
            metadata=metadata
        )

        return ChatResponse(
            conversation_id=request.conversation_id,
            message=assistant_message
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.get("/conversations")
async def list_conversations():
    """List all conversation IDs"""
    try:
        conversations = conversation_store.list_conversations()
        return {"conversations": conversations}
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    try:
        history = conversation_store.get_conversation_history(conversation_id)
        return {
            "conversation_id": conversation_id,
            "messages": history
        }
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
