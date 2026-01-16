"""Flask application factory for Annotation Tool v2."""
import re
from markupsafe import Markup, escape
from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager

from app.config import SECRET_KEY, DATABASE_URI, ensure_dirs, get_logger
from app.models import db, User
from app.highlight_config import ISLAMIC_KEYWORDS, PEOPLE_KEYWORDS, PLACE_KEYWORDS


login_manager = LoginManager()


def highlight_references(text):
    """Highlight Quran, Hadith, year references and keywords in text.

    Highlights:
    - Quran verse patterns (2:255), Quran 2:255, Surah Al-Baqarah
    - Hadith patterns: Bukhari 1234, Sahih Muslim 567
    - Years: 1925, 2021, etc.
    - Islamic keywords from config (clickable to add reference)
    - People names from config
    - Place names from config

    Args:
        text: The paragraph text to process

    Returns:
        Markup-safe HTML with highlighted references
    """
    if not text:
        return text

    # Escape the text first for safety
    text = str(escape(text))

    # Quran verse patterns: (2:255), Quran 2:255, etc. - these are auto-detected refs
    quran_patterns = [
        r'\((\d{1,3}:\d{1,3}(?:-\d{1,3})?)\)',  # (2:255) or (2:255-257)
        r'(?:Quran|Qur\'?an)\s+(\d{1,3}:\d{1,3}(?:-\d{1,3})?)',  # Quran 2:255
        r'(?:Surah|Sura)\s+([\w\-]+(?:\s+[\w\-]+)?)',  # Surah Al-Baqarah
    ]

    # Hadith patterns with numbers - auto-detected refs
    hadith_patterns = [
        r'(?:Sahih\s+)?(?:Bukhari|Muslim|Tirmidhi|Abu\s+Dawud|Ibn\s+Majah|Nasai|Muwatta)\s*[,:]?\s*(\d+)',
    ]

    # Year patterns: 1925, 2021, etc. (years between 1000-2100)
    year_pattern = r'\b(1\d{3}|20\d{2}|21\d{2})\b'

    # Apply Quran verse highlighting (clickable, data attribute for quick add)
    for pattern in quran_patterns:
        text = re.sub(
            pattern,
            r'<span class="highlight-quran highlight-clickable" data-ref-type="quran" title="Click to add as reference">\g<0></span>',
            text,
            flags=re.IGNORECASE
        )

    # Apply Hadith highlighting (clickable)
    for pattern in hadith_patterns:
        text = re.sub(
            pattern,
            r'<span class="highlight-hadith highlight-clickable" data-ref-type="hadith" title="Click to add as reference">\g<0></span>',
            text,
            flags=re.IGNORECASE
        )

    # Apply Year highlighting
    text = re.sub(
        year_pattern,
        r'<span class="highlight-year" title="Year">\1</span>',
        text
    )

    # Apply Islamic keyword highlighting (from config)
    for keyword in ISLAMIC_KEYWORDS:
        # Word boundary match, case insensitive
        pattern = r'\b(' + re.escape(keyword) + r')\b'
        # Don't highlight if already inside a span
        text = re.sub(
            pattern,
            r'<span class="highlight-keyword highlight-islamic" title="Islamic term">\1</span>',
            text,
            flags=re.IGNORECASE
        )

    # Apply People keyword highlighting
    for keyword in PEOPLE_KEYWORDS:
        pattern = r'\b(' + re.escape(keyword) + r')\b'
        text = re.sub(
            pattern,
            r'<span class="highlight-keyword highlight-people" title="Person">\1</span>',
            text,
            flags=re.IGNORECASE
        )

    # Apply Place keyword highlighting
    for keyword in PLACE_KEYWORDS:
        pattern = r'\b(' + re.escape(keyword) + r')\b'
        text = re.sub(
            pattern,
            r'<span class="highlight-keyword highlight-place" title="Place">\1</span>',
            text,
            flags=re.IGNORECASE
        )

    return Markup(text)


def create_app(testing=False):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = SECRET_KEY
    if testing:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Ensure directories exist
    ensure_dirs()

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Initialize logger
    logger = get_logger()
    logger.info("app_initialized", testing=testing)

    # Register blueprints
    from app.routes import auth, dashboard, editor, api, admin
    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(editor.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(admin.bp)

    # Create tables
    with app.app_context():
        db.create_all()

    # Register error handlers
    _register_error_handlers(app)

    # Register template filters
    app.jinja_env.filters['highlight_refs'] = highlight_references

    return app


def _register_error_handlers(app):
    """Register error handlers for the application."""
    logger = get_logger()

    def is_api_request():
        """Check if request is to an API endpoint."""
        return request.path.startswith('/api/')

    @app.errorhandler(403)
    def forbidden(error):
        logger.warning("access_forbidden", path=request.path)
        if is_api_request():
            return jsonify({'error': 'Access forbidden'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        logger.warning("not_found", path=request.path)
        if is_api_request():
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        logger.warning("method_not_allowed", path=request.path, method=request.method)
        if is_api_request():
            return jsonify({'error': 'Method not allowed'}), 405
        return render_template('errors/405.html'), 405

    @app.errorhandler(500)
    def internal_error(error):
        logger.error("internal_error", path=request.path, error=str(error))
        db.session.rollback()
        if is_api_request():
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500
