# Claude Code Prompt: Annotation Tool v2

## PHASE 0: PRE-REQUISITES (Run These First)

### A. System Dependencies (Run on Server)

```bash
# 1. Chromium for E2E testing (Playwright)
sudo apt-get update
sudo apt-get install -y chromium-browser

# 2. Verify Chromium installed
chromium-browser --version
```

### B. Python Testing Tools

```bash
# 3. Create project directory
mkdir -p /root/annotation_tool_v2
cd /root/annotation_tool_v2

# 4. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Install core dependencies
pip install flask flask-sqlalchemy flask-login python-docx PyMuPDF structlog pytest pytest-cov

# 6. Install Playwright for E2E tests
pip install pytest-playwright
playwright install chromium
playwright install-deps
```

### C. Frontend Tools (Optional - for Tailwind)

```bash
# 7. Install Node.js if not present
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 8. Verify Node
node --version
npm --version

# 9. Install Tailwind CLI (standalone, no npm project needed)
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64
chmod +x tailwindcss-linux-x64
sudo mv tailwindcss-linux-x64 /usr/local/bin/tailwindcss

# 10. Verify Tailwind
tailwindcss --version
```

---

## PHASE 0 VERIFICATION

```bash
# Run this to verify all tools installed
echo "=== VERIFICATION ==="
python3 --version
chromium-browser --version 2>/dev/null || echo "Chromium: NOT FOUND"
playwright --version 2>/dev/null || echo "Playwright: NOT FOUND"
tailwindcss --version 2>/dev/null || echo "Tailwind: NOT FOUND"
echo "=== END ==="
```

**Expected output:**
```
=== VERIFICATION ===
Python 3.11.x
Chromium 12x.x.x
Version 1.4x.x
tailwindcss v3.x.x
=== END ===
```

---

## MAIN PROMPT FOR CLAUDE CODE

```
You are building an Islamic Text Annotation Tool. 

CRITICAL RULES:
1. THINK FIRST: Use extended thinking before ANY code
2. ASK IF UNCLEAR: Use ask_user tool for ambiguities
3. SMALL STEPS: One file at a time, test after each
4. AUTO-TEST: Every feature must have tests BEFORE implementation

PROJECT LOCATION: /root/annotation_tool_v2
PRD LOCATION: [Upload PRD_REALISTIC.md to Claude Code]

---

## YOUR WORKFLOW (Repeat for each feature)

1. READ the relevant PRD section
2. PLAN what files to create/modify
3. ASK user if anything unclear
4. WRITE tests first (TDD)
5. IMPLEMENT the feature
6. RUN tests to verify
7. COMMIT with clear message
8. REPORT status to user

---

## PHASE 1 TASKS (Foundation)

### Task 1.1: Project Structure
Create these files:
- /root/annotation_tool_v2/app/__init__.py
- /root/annotation_tool_v2/app/config.py (logging setup)
- /root/annotation_tool_v2/app/models.py (6 tables)
- /root/annotation_tool_v2/app/main.py (Flask app)
- /root/annotation_tool_v2/requirements.txt
- /root/annotation_tool_v2/pytest.ini

### Task 1.2: Database Models
Implement these tables (see PRD for schema):
- User
- Book
- Chapter
- Paragraph
- Group
- Reference
- Version

### Task 1.3: Authentication
- Login route
- Logout route
- Session management
- @login_required decorator

### Task 1.4: Dashboard
- List all books
- Show stats (para count, status)
- Upload DOCX button

### Task 1.5: Tests for Phase 1
Create:
- tests/conftest.py (fixtures)
- tests/test_auth.py
- tests/test_models.py

Run: `pytest tests/ -v`

---

## TESTING COMMANDS

```bash
# Run all tests
cd /root/annotation_tool_v2
source venv/bin/activate
pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test
pytest tests/test_auth.py -v

# Run E2E tests (Phase 6)
pytest tests/e2e/ -v --browser chromium
```

---

## DEBUGGING COMMANDS

```bash
# Check logs
tail -50 logs/app.log | python -m json.tool

# Check database
sqlite3 data/annotation.db ".tables"
sqlite3 data/annotation.db "SELECT * FROM users;"

# Test Flask app
cd /root/annotation_tool_v2
source venv/bin/activate
flask run --debug
```

---

## GIT WORKFLOW

```bash
# After each task
git add -A
git commit -m "Phase 1.X: [description]"

# Before moving to next phase
git tag phase-1-complete
```

---

## ASK USER IF:
- PRD section is ambiguous
- Multiple implementation approaches exist
- External API decisions needed
- UI design choices unclear

DO NOT ASSUME. ASK.

---

START WITH: Task 1.1 (Project Structure)
```

---

## FRONTEND DESIGN NOTES

For distinctive UI (not generic Bootstrap look):

### Color Palette (Islamic/Scholarly Theme)
```css
:root {
  --primary: #1e3a5f;      /* Deep blue - trust, knowledge */
  --secondary: #c9a227;    /* Gold - Islamic manuscripts */
  --accent: #2d6a4f;       /* Green - Islamic tradition */
  --background: #f8f5f0;   /* Warm paper texture */
  --text: #2c2c2c;         /* Soft black */
  --border: #d4c5b0;       /* Aged paper edge */
}
```

### Typography
```css
/* Headers: Scholarly serif */
h1, h2, h3 { font-family: 'Crimson Text', Georgia, serif; }

/* Body: Clean sans-serif */
body { font-family: 'Inter', -apple-system, sans-serif; }

/* References: Monospace for citations */
.reference { font-family: 'JetBrains Mono', monospace; }
```

### UI Principles
1. **No generic cards** - Use subtle shadows, paper-like textures
2. **No bright colors** - Muted, scholarly palette
3. **Clear hierarchy** - Proper heading sizes, whitespace
4. **Keyboard-first** - All actions have shortcuts
5. **Information density** - Show more data, less chrome

### Example: Paragraph Component
```html
<article class="para" data-id="p_042" data-reviewed="false">
  <aside class="para-meta">
    <span class="page-num">p.42</span>
    <span class="group-badge">G3</span>
  </aside>
  <div class="para-content">
    <p>The text content here...</p>
    <div class="para-refs">
      <span class="ref ref-quran" title="Quran 2:255">Q2:255 ✓</span>
      <span class="ref ref-hadith" title="Bukhari 1234">B:1234</span>
    </div>
  </div>
  <nav class="para-actions">
    <button class="btn-icon" title="Edit [E]">✎</button>
    <button class="btn-icon" title="Verify [V]">✓</button>
  </nav>
</article>
```

---

## INSTALL SUMMARY (Copy-Paste Ready)

```bash
# === RUN ALL AT ONCE ===
sudo apt-get update && \
sudo apt-get install -y chromium-browser && \
mkdir -p /root/annotation_tool_v2 && \
cd /root/annotation_tool_v2 && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install flask flask-sqlalchemy flask-login python-docx PyMuPDF structlog pytest pytest-cov pytest-playwright && \
playwright install chromium && \
playwright install-deps && \
echo "=== ALL INSTALLED ==="
```

---

## QUESTIONS FOR YOU BEFORE STARTING

1. **Server access**: Is `/root/annotation_tool_v2` the correct path?
2. **Existing tool**: Should we backup/migrate data from v1?
3. **Domain**: Still `annotate.spiritualmessage.org`?
4. **Users**: Create admin/annotator accounts during setup?
