# Islamic Text Annotation Tool v2 - Realistic PRD

**Version:** 2.0.0  
**Date:** January 2026  
**Status:** Evidence-Based Specification

---

## Reality Check (Based on Research)

| Your Situation | Implication |
|----------------|-------------|
| 3 users max | No need for PostgreSQL, Redis, or complex concurrency |
| Each user works on different file | No locking conflicts, simple save works |
| English text only | No RTL, no Arabic font issues, no bidirectional text |
| 145 books, ~500 para max | SQLite handles millions of rows easily |
| 32GB RAM server | Overkill for this workload |

**Bottom line:** You need a simple, reliable tool. Not enterprise architecture.

---

## Technology Stack (Evidence-Based)

| Layer | Choice | Why (Evidence) |
|-------|--------|----------------|
| **Backend** | Flask + HTMX | Doccano uses Django (similar). HTMX gives snappy updates without SPA complexity |
| **Database** | SQLite | Label Studio, Doccano, Prodigy ALL default to SQLite. Proven for annotation |
| **Frontend** | Jinja2 + HTMX + Tailwind | No build step. Server-rendered HTML with partial updates |
| **Testing** | pytest | spaCy's pattern: parametrized tests for detection |
| **Logging** | structlog | Industry standard for structured JSON logs |
| **Deploy** | Docker | Your existing setup works |

**Why not FastAPI + Svelte?**
- More complex to debug
- Build step adds friction
- No evidence it's better for your scale
- Claude Code will make fewer mistakes with simpler stack

---

## Project Structure

```
annotation_tool_v2/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Flask app entry
│   ├── config.py               # All configuration
│   ├── models.py               # SQLAlchemy models (ONE file)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py             # Login/logout
│   │   ├── dashboard.py        # Book list, stats
│   │   ├── editor.py           # Annotation editor
│   │   └── api.py              # HTMX endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── docx_parser.py      # DOCX extraction
│   │   ├── pdf_matcher.py      # PDF page matching
│   │   ├── quran_detector.py   # Quran reference detection
│   │   ├── hadith_detector.py  # Hadith reference detection
│   │   ├── footnote_linker.py  # Footnote detection + linking
│   │   └── grouping.py         # Token-based grouping
│   ├── templates/
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── editor.html
│   │   └── components/         # HTMX partial templates
│   │       ├── paragraph.html
│   │       ├── group.html
│   │       ├── reference_form.html
│   │       └── toast.html
│   └── static/
│       ├── css/
│       │   └── styles.css      # Tailwind output
│       └── js/
│           └── app.js          # Minimal JS (keyboard shortcuts)
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── test_quran_detection.py
│   ├── test_hadith_detection.py
│   ├── test_footnote_linking.py
│   ├── test_grouping.py
│   ├── test_export.py
│   └── test_api.py
├── logs/                       # Log files (gitignored)
├── data/
│   ├── annotation.db           # SQLite database
│   ├── uploads/                # DOCX, PDF files
│   ├── exports/                # JSON exports
│   └── backups/                # Daily snapshots
├── migrations/                 # Alembic migrations
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
└── README.md
```

**Total files: ~25** (manageable)

---

## Data Model (Simplified)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    User      │     │    Book      │     │   Chapter    │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id           │────<│ id           │────<│ id           │
│ username     │     │ title        │     │ book_id (FK) │
│ password_hash│     │ author       │     │ title        │
│ role         │     │ slug         │     │ order_index  │
│ created_at   │     │ status       │     └──────────────┘
└──────────────┘     │ locked_by    │            │
                     │ docx_path    │            │
                     │ pdf_path     │     ┌──────────────┐
                     │ created_at   │     │  Paragraph   │
                     │ updated_at   │     ├──────────────┤
                     └──────────────┘     │ id           │
                            │             │ chapter_id   │
                     ┌──────────────┐     │ text         │
                     │    Group     │     │ type         │
                     ├──────────────┤     │ group_id (FK)│
                     │ id           │─────│ page_number  │
                     │ book_id (FK) │     │ reviewed     │
                     │ token_count  │     │ order_index  │
                     │ order_index  │     └──────────────┘
                     └──────────────┘            │
                                          ┌──────────────┐
                     ┌──────────────┐     │  Reference   │
                     │   Version    │     ├──────────────┤
                     ├──────────────┤     │ id           │
                     │ id           │     │ paragraph_id │
                     │ book_id (FK) │     │ ref_type     │
                     │ snapshot     │     │ surah/hadith │
                     │ version_type │     │ verified     │
                     │ created_at   │     │ auto_detected│
                     │ created_by   │     └──────────────┘
                     └──────────────┘
```

**6 tables total.** No audit log table (use structured logs instead).

---

## Logging Strategy (Evidence-Based)

### What To Log

| Level | What | Example |
|-------|------|---------|
| **ERROR** | Exceptions, failed operations | "Failed to parse DOCX: corrupt file" |
| **WARNING** | Recoverable issues | "PDF page match confidence < 50%" |
| **INFO** | User actions, state changes | "User admin saved book peace-in-kashmir" |
| **DEBUG** | Detection details (dev only) | "Found 3 Quran refs in para 45" |

### What NOT To Log

- Full paragraph text (use paragraph ID)
- Passwords, API keys
- Redundant success messages

### Log Format

```python
# config.py
import structlog
import logging
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def setup_logging(debug: bool = False):
    """Configure structured logging."""
    
    # Processors for all logs
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.CallsiteParameterAdder(
            [structlog.processors.CallsiteParameter.FUNC_NAME,
             structlog.processors.CallsiteParameter.LINENO]
        ),
    ]
    
    # Console: human readable
    # File: JSON for parsing
    if debug:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    
    return structlog.get_logger()
```

### Usage Pattern

```python
from app.config import logger

# In routes
@app.route("/books/<slug>/save", methods=["POST"])
def save_book(slug):
    logger.info("save_started", book_slug=slug, user=current_user.username)
    try:
        # ... save logic
        logger.info("save_completed", book_slug=slug, paragraphs_saved=count)
        return redirect(url_for("editor.book", slug=slug))
    except Exception as e:
        logger.error("save_failed", book_slug=slug, error=str(e), exc_info=True)
        flash("Save failed. Check logs.", "error")
        return redirect(url_for("editor.book", slug=slug))
```

### Log Viewing

```bash
# Real-time logs
tail -f logs/app.log | jq .

# Filter errors
cat logs/app.log | jq 'select(.level == "error")'

# Find specific book
cat logs/app.log | jq 'select(.book_slug == "peace-in-kashmir")'
```

---

## Testing Strategy (Evidence-Based)

### Test Pyramid (Realistic)

| Type | Coverage | What |
|------|----------|------|
| **Unit tests** | 70% | Detection patterns, grouping logic, export format |
| **Integration** | 20% | API endpoints, database operations |
| **E2E** | 10% | Critical flows only (save, export) |

### Test Organization

```
tests/
├── conftest.py                 # Shared fixtures
├── test_quran_detection.py     # Parametrized pattern tests
├── test_hadith_detection.py    # Parametrized pattern tests
├── test_footnote_linking.py    # Link marker → footnote
├── test_grouping.py            # Token grouping logic
├── test_export.py              # JSON schema validation
└── test_api.py                 # Route tests
```

### Parametrized Tests (spaCy Pattern)

```python
# tests/test_quran_detection.py
import pytest
from app.services.quran_detector import detect_quran_refs

@pytest.mark.parametrize("text,expected_count,expected_refs", [
    # Standard formats
    ("Quran 2:255", 1, [{"surah": 2, "ayah_start": 255}]),
    ("quran 2:255", 1, [{"surah": 2, "ayah_start": 255}]),  # lowercase
    ("Qur'an 2:255", 1, [{"surah": 2, "ayah_start": 255}]),  # apostrophe
    
    # Range formats
    ("Quran 2:255-257", 1, [{"surah": 2, "ayah_start": 255, "ayah_end": 257}]),
    ("Quran 1:1-7", 1, [{"surah": 1, "ayah_start": 1, "ayah_end": 7}]),
    
    # Surah names
    ("Surah Al-Baqarah", 1, [{"surah": 2, "surah_name": "Al-Baqarah"}]),
    ("Surah Fatiha", 1, [{"surah": 1, "surah_name": "Fatiha"}]),
    
    # Multiple in one text
    ("See Quran 2:255 and Quran 3:1", 2, None),
    
    # Edge cases
    ("", 0, []),
    ("   ", 0, []),
    ("No references here", 0, []),
    ("Quran 999:999", 0, []),  # Invalid surah/ayah
    
    # Book-style references
    ("(2:255)", 1, [{"surah": 2, "ayah_start": 255}]),
    ("Al-Baqarah: 255", 1, [{"surah": 2, "ayah_start": 255}]),
])
def test_quran_detection(text, expected_count, expected_refs):
    refs = detect_quran_refs(text)
    assert len(refs) == expected_count
    if expected_refs:
        for i, expected in enumerate(expected_refs):
            for key, value in expected.items():
                assert refs[i].get(key) == value


# tests/test_hadith_detection.py
@pytest.mark.parametrize("text,expected_count,expected_collection", [
    # Standard formats
    ("Sahih Bukhari 1234", 1, "bukhari"),
    ("Bukhari, 1234", 1, "bukhari"),
    ("Sahih Muslim 567", 1, "muslim"),
    
    # Various collections
    ("Sunan Abu Dawud 123", 1, "abudawud"),
    ("Tirmidhi 456", 1, "tirmidhi"),
    ("Ibn Majah 789", 1, "ibnmajah"),
    
    # Edge cases
    ("", 0, None),
    ("Some random text", 0, None),
])
def test_hadith_detection(text, expected_count, expected_collection):
    refs = detect_hadith_refs(text)
    assert len(refs) == expected_count
    if expected_collection:
        assert refs[0]["collection"] == expected_collection


# tests/test_grouping.py
@pytest.mark.parametrize("token_counts,expected_groups", [
    # Simple case: all fit in one group
    ([100, 100, 100], 1),
    
    # Need to split
    ([400, 400, 400], 2),  # 800 max, so 2 groups
    
    # Edge: exactly at boundary
    ([512], 1),
    ([800], 1),
    ([801], 1),  # Single para over limit stays alone
    
    # Empty
    ([], 0),
])
def test_grouping_logic(token_counts, expected_groups):
    # Create mock paragraphs with given token counts
    paragraphs = [{"id": i, "token_count": tc} for i, tc in enumerate(token_counts)]
    groups = create_groups(paragraphs, min_tokens=512, max_tokens=800)
    assert len(groups) == expected_groups
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_quran_detection.py -v

# Run only fast tests (skip slow)
pytest -m "not slow"

# Run failed tests from last run
pytest --lf
```

### CI Integration (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=app --cov-fail-under=70
```

---

## Phase 1: Foundation (Week 1)

### Scope

| Feature | Details |
|---------|---------|
| Flask app | Basic structure, config, logging |
| Database | SQLite + SQLAlchemy models |
| Auth | Login/logout, session management |
| Dashboard | List books, basic stats |
| Book CRUD | Upload DOCX, create book, delete book |

### Deliverables

```
✅ Flask app runs
✅ Login works
✅ Can upload DOCX
✅ Books appear in dashboard
✅ Logging works (check logs/app.log)
```

### Tests (Phase 1)

```python
# tests/test_api.py
def test_login(client):
    response = client.post("/login", data={"username": "admin", "password": "admin123"})
    assert response.status_code == 302  # Redirect to dashboard

def test_upload_docx(client, auth):
    auth.login()
    response = client.post("/books/upload", data={"file": (io.BytesIO(b"..."), "test.docx")})
    assert response.status_code == 302

def test_dashboard_requires_auth(client):
    response = client.get("/dashboard")
    assert response.status_code == 302  # Redirect to login
```

### Debugging Checklist (Phase 1)

```bash
# 1. Check app is running
curl http://localhost:5000/health

# 2. Check database created
ls -la data/annotation.db

# 3. Check logs
tail -20 logs/app.log | jq .

# 4. Check login works
curl -X POST http://localhost:5000/login -d "username=admin&password=admin123" -v
```

---

## Phase 2: DOCX Parsing + Display (Week 2)

### Scope

| Feature | Details |
|---------|---------|
| DOCX parsing | Extract paragraphs, detect headings |
| Editor view | Display paragraphs in editor |
| Paragraph types | Identify: heading, subheading, paragraph, quote |
| Basic save | Save paragraph edits |

### Deliverables

```
✅ DOCX uploads and parses correctly
✅ Paragraphs display in editor
✅ Headings detected automatically
✅ Can edit paragraph type
✅ Save persists to database
```

### Tests (Phase 2)

```python
# tests/test_docx_parser.py
def test_parse_simple_docx():
    result = parse_docx("tests/fixtures/simple.docx")
    assert len(result["paragraphs"]) > 0
    assert result["paragraphs"][0]["text"] != ""

def test_detect_headings():
    result = parse_docx("tests/fixtures/with_headings.docx")
    headings = [p for p in result["paragraphs"] if p["type"] == "heading"]
    assert len(headings) >= 1

@pytest.mark.parametrize("filename,expected_para_count", [
    ("simple.docx", 10),
    ("complex.docx", 50),
    ("empty.docx", 0),
])
def test_various_docx_files(filename, expected_para_count):
    result = parse_docx(f"tests/fixtures/{filename}")
    assert len(result["paragraphs"]) == expected_para_count
```

### Debugging Checklist (Phase 2)

```bash
# 1. Test DOCX parsing directly
python -c "from app.services.docx_parser import parse_docx; print(parse_docx('test.docx'))"

# 2. Check paragraphs saved
sqlite3 data/annotation.db "SELECT COUNT(*) FROM paragraphs WHERE book_id=1;"

# 3. Check for parsing errors in logs
grep "docx" logs/app.log | grep "error"
```

---

## Phase 3: PDF Matching (Week 3)

### Scope

| Feature | Details |
|---------|---------|
| PDF upload | Upload alongside DOCX |
| Page extraction | Extract text from each PDF page |
| Matching | Match paragraphs to PDF pages |
| Display | Show page number in editor |

### Deliverables

```
✅ PDF uploads successfully
✅ Page numbers detected
✅ Paragraphs show page info
✅ "Not found" displayed for unmatched
✅ Can manually set page number
```

### Tests (Phase 3)

```python
# tests/test_pdf_matcher.py
def test_extract_pages():
    pages = extract_pdf_pages("tests/fixtures/sample.pdf")
    assert len(pages) > 0
    assert pages[0]["page_number"] == 1
    assert pages[0]["text"] != ""

@pytest.mark.parametrize("para_text,pdf_pages,expected_page", [
    ("This is exact match", [{"page": 1, "text": "This is exact match"}], 1),
    ("Partial match here", [{"page": 2, "text": "Partial match here and more"}], 2),
    ("No match at all xyz", [{"page": 1, "text": "Something else"}], None),
])
def test_matching_accuracy(para_text, pdf_pages, expected_page):
    result = match_paragraph_to_page(para_text, pdf_pages)
    if expected_page:
        assert result["page_number"] == expected_page
    else:
        assert result["page_number"] is None
```

### Debugging Checklist (Phase 3)

```bash
# 1. Test PDF extraction
python -c "from app.services.pdf_matcher import extract_pdf_pages; print(len(extract_pdf_pages('test.pdf')))"

# 2. Check match confidence
sqlite3 data/annotation.db "SELECT page_number, COUNT(*) FROM paragraphs WHERE book_id=1 GROUP BY page_number;"

# 3. Check for low confidence matches
grep "confidence" logs/app.log | grep -E "confidence.*[0-4]\."
```

---

## Phase 4: Reference Detection (Week 4)

### Scope

| Feature | Details |
|---------|---------|
| Quran detection | Auto-detect Quran references |
| Hadith detection | Auto-detect Hadith references |
| Footnote linking | Detect markers, link to footnotes |
| Manual add/edit | Add references manually |
| Verification | Mark as verified/unverified |

### Deliverables

```
✅ Quran refs auto-detected
✅ Hadith refs auto-detected
✅ Footnotes linked automatically
✅ Can add manual references
✅ Can verify/unverify references
```

### Tests (Phase 4)

All the parametrized tests from earlier, plus:

```python
# tests/test_footnote_linking.py
@pytest.mark.parametrize("para_text,footnotes,expected_links", [
    (
        "The Prophet said¹ that peace is best²",
        ["1. Sahih Bukhari 1234", "2. Quran 2:255"],
        [
            {"marker": "1", "linked_to": "Sahih Bukhari 1234"},
            {"marker": "2", "linked_to": "Quran 2:255"},
        ]
    ),
    (
        "No footnotes here",
        [],
        []
    ),
])
def test_footnote_linking(para_text, footnotes, expected_links):
    result = link_footnotes(para_text, footnotes)
    assert len(result) == len(expected_links)
```

### Debugging Checklist (Phase 4)

```bash
# 1. Test detection on sample text
python -c "from app.services.quran_detector import detect_quran_refs; print(detect_quran_refs('Quran 2:255'))"

# 2. Check detection stats
sqlite3 data/annotation.db "SELECT ref_type, COUNT(*) FROM references GROUP BY ref_type;"

# 3. Find unverified references
sqlite3 data/annotation.db "SELECT * FROM references WHERE verified=0 LIMIT 10;"
```

---

## Phase 5: Grouping + Export (Week 5)

### Scope

| Feature | Details |
|---------|---------|
| Auto-grouping | Group paragraphs by token count (512-800) |
| Group display | Show group boundaries in UI |
| Group editing | Move paragraphs between groups |
| Book JSON export | Export full book structure |
| LightRAG export | Export for LightRAG ingestion |

### Deliverables

```
✅ Groups created automatically
✅ Groups visible in editor
✅ Can edit group membership
✅ Book JSON exports correctly
✅ LightRAG JSON exports correctly
```

### Tests (Phase 5)

```python
# tests/test_export.py
import jsonschema

BOOK_JSON_SCHEMA = {
    "type": "object",
    "required": ["book_metadata", "structure"],
    "properties": {
        "book_metadata": {
            "type": "object",
            "required": ["title", "author", "slug"]
        },
        "structure": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type", "title", "paragraphs"]
            }
        }
    }
}

def test_book_json_schema():
    book = create_test_book()
    export = export_book_json(book.id)
    jsonschema.validate(export, BOOK_JSON_SCHEMA)  # Raises if invalid

def test_lightrag_export_format():
    book = create_test_book()
    export = export_lightrag_json(book.id)
    assert "chunks" in export
    assert len(export["chunks"]) > 0
    assert "content" in export["chunks"][0]
    assert "source_ids" in export["chunks"][0]
```

### Debugging Checklist (Phase 5)

```bash
# 1. Check group distribution
sqlite3 data/annotation.db "SELECT token_count, COUNT(*) FROM groups WHERE book_id=1 GROUP BY token_count ORDER BY token_count;"

# 2. Validate export JSON
python -c "import json; json.load(open('data/exports/book.json'))"

# 3. Check for orphan paragraphs (no group)
sqlite3 data/annotation.db "SELECT id FROM paragraphs WHERE group_id IS NULL AND book_id=1;"
```

---

## Phase 6: Polish + Deploy (Week 6)

### Scope

| Feature | Details |
|---------|---------|
| Version history | Save/restore versions |
| Admin panel | User management, book approval |
| Error handling | Graceful error pages |
| Performance | Lazy loading for long books |
| Deploy | Docker, nginx, SSL |

### Deliverables

```
✅ Can save manual versions
✅ Can restore from version
✅ Admin can manage users
✅ Errors show friendly message
✅ Long books load fast
✅ Deployed to production
```

### Deployment Checklist

```bash
# 1. Build and run
docker-compose up -d --build

# 2. Check health
curl https://annotate.spiritualmessage.org/health

# 3. Check logs
docker-compose logs -f app

# 4. Run production tests
pytest tests/ --env=production

# 5. Backup before go-live
cp data/annotation.db data/backups/annotation_$(date +%Y%m%d).db
```

---

## Summary: What Changed From Original Spec

| Original | Realistic |
|----------|-----------|
| FastAPI + Svelte | Flask + HTMX (simpler) |
| 8 database tables | 6 tables (no audit log table) |
| 100% test coverage | 70% on critical paths |
| 35+ API endpoints | ~15 routes (HTMX reduces API needs) |
| 6 weeks | 6 weeks (same, but more buffer) |
| Complex logging config | Simple structlog setup |
| Sentry integration | File-based logs (free) |

---

## Test Commands Quick Reference

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Run specific test file
pytest tests/test_quran_detection.py -v

# Run tests matching pattern
pytest -k "quran"

# Run only fast tests
pytest -m "not slow"

# Watch mode (rerun on changes)
pytest-watch

# Debug failing test
pytest tests/test_quran_detection.py::test_quran_detection -v --pdb
```

---

## Debug Commands Quick Reference

```bash
# View recent logs
tail -50 logs/app.log | jq .

# Filter errors
cat logs/app.log | jq 'select(.level == "error")'

# Find specific book
cat logs/app.log | jq 'select(.book_slug == "peace-in-kashmir")'

# Database queries
sqlite3 data/annotation.db ".tables"
sqlite3 data/annotation.db "SELECT * FROM books;"
sqlite3 data/annotation.db ".schema paragraphs"

# Check disk usage
du -sh data/*

# Container logs
docker-compose logs -f app
```

---

## Next Step

**Confirm this PRD is acceptable, then I create:**

1. `requirements.txt` - All Python dependencies
2. `app/models.py` - SQLAlchemy models
3. `app/config.py` - Configuration + logging setup
4. `tests/conftest.py` - Test fixtures

Then build Phase 1.
