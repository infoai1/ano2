"""Tests for admin panel user management."""
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.models import db, User


@pytest.fixture
def app():
    """Create test application."""
    app = create_app(testing=True)
    with app.app_context():
        db.create_all()
        # Create admin user
        admin = User(username='admin', role='admin')
        admin.set_password('adminpass')
        db.session.add(admin)
        # Create regular user
        user = User(username='annotator', role='annotator')
        user.set_password('userpass')
        db.session.add(user)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def admin_client(client, app):
    """Create authenticated admin client."""
    client.post('/login', data={
        'username': 'admin',
        'password': 'adminpass'
    })
    return client


@pytest.fixture
def user_client(client, app):
    """Create authenticated regular user client."""
    with app.test_client() as c:
        c.post('/login', data={
            'username': 'annotator',
            'password': 'userpass'
        })
        return c


class TestAdminPageAccess:
    """Test admin page access control."""

    def test_admin_page_requires_login(self, client):
        """Admin page should require authentication."""
        response = client.get('/admin/')
        assert response.status_code in [302, 401]

    def test_admin_page_requires_admin_role(self, app):
        """Admin page should require admin role."""
        with app.test_client() as c:
            c.post('/login', data={
                'username': 'annotator',
                'password': 'userpass'
            })
            response = c.get('/admin/')
            assert response.status_code == 403

    def test_admin_page_accessible_to_admin(self, admin_client):
        """Admin should be able to access admin page."""
        response = admin_client.get('/admin/')
        assert response.status_code == 200

    def test_admin_page_shows_user_list(self, admin_client):
        """Admin page should show list of users."""
        response = admin_client.get('/admin/')
        assert b'admin' in response.data
        assert b'annotator' in response.data


class TestUserCreation:
    """Test user creation."""

    def test_create_user_success(self, admin_client, app):
        """Admin should be able to create a new user."""
        response = admin_client.post('/admin/users', data={
            'username': 'newuser',
            'password': 'newpass123',
            'role': 'annotator'
        })
        assert response.status_code in [200, 302]

        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.role == 'annotator'

    def test_create_user_duplicate_username(self, admin_client):
        """Creating user with existing username should fail."""
        response = admin_client.post('/admin/users', data={
            'username': 'admin',
            'password': 'newpass123',
            'role': 'annotator'
        })
        assert response.status_code == 400

    def test_create_user_empty_username(self, admin_client):
        """Creating user with empty username should fail."""
        response = admin_client.post('/admin/users', data={
            'username': '',
            'password': 'somepass',
            'role': 'annotator'
        })
        assert response.status_code == 400

    def test_create_user_empty_password(self, admin_client):
        """Creating user with empty password should fail."""
        response = admin_client.post('/admin/users', data={
            'username': 'newuser',
            'password': '',
            'role': 'annotator'
        })
        assert response.status_code == 400

    def test_non_admin_cannot_create_user(self, app):
        """Non-admin users cannot create users."""
        with app.test_client() as c:
            c.post('/login', data={
                'username': 'annotator',
                'password': 'userpass'
            })
            response = c.post('/admin/users', data={
                'username': 'newuser',
                'password': 'newpass123',
                'role': 'annotator'
            })
            assert response.status_code == 403


class TestUserUpdate:
    """Test user updates."""

    def test_update_user_role(self, admin_client, app):
        """Admin should be able to update user role."""
        with app.app_context():
            user = User.query.filter_by(username='annotator').first()
            user_id = user.id

        response = admin_client.post(f'/admin/users/{user_id}', data={
            'role': 'reviewer'
        })
        assert response.status_code in [200, 302]

        with app.app_context():
            user = User.query.get(user_id)
            assert user.role == 'reviewer'

    def test_update_user_password(self, admin_client, app):
        """Admin should be able to reset user password."""
        with app.app_context():
            user = User.query.filter_by(username='annotator').first()
            user_id = user.id

        response = admin_client.post(f'/admin/users/{user_id}', data={
            'password': 'newpassword123'
        })
        assert response.status_code in [200, 302]

        with app.app_context():
            user = User.query.get(user_id)
            assert user.check_password('newpassword123')

    def test_update_nonexistent_user(self, admin_client):
        """Updating nonexistent user should 404."""
        response = admin_client.post('/admin/users/99999', data={
            'role': 'reviewer'
        })
        assert response.status_code == 404

    def test_non_admin_cannot_update_user(self, app):
        """Non-admin users cannot update users."""
        with app.app_context():
            user = User.query.filter_by(username='admin').first()
            user_id = user.id

        with app.test_client() as c:
            c.post('/login', data={
                'username': 'annotator',
                'password': 'userpass'
            })
            response = c.post(f'/admin/users/{user_id}', data={
                'role': 'annotator'
            })
            assert response.status_code == 403


class TestUserDeletion:
    """Test user deletion."""

    def test_delete_user_success(self, admin_client, app):
        """Admin should be able to delete a user."""
        with app.app_context():
            user = User.query.filter_by(username='annotator').first()
            user_id = user.id

        response = admin_client.delete(f'/admin/users/{user_id}')
        assert response.status_code in [200, 302]

        with app.app_context():
            user = User.query.get(user_id)
            assert user is None

    def test_delete_nonexistent_user(self, admin_client):
        """Deleting nonexistent user should 404."""
        response = admin_client.delete('/admin/users/99999')
        assert response.status_code == 404

    def test_non_admin_cannot_delete_user(self, app):
        """Non-admin users cannot delete users."""
        with app.app_context():
            user = User.query.filter_by(username='admin').first()
            user_id = user.id

        with app.test_client() as c:
            c.post('/login', data={
                'username': 'annotator',
                'password': 'userpass'
            })
            response = c.delete(f'/admin/users/{user_id}')
            assert response.status_code == 403

    def test_cannot_delete_self(self, admin_client, app):
        """Admin should not be able to delete themselves."""
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            admin_id = admin.id

        response = admin_client.delete(f'/admin/users/{admin_id}')
        assert response.status_code == 400


class TestUserRoles:
    """Test user role handling."""

    @pytest.mark.parametrize("role", ['admin', 'annotator', 'reviewer'])
    def test_valid_roles(self, admin_client, app, role):
        """All valid roles should be accepted."""
        response = admin_client.post('/admin/users', data={
            'username': f'test_{role}',
            'password': 'testpass123',
            'role': role
        })
        assert response.status_code in [200, 302]

        with app.app_context():
            user = User.query.filter_by(username=f'test_{role}').first()
            assert user.role == role

    def test_invalid_role_rejected(self, admin_client):
        """Invalid roles should be rejected."""
        response = admin_client.post('/admin/users', data={
            'username': 'testuser',
            'password': 'testpass123',
            'role': 'superuser'
        })
        assert response.status_code == 400


class TestUserListing:
    """Test user listing API."""

    def test_list_users_api(self, admin_client):
        """Admin can list all users via API."""
        response = admin_client.get('/admin/users')
        assert response.status_code == 200
        data = response.get_json()
        assert 'users' in data
        assert len(data['users']) >= 2

    def test_user_list_includes_roles(self, admin_client):
        """User list should include roles."""
        response = admin_client.get('/admin/users')
        data = response.get_json()
        for user in data['users']:
            assert 'role' in user

    def test_non_admin_cannot_list_users(self, app):
        """Non-admin cannot list users via API."""
        with app.test_client() as c:
            c.post('/login', data={
                'username': 'annotator',
                'password': 'userpass'
            })
            response = c.get('/admin/users')
            assert response.status_code == 403

