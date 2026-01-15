"""Authentication routes."""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.models import User
from app.config import get_logger

bp = Blueprint('auth', __name__)
logger = get_logger()


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            logger.info("user_login_success", username=username)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            logger.warning("user_login_failed", username=username)
            flash('Invalid username or password', 'error')

    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    username = current_user.username
    logout_user()
    logger.info("user_logout", username=username)
    return redirect(url_for('auth.login'))
