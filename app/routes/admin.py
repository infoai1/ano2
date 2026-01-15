"""Admin routes for user management."""
from functools import wraps
from flask import Blueprint, request, jsonify, render_template, abort
from flask_login import login_required, current_user

from app.models import db, User
from app.config import get_logger

bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = get_logger()

VALID_ROLES = {'admin', 'annotator', 'reviewer'}


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            logger.warning("admin_access_denied",
                          user=current_user.username,
                          endpoint=request.endpoint)
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/')
@admin_required
def admin_panel():
    """Admin panel main page."""
    users = User.query.order_by(User.username).all()
    return render_template('admin/index.html', users=users)


@bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    """List all users (JSON API)."""
    users = User.query.order_by(User.username).all()
    user_list = []
    for user in users:
        user_list.append({
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'created_at': user.created_at.isoformat() if user.created_at else None
        })
    return jsonify({'users': user_list})


@bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    """Create a new user."""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'annotator').strip()

    # Validation
    if not username:
        logger.warning("create_user_empty_username", admin=current_user.username)
        return jsonify({'error': 'Username is required'}), 400

    if not password:
        logger.warning("create_user_empty_password", admin=current_user.username)
        return jsonify({'error': 'Password is required'}), 400

    if role not in VALID_ROLES:
        logger.warning("create_user_invalid_role",
                      admin=current_user.username,
                      role=role)
        return jsonify({'error': f'Invalid role. Must be one of: {", ".join(VALID_ROLES)}'}), 400

    # Check for duplicate
    if User.query.filter_by(username=username).first():
        logger.warning("create_user_duplicate",
                      admin=current_user.username,
                      username=username)
        return jsonify({'error': 'Username already exists'}), 400

    # Create user
    user = User(username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    logger.info("user_created",
                admin=current_user.username,
                username=username,
                role=role)

    return jsonify({
        'status': 'ok',
        'message': f'User {username} created',
        'user_id': user.id
    })


@bp.route('/users/<int:user_id>', methods=['POST'])
@admin_required
def update_user(user_id):
    """Update user details."""
    user = User.query.get_or_404(user_id)

    new_role = request.form.get('role')
    new_password = request.form.get('password')

    if new_role:
        if new_role not in VALID_ROLES:
            logger.warning("update_user_invalid_role",
                          admin=current_user.username,
                          user_id=user_id,
                          role=new_role)
            return jsonify({'error': f'Invalid role. Must be one of: {", ".join(VALID_ROLES)}'}), 400
        user.role = new_role
        logger.info("user_role_updated",
                   admin=current_user.username,
                   username=user.username,
                   new_role=new_role)

    if new_password:
        user.set_password(new_password)
        logger.info("user_password_reset",
                   admin=current_user.username,
                   username=user.username)

    db.session.commit()

    return jsonify({
        'status': 'ok',
        'message': f'User {user.username} updated'
    })


@bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)

    # Cannot delete self
    if user.id == current_user.id:
        logger.warning("delete_self_attempt", admin=current_user.username)
        return jsonify({'error': 'Cannot delete yourself'}), 400

    username = user.username
    db.session.delete(user)
    db.session.commit()

    logger.info("user_deleted",
                admin=current_user.username,
                deleted_user=username)

    return jsonify({
        'status': 'ok',
        'message': f'User {username} deleted'
    })
