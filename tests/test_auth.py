"""Tests for authentication routes."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app():
    """Create test Flask app."""
    from app import create_app
    app = create_app(testing=True)
    with app.app_context():
        from app.models import db, User
        db.create_all()
        # Create test user
        user = User(username='testuser', role='annotator')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestLoginPage:
    """Test login page rendering."""

    def test_login_page_renders(self, client):
        """Login page should render."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data

    def test_login_page_has_form(self, client):
        """Login page should have username and password fields."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'username' in response.data
        assert b'password' in response.data


class TestLogin:
    """Test login functionality."""

    def test_login_success(self, client):
        """Valid credentials should log in user."""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to dashboard
        assert b'Dashboard' in response.data or b'dashboard' in response.data or response.request.path == '/dashboard'

    def test_login_wrong_password(self, client):
        """Wrong password should fail."""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpass'
        })
        # Should stay on login page or show error
        assert response.status_code in [200, 401]

    def test_login_nonexistent_user(self, client):
        """Nonexistent user should fail."""
        response = client.post('/login', data={
            'username': 'nobody',
            'password': 'testpass'
        })
        assert response.status_code in [200, 401]


class TestLogout:
    """Test logout functionality."""

    def test_logout_redirects(self, client):
        """Logout should redirect to login page."""
        # First login
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        })
        # Then logout
        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200

    def test_logout_clears_session(self, client):
        """After logout, protected pages should redirect to login."""
        # Login
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        })
        # Logout
        client.get('/logout')
        # Try to access protected page
        response = client.get('/dashboard')
        # Should redirect to login
        assert response.status_code in [302, 401]


class TestProtectedRoutes:
    """Test route protection."""

    def test_dashboard_requires_login(self, client):
        """Dashboard should redirect unauthenticated users."""
        response = client.get('/dashboard')
        assert response.status_code in [302, 401]

    def test_dashboard_accessible_when_logged_in(self, client):
        """Dashboard should be accessible when logged in."""
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        })
        response = client.get('/dashboard')
        assert response.status_code == 200
