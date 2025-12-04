# Contributing Guide

Thank you for your interest in contributing to the Quantum Wiki RAG demo project!

## Development Setup

1. Fork and clone the repository
2. Follow the setup instructions in `SETUP_GUIDE.md`
3. Create a new branch for your feature: `git checkout -b feature/your-feature-name`

## Code Style

### Python

- Follow PEP 8
- Use type hints where appropriate
- Add docstrings for public functions and classes
- Keep functions focused and under 50 lines when possible

```python
def example_function(param: str, optional: int = 10) -> dict:
    """
    Brief description of what this function does.

    Args:
        param: Description of param
        optional: Description of optional parameter

    Returns:
        Description of return value
    """
    # Implementation
    pass
```

### JavaScript/React

- Use functional components with hooks
- Keep components under 200 lines
- Use meaningful variable names
- Add comments for complex logic

## Project Structure

```
app/
├── agents/     # Agent implementations (router, generator, reviewer, formatter)
├── api/        # FastAPI endpoints and request/response schemas
├── database/   # Conversation storage
├── llm/        # LLM client wrappers
├── rag/        # RAG retrieval logic
└── main.py     # Application entry point

scripts/
├── scrape_wikipedia.py  # Corpus scraper
└── build_index.py       # Index builder

frontend/
└── src/
    ├── App.jsx          # Main application component
    └── App.css          # Styling
```

## Adding New Features

### Adding a New Agent

1. Create a new file in `app/agents/`
2. Implement the agent class with Phoenix tracing:

```python
from opentelemetry import trace

class NewAgent:
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)

    def process(self, input_data):
        with self.tracer.start_as_current_span("agent.new_agent") as span:
            span.set_attribute("agent.role", "new_agent")
            # Implementation
            pass
```

3. Wire into orchestrator in `app/api/orchestrator.py`
4. Update tests

### Adding New RAG Features

1. Modify retriever in `app/rag/retriever.py`
2. Ensure proper Phoenix instrumentation
3. Update chunking strategy if needed in `scripts/build_index.py`

### Adding New Frontend Features

1. Update `frontend/src/App.jsx`
2. Add corresponding styles in `App.css`
3. Update API schemas if new endpoints are needed

## Testing

Currently, the project focuses on manual testing:

1. Start all services
2. Run through usage scenarios
3. Verify traces in Phoenix
4. Check for errors in logs

**Future**: We plan to add automated tests. Contributions welcome!

## Documentation

When adding features:

1. Update README.md with new configuration options
2. Add examples to SETUP_GUIDE.md if setup changes
3. Update code comments
4. Add docstrings for new functions

## Submitting Changes

1. Ensure your code works locally
2. Test with Phoenix to ensure traces are correct
3. Commit with clear, descriptive messages:
   ```
   feat: Add multi-language support for embeddings

   - Add language detection to retriever
   - Update chunking to respect sentence boundaries
   - Add configuration for language models
   ```
4. Push to your fork
5. Create a Pull Request with:
   - Clear description of changes
   - Screenshots if UI changes
   - Link to any related issues

## Commit Message Convention

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the technical merits
- Help others learn

## Ideas for Contributions

Here are some areas that need work:

### High Priority
- [ ] Add automated tests (pytest for backend, Jest for frontend)
- [ ] Implement Phoenix evaluations
- [ ] Add conversation export feature
- [ ] Improve error handling and user feedback

### Medium Priority
- [ ] Support for different embedding models
- [ ] Advanced chunking strategies (semantic chunking)
- [ ] Batch evaluation pipeline
- [ ] A/B testing framework for prompts

### Low Priority
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Multiple LLM provider support
- [ ] User authentication

## Getting Help

- Read the documentation first (README.md, SETUP_GUIDE.md)
- Check existing issues and PRs
- Ask questions in issue discussions
- Join community discussions (if available)

## License

By contributing, you agree that your contributions will be licensed under the same terms as the project.

---

Thank you for contributing! 🎉
