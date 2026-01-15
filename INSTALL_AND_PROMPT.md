# STEP 1: INSTALL COMMANDS (Run on Server First)

## A. One-Shot Install (Copy-Paste This Entire Block)

```bash
# === ANNOTATION TOOL V2 SETUP ===
cd /root

# System deps
sudo apt-get update
sudo apt-get install -y chromium-browser fonts-liberation libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1

# Project folder
mkdir -p annotation_tool_v2
cd annotation_tool_v2

# Python virtual env
python3 -m venv venv
source venv/bin/activate

# Python packages
pip install --upgrade pip
pip install \
    flask==3.0.0 \
    flask-sqlalchemy==3.1.1 \
    flask-login==0.6.3 \
    python-docx==1.1.0 \
    PyMuPDF==1.23.8 \
    structlog==24.1.0 \
    pytest==8.0.0 \
    pytest-cov==4.1.0 \
    pytest-playwright==0.4.4 \
    jsonschema==4.21.1

# Playwright browsers
playwright install chromium
playwright install-deps chromium

# Tailwind CLI (standalone)
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x tailwindcss-linux-x64
sudo mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss

# Create folder structure
mkdir -p app/routes app/services app/templates/components app/static/css app/static/js
mkdir -p tests/fixtures data/uploads data/exports data/backups logs

# Verify
echo "=== VERIFICATION ==="
python --version
playwright --version
tailwindcss --version
chromium-browser --version
echo "=== SETUP COMPLETE ==="
```

---

## B. Verify Installation

```bash
cd /root/annotation_tool_v2
source venv/bin/activate

# Should show versions, not errors
python -c "import flask; print(f'Flask: {flask.__version__}')"
python -c "import structlog; print('structlog: OK')"
python -c "import fitz; print(f'PyMuPDF: {fitz.version}')"
python -c "import docx; print('python-docx: OK')"
playwright --version
```

**Expected:**
```
Flask: 3.0.0
structlog: OK
PyMuPDF: (1.23.8, ...)
python-docx: OK
Version 1.4x.x
```

---

# STEP 2: CLAUDE CODE PROMPT

Upload these files to Claude Code:
1. `PRD_REALISTIC.md` (the spec)
2. `CLAUDE_CODE_PROMPT.md` (this file)

Then paste this prompt:

---

```
# ANNOTATION TOOL V2 BUILD

## RULES (CRITICAL)
1. **ULTRATHINK**: Use extended thinking before every action
2. **ASK FIRST**: Use ask_user() if ANYTHING is unclear
3. **SMALL STEPS**: One file at a time, max 100 lines per file
4. **TDD**: Write test BEFORE implementation
5. **VERIFY**: Run tests after EVERY change

## PROJECT INFO
- Location: /root/annotation_tool_v2
- Python venv: /root/annotation_tool_v2/venv (already created)
- Spec: See PRD_REALISTIC.md

## YOUR WORKFLOW

For EACH task:
1. Read PRD section
2. Think: What could go wrong?
3. Ask user if unclear
4. Write test file first
5. Run test (should FAIL)
6. Implement code
7. Run test (should PASS)
8. Git commit

## PHASE 1 CHECKLIST

### 1.1 Config + Logging
□ Create app/config.py with structlog setup
□ Create tests/test_config.py
□ Verify: `pytest tests/test_config.py -v`

### 1.2 Database Models
□ Create app/models.py (6 tables)
□ Create tests/test_models.py
□ Verify: `pytest tests/test_models.py -v`

### 1.3 Flask App
□ Create app/__init__.py (app factory)
□ Create app/main.py (entry point)
□ Create tests/conftest.py (fixtures)
□ Verify: `flask run` works

### 1.4 Authentication
□ Create app/routes/auth.py
□ Create tests/test_auth.py
□ Verify: Login/logout works

### 1.5 Dashboard
□ Create app/routes/dashboard.py
□ Create app/templates/dashboard.html
□ Create tests/test_dashboard.py
□ Verify: Dashboard shows books

## COMMANDS TO USE

```bash
# Activate env (always first)
cd /root/annotation_tool_v2 && source venv/bin/activate

# Run tests
pytest -v

# Run specific test
pytest tests/test_config.py -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Start Flask dev server
flask run --host=0.0.0.0 --port=5000 --debug

# Check logs
tail -20 logs/app.log | python -m json.tool

# Database inspection
sqlite3 data/annotation.db ".tables"
sqlite3 data/annotation.db "SELECT * FROM users;"
```

## UI DESIGN REQUIREMENTS

NOT generic Bootstrap. Use this palette:

```css
/* Scholarly/Islamic theme */
--primary: #1e3a5f;      /* Deep blue */
--secondary: #c9a227;    /* Gold accent */
--accent: #2d6a4f;       /* Islamic green */
--bg: #f8f5f0;           /* Warm paper */
--text: #2c2c2c;
--border: #d4c5b0;
```

UI principles:
- Minimal chrome, maximum content
- Keyboard shortcuts for everything
- Subtle shadows, no harsh borders
- Serif headers, sans-serif body

## QUESTIONS TO ASK ME

Before starting, ask me:
1. Confirm project path is /root/annotation_tool_v2?
2. Should I migrate data from v1 tool?
3. Create default admin user during setup?
4. Any specific styling preferences?

## START

Begin with Task 1.1: Config + Logging
Think first. Ask if unclear. Write test first.
```

---

# STEP 3: EXPECTED PROGRESS

After Claude Code completes each phase, verify:

## Phase 1 Verification
```bash
cd /root/annotation_tool_v2
source venv/bin/activate

# All tests pass
pytest -v
# Expected: 10+ tests, all PASSED

# App runs
flask run --debug
# Visit http://server:5000 - should see login page

# Logs work
cat logs/app.log | head -5
# Expected: JSON log entries

# Database created
sqlite3 data/annotation.db ".tables"
# Expected: users books chapters paragraphs groups references versions
```

---

# TROUBLESHOOTING

## Playwright fails to install
```bash
# Install deps manually
sudo apt-get install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2

# Retry
playwright install chromium
```

## Tailwind not found
```bash
# Check if installed
which tailwindcss

# If not, reinstall
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x tailwindcss-linux-x64
sudo mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss
```

## Permission denied on /root
```bash
# If running as non-root user
mkdir -p ~/annotation_tool_v2
cd ~/annotation_tool_v2
# Update all paths in prompt accordingly
```
