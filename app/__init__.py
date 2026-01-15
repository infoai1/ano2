"""Flask application factory for Annotation Tool v2."""
from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager

from app.config import SECRET_KEY, DATABASE_URI, ensure_dirs, get_logger
from app.models import db, User


login_manager = LoginManager()


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
