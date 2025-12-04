.PHONY: help install scrape index dev-backend dev-frontend dev clean test health

help:
	@echo "Quantum Wiki RAG - Available Commands"
	@echo "======================================"
	@echo "make install       - Install all dependencies"
	@echo "make scrape        - Scrape Wikipedia corpus (takes ~10-15 min)"
	@echo "make index         - Build ChromaDB vector index"
	@echo "make dev-backend   - Start backend API server"
	@echo "make dev-frontend  - Start frontend dev server"
	@echo "make dev           - Start both backend and frontend (uses tmux)"
	@echo "make health        - Check system health"
	@echo "make clean         - Clean generated files"
	@echo "make test          - Run basic tests"
	@echo ""
	@echo "Quick Start:"
	@echo "  1. make install"
	@echo "  2. Start Ollama: ollama serve"
	@echo "  3. Start Phoenix: phoenix serve (in new terminal)"
	@echo "  4. make scrape"
	@echo "  5. make index"
	@echo "  6. make dev-backend (in new terminal)"
	@echo "  7. make dev-frontend (in new terminal)"

install:
	@echo "Installing Python dependencies..."
	uv sync
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✓ Installation complete!"

scrape:
	@echo "Scraping Wikipedia quantum physics articles..."
	@echo "This will take ~10-15 minutes with default settings"
	uv run python scripts/scrape_wikipedia.py \
		--max-pages 200 \
		--out data/corpus/quantum \
		--delay 2

index:
	@echo "Building ChromaDB vector index..."
	uv run python scripts/build_index.py \
		--corpus-dir data/corpus/quantum \
		--chroma-dir .chroma/quantum_wiki

dev-backend:
	@echo "Starting backend API server..."
	uv run python -m uvicorn app.main:app --reload --port 8000

dev-frontend:
	@echo "Starting frontend dev server..."
	cd frontend && npm run dev

health:
	@echo "Checking system health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "Backend not running"

clean:
	@echo "Cleaning generated files..."
	rm -rf .chroma/
	rm -rf data/corpus/quantum/*
	rm -f conversations.db
	rm -f *.log
	@echo "✓ Cleaned!"

test:
	@echo "Running basic tests..."
	@echo "1. Checking if Ollama is accessible..."
	@curl -s http://localhost:11434/api/tags > /dev/null && echo "✓ Ollama OK" || echo "✗ Ollama not running"
	@echo "2. Checking if backend is running..."
	@curl -s http://localhost:8000/health > /dev/null && echo "✓ Backend OK" || echo "✗ Backend not running"
	@echo "3. Checking if Phoenix is running..."
	@curl -s http://localhost:6006 > /dev/null && echo "✓ Phoenix OK" || echo "✗ Phoenix not running"
	@echo "4. Checking ChromaDB index..."
	@test -d .chroma/quantum_wiki && echo "✓ ChromaDB index exists" || echo "✗ ChromaDB index not found"

# Quick setup for first time users
first-time-setup: install
	@echo ""
	@echo "First-time setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Ensure Ollama is running: ollama serve"
	@echo "2. Pull the model: ollama pull gpt-oss:20b"
	@echo "3. Start Phoenix: phoenix serve (in new terminal)"
	@echo "4. Run: make scrape"
	@echo "5. Run: make index"
	@echo "6. Run: make dev-backend (in new terminal)"
	@echo "7. Run: make dev-frontend (in new terminal)"
