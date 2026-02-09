# TOS Searcher

## Project Description

A desktop GUI application that searches the internet for terms of service, contracts, policies, and agreements published by companies — specifically looking for hidden contests, prizes, giveaways, or rewards buried in the fine print. Inspired by real cases like Squaremouth hiding a $10,000 prize in their travel insurance policy for the first person who actually read it.

The app features a "Begin Search" button that triggers a multi-phase pipeline: discovering TOS documents via search engines, fetching and parsing them, then analyzing for hidden prize language. Results are displayed with confidence scores. The database tracks previously scanned documents so subsequent searches only process new content.

## Tech Stack

- **Language**: Python 3.12+
- **GUI**: `customtkinter` (modern desktop look)
- **Search engines**: `duckduckgo-search` (primary), `search-engines-scraper` (Bing/Google fallback)
- **Web scraping**: `requests` + `beautifulsoup4` (static pages), `playwright` (JS-rendered fallback)
- **Text analysis**: regex patterns (strong/medium/weak tiers) + `spaCy` NLP scoring
- **Configuration**: `pydantic-settings`
- **Storage**: SQLite via `sqlite3` (stdlib)
- **Formatting/Linting**: `ruff`
- **Type checking**: `mypy`
- **Testing**: `pytest`
- **Packaging**: `pyproject.toml` with pip

## Project Structure

```
TOS Searcher/
├── CLAUDE.md
├── pyproject.toml
├── src/tos_searcher/
│   ├── __init__.py
│   ├── __main__.py           # python -m tos_searcher
│   ├── app.py                # Entry point, launches GUI
│   ├── config.py             # Pydantic settings
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py    # CTk root window, layout
│   │   ├── search_frame.py   # Begin/Stop/Reset buttons, progress bar, stats
│   │   └── results_frame.py  # Scrollable result cards with confidence badges
│   ├── search/
│   │   ├── __init__.py       # SearchProvider protocol
│   │   ├── engine.py         # Search orchestrator, runs discovery queries
│   │   ├── pipeline.py       # Master 4-phase pipeline (discovery→fetch→analyze→results)
│   │   ├── duckduckgo.py     # DuckDuckGo provider (primary)
│   │   ├── bing.py           # Bing scraper via search-engines-scraper
│   │   ├── google.py         # Google scraper (least reliable, graceful fallback)
│   │   └── crawler.py        # Direct crawler for known domains' /terms, /tos pages
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── fetcher.py        # Two-tier: requests first, playwright fallback
│   │   └── parser.py         # HTML→clean text extraction
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── patterns.py       # Regex patterns (strong/medium/weak + negative)
│   │   ├── detector.py       # Core detection engine combining patterns + NLP
│   │   └── scorer.py         # spaCy-based confidence scoring
│   └── storage/
│       ├── __init__.py
│       ├── database.py       # SQLite wrapper (CRUD, stats, reset)
│       └── models.py         # Dataclasses: Document, Result, SearchQuery, SearchProgress
└── tests/
    ├── conftest.py
    ├── test_database.py
    ├── test_patterns.py
    ├── test_detector.py
    ├── test_fetcher.py
    └── test_parser.py
```

## Setup

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install playwright browsers (optional, for JS-rendered pages)
playwright install chromium

# Download spaCy model (optional, for NLP scoring)
python -m spacy download en_core_web_sm
```

## Running

```bash
# Launch the desktop GUI
python -m tos_searcher
# or
tos-searcher

# Run tests
pytest

# Lint and format
ruff check .
ruff format .

# Type check
mypy src/
```

## How It Works

1. **Discovery**: Searches DuckDuckGo, Bing, Google with TOS-related queries + crawls ~100 seed domains
2. **Fetching**: Downloads each discovered page, extracts clean text from HTML
3. **Analysis**: Runs regex patterns (3 tiers: strong/medium/weak) + negative patterns to penalize false positives, then NLP scoring via spaCy for confidence boost
4. **Results**: Displays matches in GUI with confidence badges (HIGH/MEDIUM/LOW), matched text, context, and clickable URLs

Subsequent runs skip previously scanned documents (tracked in SQLite). "Reset Database" wipes everything for a fresh start.

## Coding Conventions

- **Type hints**: All function signatures must have type annotations
- **Formatting**: `ruff format` (88 char line length, default settings)
- **Linting**: `ruff check` with default rules
- **Docstrings**: Only where logic isn't self-evident; no boilerplate docstrings
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Imports**: stdlib first, third-party second, local third (enforced by ruff)
- **Testing**: Each module gets a corresponding `test_*.py` file; use pytest fixtures
- **Error handling**: Validate at system boundaries (user input, HTTP responses); trust internal code
- **Threading**: GUI on main thread, search pipeline on background thread, communicate via queue.Queue

## Key Design Decisions

- **Two-tier fetching**: Try `requests` first (fast, lightweight), fall back to `playwright` for JS-rendered pages
- **Pattern + NLP hybrid**: Fast regex patterns as first pass, then spaCy NLP scoring to reduce false positives
- **Three-tier pattern scoring**: Strong signals (0.7-0.8), medium (0.2-0.3), weak (0.1) + negative patterns (-0.3 to -0.4) for sweepstakes rules pages
- **Confidence scoring**: Each match gets a score (0-1); displayed as HIGH (>=0.7), MEDIUM (>=0.4), LOW (<0.4)
- **Incremental searching**: SQLite tracks discovered URLs and executed queries; subsequent runs only process new content
- **Polite scraping**: 2-5 second random delays between search engine queries, 0.3s between page fetches, rotated User-Agent headers
