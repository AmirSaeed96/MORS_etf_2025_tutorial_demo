# Complete Setup Guide

This guide walks you through setting up the Quantum Wiki RAG demo system step-by-step.

## Prerequisites Checklist

Before starting, verify you have:

- [ ] Python 3.10 or higher (`python --version`)
- [ ] Node.js 18 or higher (`node --version`)
- [ ] uv package manager installed
- [ ] Ollama installed
- [ ] At least 10GB free disk space
- [ ] Stable internet connection (for scraping Wikipedia)

## Step-by-Step Setup

### Step 1: Install uv (if not installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

### Step 2: Install and Configure Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve &

# Pull the model (this is large, ~11GB)
ollama pull gpt-oss:20b

# Verify model is available
ollama list
# Should show gpt-oss:20b in the list
```

**Note**: The model download may take 15-30 minutes depending on your connection.

### Step 3: Project Setup

```bash
# Navigate to project directory
cd /path/to/MORS_tutorial_demo

# Create .env file
cp .env.example .env

# Install Python dependencies
uv sync

# This creates a virtual environment and installs all packages
# Takes ~5 minutes
```

### Step 4: Install Phoenix

Phoenix should be installed via `uv sync`, but verify:

```bash
# Check Phoenix is installed
uv pip list | grep phoenix

# Should show:
# arize-phoenix            4.x.x
# arize-phoenix-otel       0.x.x
```

### Step 5: Start Phoenix Server

Open a new terminal window/tab:

```bash
# Start Phoenix
phoenix serve

# You should see:
# 🚀 Phoenix is running at http://localhost:6006
```

**Important**: Keep this terminal open. Phoenix needs to run continuously.

Visit http://localhost:6006 to verify the Phoenix UI loads.

### Step 6: Scrape Wikipedia Corpus

This is the longest step (10-20 minutes).

```bash
# In the main terminal (not Phoenix terminal)
uv run python scripts/scrape_wikipedia.py \
    --max-pages 200 \
    --out data/corpus/quantum \
    --delay 2

# You'll see logs like:
# INFO - Loading robots.txt from Wikipedia...
# INFO - Starting crawl with 37 seed URLs
# INFO - Scraping: https://en.wikipedia.org/wiki/Quantum_mechanics
# INFO - Progress: 1/200 pages
# ...
```

**Expected Duration**:
- 200 pages with 2-second delay = ~400 seconds (~7 minutes)
- Plus processing time = 10-15 minutes total

**If it fails**:
- Check your internet connection
- Ensure Wikipedia is accessible
- Try reducing `--max-pages` to 50 for a faster test

### Step 7: Build Vector Index

```bash
# Build ChromaDB index with embeddings
uv run python scripts/build_index.py \
    --corpus-dir data/corpus/quantum \
    --chroma-dir .chroma/quantum_wiki \
    --embedding-model sentence-transformers/all-MiniLM-L6-v2

# You'll see:
# INFO - Loading embedding model...
# INFO - Initializing ChromaDB...
# INFO - Created 1523 chunks from 200 documents
# INFO - Processing batch 1/16
# ...
# INFO - Successfully indexed 1523 chunks
# INFO - Collection now contains 1523 documents
```

**Expected Duration**: 3-5 minutes

The embedding model will be downloaded on first run (~100MB).

### Step 8: Start Backend API

Open a new terminal window/tab:

```bash
cd /path/to/MORS_tutorial_demo

# Start FastAPI backend
uv run python -m uvicorn app.main:app --reload --port 8000

# You should see:
# INFO - Starting Quantum Wiki RAG application...
# INFO - Registering Phoenix OTEL instrumentation...
# INFO - Phoenix tracing enabled: http://localhost:6006
# INFO - Initializing LLM client...
# INFO - Initializing retriever...
# INFO - Application startup complete!
# INFO - Uvicorn running on http://0.0.0.0:8000
```

**Important**: Keep this terminal open.

**Test the API**:

```bash
# In another terminal
curl http://localhost:8000/health

# Should return:
# {
#   "status": "healthy",
#   "ollama": true,
#   "chromadb": true,
#   "phoenix": true,
#   "message": "All systems operational"
# }
```

### Step 9: Start Frontend

Open a new terminal window/tab:

```bash
cd /path/to/MORS_tutorial_demo/frontend

# Install frontend dependencies (first time only)
npm install

# Start dev server
npm run dev

# You should see:
# VITE v5.x.x ready in xxx ms
# ➜ Local:   http://localhost:3000/
```

**Important**: Keep this terminal open.

### Step 10: Verify Everything Works

You should now have 4 terminals running:

1. **Phoenix**: http://localhost:6006
2. **Backend API**: http://localhost:8000
3. **Frontend**: http://localhost:3000
4. **Ollama**: (may be background service)

**Final Test**:

1. Open browser to http://localhost:3000
2. Type: "What is quantum entanglement?"
3. Click Send
4. Wait for response (~10-30 seconds depending on your machine)
5. You should see:
   - A formatted answer with sources
   - TL;DR at the bottom
   - Badges showing "RAG: Used" (or "Not Used")
   - Review label
6. Open Phoenix UI (http://localhost:6006)
7. Navigate to "Traces"
8. You should see your chat request trace
9. Click on it to explore the spans

## Terminal Summary

Keep these running:

```bash
# Terminal 1: Phoenix
phoenix serve

# Terminal 2: Backend
uv run python -m uvicorn app.main:app --reload --port 8000

# Terminal 3: Frontend
cd frontend && npm run dev

# Terminal 4: Ollama (if not background service)
ollama serve
```

## Common Issues

### Issue: "Module not found" errors

**Solution**:
```bash
# Re-sync dependencies
uv sync
```

### Issue: Ollama connection refused

**Solution**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Issue: ChromaDB not found

**Solution**:
```bash
# Make sure you ran the indexing step
ls .chroma/quantum_wiki/

# If empty, re-run build_index.py
uv run python scripts/build_index.py --corpus-dir data/corpus/quantum
```

### Issue: Phoenix not receiving traces

**Solution**:
1. Check Phoenix is running: `curl http://localhost:6006/healthz`
2. Restart the backend
3. Check `.env` has correct `PHOENIX_COLLECTOR_ENDPOINT`

### Issue: Frontend can't connect to backend

**Solution**:
1. Verify backend is running on port 8000
2. Check browser console for CORS errors
3. Verify `.env` has `CORS_ORIGINS=http://localhost:3000`

## Development Tips

### Stopping Services

```bash
# Stop Phoenix: Ctrl+C in Phoenix terminal
# Stop Backend: Ctrl+C in backend terminal
# Stop Frontend: Ctrl+C in frontend terminal
# Stop Ollama: killall ollama (or keep running)
```

### Rebuilding Corpus

If you want to rescrape:

```bash
# Delete old corpus
rm -rf data/corpus/quantum/*

# Rescrape
uv run python scripts/scrape_wikipedia.py --max-pages 200 --out data/corpus/quantum

# Rebuild index
uv run python scripts/build_index.py --corpus-dir data/corpus/quantum
```

### Viewing Logs

All services log to stdout. For persistent logs:

```bash
# Backend with log file
uv run python -m uvicorn app.main:app --reload --port 8000 2>&1 | tee backend.log

# Phoenix with log file
phoenix serve 2>&1 | tee phoenix.log
```

## Next Steps

Once everything is running:

1. Read the main README.md for usage examples
2. Try different queries
3. Experiment with routing modes
4. Explore traces in Phoenix
5. Modify prompts in the agent code
6. Add custom Wikipedia seed URLs in `scripts/quantum_seeds.py`

## Getting Help

If you encounter issues:

1. Check all services are running (4 terminals)
2. Verify health endpoint: `curl http://localhost:8000/health`
3. Check Phoenix UI loads: http://localhost:6006
4. Review error logs in each terminal
5. Consult troubleshooting section in README.md

---

**Setup Complete!** 🎉

You're ready to explore quantum physics with RAG and Phoenix observability!
