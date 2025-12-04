# Quantum Wiki RAG with Phoenix Observability

**Codename:** quantum-phoenix
**Version:** 1.0.0

A Phoenix-instrumented, agentic RAG system that demonstrates LLM observability using quantum physics Wikipedia articles. This project showcases a multi-agent workflow with router-based decision making, RAG retrieval, accuracy review, and response formatting — all traced with Arize Phoenix.

## 🌟 Features

- **Agentic RAG Architecture**: Multi-agent workflow with router, answer generator, reviewer, and formatter
- **Probabilistic Routing**: Coin-flip router that randomly decides between RAG and non-RAG paths
- **Phoenix Observability**: Full OpenTelemetry instrumentation showing every agent step
- **Wikipedia Corpus**: Polite HTML scraping of quantum physics articles (respects robots.txt)
- **ChromaDB Vector Store**: Local persistent vector database for document retrieval
- **Chat History**: Multi-turn conversation support with SQLite storage
- **Web UI**: Clean React interface with routing controls and trace visibility
- **Local LLM**: Uses Ollama with gpt-oss:20b model

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+**
- **Node.js 18+** and npm/yarn
- **uv** (for Python package management): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Ollama**: Download from [ollama.ai](https://ollama.ai)
- **Git** (optional, for cloning)

## 🚀 Quick Start

### 1. Install Ollama and Pull Model

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the gpt-oss:20b model
ollama pull gpt-oss:20b

# Start Ollama server (if not already running)
ollama serve
```

### 2. Clone Repository and Setup Environment

```bash
# Navigate to project directory
cd MORS_tutorial_demo

# Copy environment variables
cp .env.example .env

# Edit .env if you need to customize settings
# (defaults should work for most setups)
```

### 3. Install Python Dependencies

```bash
# Sync dependencies using uv
uv sync
```

### 4. Install Phoenix

```bash
# Phoenix is included in dependencies, but verify:
uv pip install arize-phoenix arize-phoenix-otel
```

### 5. Start Phoenix Server

In a new terminal:

```bash
source .venv/bin/activate
phoenix serve

# Phoenix UI will be available at http://localhost:6006
```

Keep this terminal running.

### 6. Scrape Wikipedia Corpus

This is a one-time setup to build your quantum physics corpus:

```bash
# Run the scraper (will take ~10-15 minutes for 200 pages with 2s delay)
uv run python scripts/scrape_wikipedia.py --max-pages 200 --out data/corpus/quantum

# You should see progress logs as pages are scraped
```

**Note**: The scraper respects Wikipedia's robots.txt and implements polite rate limiting (2 seconds between requests by default).

### 7. Build ChromaDB Index

After scraping, build the vector index:

```bash
# Build index with embeddings
uv run python scripts/build_index.py \
    --corpus-dir data/corpus/quantum \
    --chroma-dir .chroma/quantum_wiki

# This will:
# - Load scraped documents
# - Chunk them into ~800 character segments
# - Generate embeddings using sentence-transformers
# - Store in ChromaDB
```

### 8. Start the Backend API

In a new terminal:

```bash
# Start FastAPI backend
uv run python -m uvicorn app.main:app --reload --port 8000

# API will be available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

Keep this terminal running.

### 9. Start the Frontend

In a new terminal:

```bash
cd frontend

# Install frontend dependencies
npm install

# Start Vite dev server
npm run dev

# Frontend will be available at http://localhost:3000
```

### 10. Use the Application

1. **Open the web UI**: Navigate to http://localhost:3000
2. **Ask a quantum physics question**: Try "What is quantum entanglement?"
3. **View traces in Phoenix**: Open http://localhost:6006 to see the agent workflow traces

## 🏗️ Architecture

### Agent Workflow

```
User Query
    ↓
Router Agent (coin flip)
    ↓
┌───────────────┴────────────────┐
│                                │
RAG Path                    No-RAG Path
    ↓                            ↓
Retrieve from ChromaDB          Skip Retrieval
    ↓                            ↓
└───────────────┬────────────────┘
                ↓
    Answer Generator Agent
                ↓
    Accuracy Reviewer Agent
                ↓
    Formatter Agent (+ TL;DR)
                ↓
    Final Response
```

### Components

1. **Router Agent**: Randomly decides (50% probability) whether to use RAG
2. **RAG Retriever**: Queries ChromaDB for relevant quantum physics articles
3. **Answer Generator**: Creates draft response (with or without context)
4. **Accuracy Reviewer**: Checks for hallucinations and correctness
5. **Formatter**: Adds TL;DR, sources, and formatting

### Phoenix Instrumentation

All components are instrumented with OpenTelemetry spans:

- `chat.process_message` - Overall chat request
- `agent.router` - Routing decision
- `rag.retrieve` - Vector search
- `agent.answer_generator` - Answer generation
- `llm.generate_with_rag` / `llm.generate_without_rag` - LLM calls
- `agent.reviewer` - Accuracy review
- `agent.formatter` - Response formatting

## 📁 Project Structure

```
.
├── app/
│   ├── agents/          # Agent implementations
│   │   ├── router.py
│   │   ├── answer_generator.py
│   │   ├── reviewer.py
│   │   └── formatter.py
│   ├── api/             # FastAPI endpoints and orchestration
│   │   ├── orchestrator.py
│   │   └── schemas.py
│   ├── database/        # Conversation storage
│   ├── llm/            # Ollama client
│   ├── rag/            # ChromaDB retriever
│   ├── config.py       # Configuration management
│   └── main.py         # FastAPI application
├── scripts/
│   ├── scrape_wikipedia.py    # Wikipedia scraper
│   ├── build_index.py         # Index builder
│   └── quantum_seeds.py       # Seed URLs
├── frontend/           # React web UI
│   ├── src/
│   │   ├── App.jsx
│   │   └── App.css
│   └── package.json
├── data/
│   ├── raw/           # Raw scraped data
│   └── corpus/        # Processed corpus
├── .chroma/           # ChromaDB storage
├── pyproject.toml     # Python dependencies (uv)
├── .env.example       # Environment template
└── README.md
```

## 🎯 Usage Examples

### Basic Chat

```bash
# Using the web UI
1. Open http://localhost:3000
2. Type: "Explain the uncertainty principle"
3. Press Send
4. View response with RAG sources (if used)
```

### Controlling Routing

In the web UI, use the "Routing Mode" dropdown:

- **Auto (Coin Flip)**: 50% chance of using RAG
- **Always RAG**: Forces RAG retrieval for every query
- **Never RAG**: Uses only model knowledge (no retrieval)

### Viewing Traces in Phoenix

1. Open http://localhost:6006
2. Navigate to "Traces" tab
3. Filter by project: `quantum-wiki-rag`
4. Click on a trace to see:
   - Router decision and path taken
   - Retrieved documents (if RAG was used)
   - LLM calls and token counts
   - Review verdict
   - Overall latency breakdown

### API Usage

You can also interact directly with the API:

```bash
# Health check
curl http://localhost:8000/health

# Send a chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test-123",
    "message": "What is a qubit?",
    "override_routing": "auto"
  }'
```

## 🧪 Demo Scenarios

### Scenario 1: RAG vs No-RAG Comparison

1. Set routing to "Always RAG"
2. Ask: "What is the Pauli exclusion principle?"
3. Note the Wikipedia sources cited
4. Start new conversation
5. Set routing to "Never RAG"
6. Ask the same question
7. Compare responses and trace differences in Phoenix

### Scenario 2: Hallucination Detection

1. Ask a question that mixes real and fake concepts:
   "How does quantum superposition relate to the Heisenberg stability theorem?"
   (Note: "Heisenberg stability theorem" is not a real concept)
2. Check the reviewer's verdict in the response metadata
3. View the review span in Phoenix to see the reasoning

### Scenario 3: Multi-Turn Conversation

1. Ask: "What is quantum entanglement?"
2. Follow up: "Can you explain Bell's theorem in that context?"
3. Follow up: "What experiments verify this?"
4. View the conversation trace in Phoenix showing history context

## ⚙️ Configuration

Key environment variables in `.env`:

```bash
# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gpt-oss:20b

# Phoenix
PHOENIX_PROJECT_NAME=quantum-wiki-rag
PHOENIX_ENDPOINT=http://localhost:6006

# RAG
RAG_CHUNK_SIZE=800
RAG_CHUNK_OVERLAP=100
RAG_TOP_K=5

# Scraper
SCRAPER_MAX_PAGES=200
SCRAPER_DELAY_SECONDS=2
```

## 🔧 Troubleshooting

### Ollama Connection Error

```
Error: Connection refused to localhost:11434
```

**Solution**: Ensure Ollama is running:

```bash
ollama serve
```

### ChromaDB Not Found

```
Error: ChromaDB directory not found
```

**Solution**: Run the indexing script:

```bash
uv run python scripts/build_index.py --corpus-dir data/corpus/quantum
```

### Phoenix Not Receiving Traces

**Solution**:

1. Verify Phoenix is running: `curl http://localhost:6006/healthz`
2. Check environment variable: `PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006/v1/traces`
3. Restart the backend

### Frontend CORS Error

**Solution**: Ensure backend is running on port 8000 and CORS origins in `.env` include `http://localhost:3000`

## 📊 Phoenix Observability Features

### What You Can See in Phoenix

1. **Trace Timeline**: Visual timeline of all agent steps
2. **Span Details**: Input/output for each LLM call and tool use
3. **Latency Analysis**: Identify slow components
4. **RAG Quality**: Which documents were retrieved and used
5. **Error Tracking**: Failed steps and exceptions
6. **Token Counts**: Monitor LLM usage

### Filtering Traces

- By session ID (conversation_id)
- By routing path (rag vs no_rag)
- By review label (good, needs_revision, bad)
- By time range

## 🎓 Tutorial Talking Points

When using this for a demo/tutorial:

1. **Architecture Overview**: Show the agent graph and explain non-deterministic routing
2. **Corpus Building**: Walk through scraping and indexing process
3. **Live Demo**: Ask questions and show real-time traces in Phoenix
4. **RAG Quality**: Compare RAG vs non-RAG responses
5. **Debugging**: Show how to identify issues using traces (e.g., wrong retrieval, hallucinations)
6. **Metrics**: Discuss potential eval metrics based on reviewer output

## 🔒 Security & Ethics

- **Robots.txt Compliance**: Scraper respects Wikipedia's robots.txt
- **Rate Limiting**: 2-second delay between requests (polite scraping)
- **Local Processing**: All data stays on your machine
- **Educational Use**: This is a demo system, not production-ready

## 📝 License

This project is for educational and demonstration purposes.

## 🙏 Acknowledgments

- **Wikipedia**: Corpus source (following their usage guidelines)
- **Arize Phoenix**: Observability platform
- **Ollama**: Local LLM runtime
- **ChromaDB**: Vector database

## 🐛 Known Limitations

- Corpus limited to ~200 pages (can be expanded)
- Local LLM (gpt-oss:20b) may be slower than cloud APIs
- Simple chunking strategy (could use more sophisticated methods)
- No advanced evaluation metrics (just basic review)
- SQLite for conversations (not suitable for high concurrency)

## 🚀 Future Enhancements

- [ ] Phoenix evaluations integration
- [ ] Prompt management via Phoenix
- [ ] Advanced chunking strategies
- [ ] Support for multiple LLM providers
- [ ] Batch evaluation pipelines
- [ ] User feedback collection
- [ ] A/B testing different prompts

---

**Happy Hacking!** 🎉

For questions or issues, please refer to the Phoenix documentation: https://docs.arize.com/phoenix
