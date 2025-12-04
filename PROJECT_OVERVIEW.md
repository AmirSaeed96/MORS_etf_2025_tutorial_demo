# Project Overview: Quantum Wiki RAG with Phoenix

## Executive Summary

This project implements a complete Phoenix-instrumented agentic RAG system for quantum physics question answering. It demonstrates LLM observability best practices through a multi-agent architecture with probabilistic routing, accuracy review, and comprehensive tracing.

## Key Achievements

✅ **Complete Agentic Workflow**
- Router agent with probabilistic (coin-flip) decision making
- RAG retrieval with ChromaDB
- Answer generation (with/without context)
- Accuracy review for hallucination detection
- Response formatting with TL;DR generation

✅ **Full Phoenix Instrumentation**
- OpenTelemetry spans for all agent steps
- Automatic LLM call tracing
- RAG retrieval tracking with document metadata
- Session-based trace filtering
- Comprehensive span attributes for debugging

✅ **Production-Ready Components**
- Wikipedia scraper with robots.txt compliance
- Vector indexing with sentence-transformers embeddings
- Persistent ChromaDB storage
- Multi-turn conversation support with SQLite
- FastAPI backend with health checks
- Modern React frontend with real-time updates

✅ **Developer Experience**
- Comprehensive documentation (README, SETUP_GUIDE, CONTRIBUTING)
- Makefile for common tasks
- Environment-based configuration
- Clear project structure
- Detailed code comments and docstrings

## Technical Architecture

### Data Flow

```
1. User Query → Frontend (React)
2. Frontend → FastAPI Backend (/chat endpoint)
3. Backend → Chat Orchestrator
4. Orchestrator → Router Agent (decides RAG vs no-RAG)
5a. If RAG: Orchestrator → Retriever → ChromaDB
5b. If no-RAG: Skip retrieval
6. Orchestrator → Answer Generator → Ollama LLM
7. Orchestrator → Accuracy Reviewer → Ollama LLM
8. Orchestrator → Formatter → Ollama LLM (for TL;DR)
9. Backend → Frontend (formatted response with metadata)
10. All steps → Phoenix (OTEL traces)
```

### Technology Stack

**Backend:**
- Python 3.10+ with uv package management
- FastAPI for REST API
- SQLAlchemy for conversation storage
- ChromaDB for vector storage
- Sentence-Transformers for embeddings
- Ollama client for LLM calls
- Phoenix OTEL for instrumentation

**Frontend:**
- React 18
- Vite for dev server and bundling
- React Markdown for response rendering
- Modern CSS with dark theme

**Infrastructure:**
- Ollama for local LLM (gpt-oss:20b)
- Phoenix server for observability
- SQLite for chat history
- ChromaDB for vector search

## Component Details

### 1. Wikipedia Scraper (`scripts/scrape_wikipedia.py`)

**Features:**
- Robots.txt compliance using `urllib.robotparser`
- Polite rate limiting (2s delay between requests)
- BFS crawl with keyword filtering
- HTML parsing with BeautifulSoup
- Clean text extraction (removes nav, tables, etc.)
- Configurable max pages and output directory

**Seed URLs:** 37 quantum physics articles (expandable)

**Output:** JSON files per article with title, URL, content, links

### 2. Corpus Indexer (`scripts/build_index.py`)

**Features:**
- Text chunking with overlap (800 char chunks, 100 char overlap)
- Sentence-based splitting (preserves context)
- Embedding generation with HuggingFace models
- Batch processing for efficiency
- ChromaDB persistent storage
- Verification with test query

**Embeddings:** sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)

### 3. LLM Client (`app/llm/ollama_client.py`)

**Features:**
- Ollama API integration
- Phoenix tracing for all LLM calls
- Retry logic with exponential backoff
- Token counting (when available)
- Configurable temperature and max_tokens
- Health check endpoint

**Traced Attributes:**
- Model name, temperature, message count
- Input/output previews (first 200 chars)
- Token counts (input/output)
- Latency

### 4. RAG Retriever (`app/rag/retriever.py`)

**Features:**
- Query embedding generation
- ChromaDB similarity search
- Top-K retrieval (default: 5)
- Context formatting for LLM
- Phoenix instrumentation

**Traced Attributes:**
- Query text, top_k, collection name
- Number of results, document titles
- Distances/similarities

### 5. Router Agent (`app/agents/router.py`)

**Features:**
- Probabilistic routing (50% RAG by default)
- Override capability for deterministic behavior
- Phoenix tracing with routing decision

**Traced Attributes:**
- Query preview, routing path
- Override flag, probability

### 6. Answer Generator (`app/agents/answer_generator.py`)

**Features:**
- Dual mode: RAG-based and knowledge-based
- Context-aware prompting
- Conversation history integration
- Lower temperature for RAG (0.3 vs 0.7)

**Traced Attributes:**
- Route, has_context flag
- Answer length

### 7. Accuracy Reviewer (`app/agents/reviewer.py`)

**Features:**
- Context-based verification (when RAG used)
- General correctness check (when no RAG)
- Structured verdict with JSON parsing
- Confidence scoring
- Hallucination detection

**Output:**
- Label: good / needs_revision / bad
- Rationale, suggestions, confidence

### 8. Formatter (`app/agents/formatter.py`)

**Features:**
- Markdown formatting
- TL;DR generation
- Source citation (with Wikipedia links)
- Review warning inclusion
- Metadata assembly

### 9. Chat Orchestrator (`app/api/orchestrator.py`)

**Features:**
- Coordinates all agents in sequence
- Manages conversation history
- Stores messages in database
- Phoenix tracing for full workflow

**Traced Attributes:**
- Session ID, user message
- Route path, used_rag flag
- Review label

### 10. FastAPI Backend (`app/main.py`)

**Endpoints:**
- `POST /chat` - Main chat interaction
- `GET /health` - System health check
- `GET /conversations` - List all conversations
- `GET /conversations/{id}` - Get conversation history

**Features:**
- Phoenix OTEL registration on startup
- Graceful degradation if Phoenix unavailable
- CORS configuration
- Trace ID injection in responses

### 11. React Frontend (`frontend/src/App.jsx`)

**Features:**
- Real-time chat interface
- Routing mode controls (auto/always/never RAG)
- Message badges (RAG status, review, trace ID)
- Markdown rendering for responses
- Conversation persistence
- Health indicator
- Phoenix UI link

## File Statistics

**Python Files:** 15+
**Lines of Code (estimate):** ~3,500
**React Components:** 1 main component
**Configuration Files:** 5 (pyproject.toml, .env, package.json, etc.)
**Documentation Files:** 5 (README, SETUP_GUIDE, CONTRIBUTING, etc.)

## Phoenix Observability Features

### Span Hierarchy Example

```
chat.process_message (root)
├── agent.router
├── rag.retrieve (if RAG path)
│   └── [embedding generation]
├── agent.answer_generator
│   └── llm.generate_with_rag (or llm.generate_without_rag)
├── agent.reviewer
│   └── llm.review_with_context (or llm.review_without_context)
└── agent.formatter
    └── llm.generate_tldr
```

### Key Attributes Captured

**Session Level:**
- `session.id` - Conversation ID for filtering

**LLM Calls:**
- `llm.vendor`, `llm.model`, `llm.temperature`
- `llm.input_preview`, `llm.output_preview`
- `llm.input_tokens`, `llm.output_tokens`

**RAG:**
- `rag.query`, `rag.top_k`, `rag.num_results`
- `rag.top_titles` - Document titles retrieved

**Agents:**
- `agent.role` - router, answer_generator, reviewer, formatter
- `router.path` - rag or no_rag
- `review.label` - good, needs_revision, bad

## Demo Scenarios

### 1. RAG Quality Comparison

Compare responses with and without RAG for the same query.

**Query:** "What is the Pauli exclusion principle?"

**Expected:**
- RAG response: Cites Wikipedia sources, accurate
- No-RAG response: General knowledge, may lack specific details

**Phoenix View:**
- Compare retrieved documents
- Compare LLM prompts
- Compare review verdicts

### 2. Hallucination Detection

Ask about a non-existent concept.

**Query:** "Explain the Heisenberg stability theorem"

**Expected:**
- Reviewer detects lack of support
- Response includes warning
- Phoenix shows reviewer reasoning

### 3. Multi-Turn Reasoning

Build on previous context.

**Queries:**
1. "What is quantum entanglement?"
2. "How does Bell's theorem relate to that?"
3. "What experiments have tested this?"

**Expected:**
- Context carries through conversation
- Phoenix shows full conversation trace
- Answers build on each other

## Performance Characteristics

**Scraping:** ~10-15 minutes for 200 pages
**Indexing:** ~3-5 minutes for 200 documents
**Query Latency:**
- Router: <100ms
- Retrieval: 100-300ms
- LLM calls: 5-20 seconds each (depends on model speed)
- Total: 15-60 seconds per query

**Storage:**
- Corpus: ~50MB for 200 pages
- ChromaDB: ~100MB with embeddings
- Conversations: <1MB (SQLite)

## Future Enhancements

**High Priority:**
1. Automated testing (pytest, Jest)
2. Phoenix evaluations integration
3. Prompt versioning and A/B testing
4. Conversation export/import

**Medium Priority:**
5. Support for multiple embedding models
6. Semantic chunking (vs fixed-size)
7. Batch evaluation pipeline
8. Response caching

**Low Priority:**
9. Docker containerization
10. Multi-user support with auth
11. Cloud LLM provider support
12. Advanced RAG techniques (HyDE, reranking)

## Success Metrics

This project successfully demonstrates:

✅ **Observability:** Every step traced in Phoenix with rich metadata
✅ **Modularity:** Clear separation of concerns (agents, API, storage)
✅ **Extensibility:** Easy to add new agents or modify prompts
✅ **Usability:** Simple setup with comprehensive documentation
✅ **Educational Value:** Perfect for tutorials on LLM observability

## Conclusion

The Quantum Wiki RAG project provides a complete, production-quality example of an observable agentic RAG system. It balances sophistication (multi-agent workflow, accuracy review) with simplicity (clear code structure, good documentation), making it ideal for demonstrations, tutorials, and as a starting point for more advanced systems.

The Phoenix instrumentation is comprehensive without being intrusive, showing how observability can be integrated seamlessly into LLM applications from day one.

---

**Project Status:** ✅ Complete and ready for demo/tutorial use

**Repository:** Local (ready for git initialization and remote push)

**Maintainer:** Demo project for Phoenix observability tutorials
