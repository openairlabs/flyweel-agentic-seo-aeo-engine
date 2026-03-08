# AGENTS.md — V2 Brand Content Engine

Guidelines for AI coding agents operating in this repository.

## Project Overview

Multi-model AI content pipeline producing SEO-optimized MDX blog posts.
Entry points: `generate.py` (CLI), `reddit_scraper.py` (community mining).
Python 3.10+, async-first, no framework (plain scripts + modules).

## Project Structure

```
core/                          # Pipeline modules (the main codebase)
├── ai_router.py               # SmartAIRouter — multi-model orchestration
├── generator.py               # ContentGenerator — 8 content styles, 3-part generation
├── research.py                # WebResearcher, CommunityResearcher, classify_keyword_intent()
├── formatter.py               # AstroFormatter, validate_title(), validate_meta_description()
├── gsc_analyzer.py            # GSCAnalyzer, KeywordCategory, ContentRecommendation
├── content_monitor.py         # Refresh triggers (position drops, CTR, staleness)
├── publisher.py               # AstroPublisher — write MDX to astro-site repo
├── repo_extractor.py          # Astro-brand repo context extraction
├── site_extractor.py          # Live site crawl + AI analysis
├── context_builder.py         # IntelligentContextBuilder — dynamic ICP from research
├── content_validator.py       # Post-generation quality assurance
├── schema_generator.py        # JSON-LD schema markup (BlogPosting, FAQPage, etc.)
├── fact_checker.py            # Citation analysis
├── insight_formatter.py       # SERP insight formatting
├── intelligent_benchmark_extractor.py  # Benchmark data extraction
├── context_intelligence.py    # Table validation
└── cli/                       # Interactive CLI (Click + Rich + Questionary)
    ├── app.py                 # Main Click commands
    ├── prompts.py             # Interactive prompts
    ├── output.py              # Rich panels and tables
    ├── progress.py            # Progress tracking
    └── live_display.py        # Live status display

config/                        # JSON configuration (committed, not gitignored)
├── brand_voice_config.json    # Tone, banned words, style rules
├── icp_config.json            # Ideal Customer Profile
├── seo_optimization.json      # Title/meta limits, banned words, CTR targets
├── products.json              # Brand product registry
├── content-templates.json     # Style templates
├── customer-language.json     # Customer voice patterns
├── competitors.json           # Competitor data
├── research_config.json       # Research quality thresholds
└── author_profiles.json       # E-E-A-T author data

tests/                         # Pytest suite (unit + integration)
output/generations/            # Generated MDX outputs (gitignored)
```

## Build, Test, and Development Commands

```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run generator
python generate.py -k "your keyword"             # Interactive mode (default)
python generate.py --no-int -k "your keyword"     # Non-interactive CLI mode
python generate.py -k "keyword" --nr              # Skip Reddit/Quora research
python generate.py -k "keyword" --publish         # Auto-publish to astro-site

# Run all tests
pytest

# Run a single test file
pytest tests/test_formatter.py -v

# Run a single test by name
pytest tests/test_formatter.py::TestAstroFormatter::test_basic_formatting -v

# Run a single test by keyword match
pytest -k "test_basic_formatting" -v

# Run by marker
pytest -m unit -v                    # Fast unit tests (no API keys needed)
pytest -m integration -v             # Integration tests (requires API keys)
pytest -m "not slow" -v              # Skip slow tests

# Coverage
pytest --cov=core --cov-report=html  # Requires pytest-cov

# Quick import validation
python -c "from core.generator import ContentGenerator; print('OK')"
```

Test markers defined in `pytest.ini`: `unit`, `integration`, `slow`, `research`, `generation`.
Async tests use `@pytest.mark.asyncio` with `asyncio_mode = auto`.

## Code Style and Conventions

### General

- Python 3.10+. 4-space indentation. No configured formatter or linter.
- Match the existing style in `core/*.py` — no need to reformat existing code.
- `flake8`, `black`, `isort` are mentioned in CLAUDE.md but NOT enforced or configured.

### Naming

- Functions and variables: `snake_case`
- Classes: `CapWords` (`SmartAIRouter`, `ContentGenerator`, `AstroFormatter`)
- Constants: `UPPER_SNAKE_CASE` (`INTENT_PATTERNS`, `CTR_BY_POSITION`)
- Environment variables: `UPPER_SNAKE_CASE` (`PERPLEXITY_API_KEY`, `GROQ_API_KEY`)
- Private methods: single leading underscore (`_load_template`, `_get_none`)

### Imports

Imports are organized in this order (no blank line enforcement, but follow the pattern):
1. Standard library (`os`, `re`, `json`, `asyncio`, `logging`, `pathlib`, `typing`, `datetime`, `dataclasses`)
2. Third-party (`aiohttp`, `google.genai`, `groq`, `openai`, `rich`, `click`, `pydantic`, `bs4`, `dotenv`)
3. Local/relative (`from .ai_router import SmartAIRouter`, `from core.formatter import AstroFormatter`)

Relative imports within `core/` package: use `from .module import Class`.
Exception: `core/formatter.py` uses absolute imports (`from core.schema_generator import ...`).
Top-level scripts (`generate.py`) use `sys.path.insert` then absolute imports.
Tests use `sys.path.insert(0, str(Path(__file__).parent.parent))` before importing `core`.

### Type Annotations

- Use `typing` module: `Dict`, `List`, `Optional`, `Any`, `Tuple`, `Callable`
- Function signatures include type hints for parameters and return values
- `@dataclass` used for structured data (`KeywordData`, `PagePerformance`, `RefreshTrigger`)
- `Enum` used for categories (`KeywordCategory`, `ContentRecommendation`, `OutputMode`)
- No `TypedDict` usage — prefer `Dict[str, Any]` or `@dataclass`

### Docstrings

- Module-level: triple-quoted one-liner describing purpose (e.g., `"""Smart AI Router - Right model for each job, no BS"""`)
- Class-level: short description of purpose and features
- Method-level: description + `Args:` / `Returns:` blocks where non-trivial
- Some modules include `Usage:` examples in module docstrings (see `gsc_analyzer.py`, `content_monitor.py`)

### Error Handling

- Broad `except Exception as e` with `logger.warning()` or `logger.error()` is the dominant pattern
- Specific exceptions used where appropriate: `json.JSONDecodeError`, `PermissionError`, `yaml.YAMLError`
- Graceful degradation: missing API keys skip features rather than crash
- Return empty structures on failure (empty dict `{}`, empty list `[]`, `None`)
- Never raise custom exceptions — the codebase has no custom exception classes
- AI API calls wrapped in try/except with fallback chains (e.g., OSS-120B → DeepSeek-V3 → Kimi-K2)

### Logging

- Every module uses: `logger = logging.getLogger(__name__)`
- Log levels: `logger.info()` for progress, `logger.warning()` for recoverable errors, `logger.error()` for failures
- `logger.debug()` for verbose/diagnostic info
- Rich logging configured in `generator.py:configure_logging()` — suppresses third-party noise
- Warning: `site_extractor.py` calls `logging.basicConfig()` at module level, which can conflict

### Async Patterns

- Heavy use of `asyncio` and `async/await` throughout pipeline
- `AsyncGroq` and `AsyncOpenAI` clients for non-blocking API calls
- `aiohttp` for HTTP requests (not `requests`)
- Async context managers: `async with SmartAIRouter() as router:` pattern in tests
- `nest_asyncio` used for questionary compatibility in interactive mode

### Configuration Loading

- JSON configs loaded from `config/` using `Path(__file__).parent.parent / 'config' / 'filename.json'`
- Module-level caching: load once, store in `_VARIABLE` (e.g., `_SEO_CONFIG`, `_ICP_RESEARCH_CONTEXT`)
- Environment variables via `os.getenv()` with no defaults (check for `None`)
- `python-dotenv`: `load_dotenv(Path(__file__).parent.parent / '.env', override=True)`

## Environment Variables

**Required** (for full pipeline):
- `PERPLEXITY_API_KEY` — Perplexity SERP analysis
- `GROQ_API_KEY` — Groq community mining + extraction
- `GOOGLE_API_KEY` — Gemini content generation

**Optional** (graceful degradation if missing):
- `NEBIUS_API_KEY` — Content polish step
- `GOOGLE_SERVICE_ACCOUNT_PATH` — GSC service account JSON path
- `GSC_SITE_URL` or `GSC_PROPERTY_URL` — Google Search Console site URL
- `AUTHOR_EMAIL` — Frontmatter author field

Store in `.env` at project root. Never commit `.env` or API keys.
See `.env.example` for full reference.

## Testing Patterns

- Test files: `test_*.py` in `tests/` and project root
- Test classes: `class TestClassName:` (no `unittest.TestCase` inheritance)
- Test functions: `def test_descriptive_name(self):`
- Async tests: `@pytest.mark.asyncio` decorator on class or method
- Fixtures in `tests/conftest.py`: `api_keys_available`, `require_api_keys`, `skip_if_no_api_keys`
- Assertions use `assert expr, "message"` style (not `assertEqual`)
- Integration tests use `async with Resource() as r:` context manager pattern
- Note: `core/` has no `__init__.py` — tests rely on `sys.path` manipulation

## Important Notes

- `output/` contents are gitignored — never commit generated MDX
- `config/*.json` files ARE committed (whitelisted in `.gitignore`)
- No Cursor rules (`.cursor/rules/`) or Copilot rules (`.github/copilot-instructions.md`) exist
- No pre-commit hooks, CI pipeline, or automated linting configured
- The `core/` package has no `__init__.py` — only `core/cli/` has one
