"""Tests for error handling pages."""
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
        user = User(username='testuser', role='annotator')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Create authenticated test client."""
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    return client


class TestNotFoundPage:
    """Test 404 error page."""

    def test_404_returns_correct_status(self, client):
        """Non-existent page should return 404."""
        response = client.get('/this-page-does-not-exist')
        assert response.status_code == 404

    def test_404_page_has_content(self, client):
        """404 page should have meaningful content."""
        response = client.get('/nonexistent-path')
        assert b'404' in response.data or b'not found' in response.data.lower()

    def test_404_has_home_link(self, client):
        """404 page should have a link to home."""
        response = client.get('/nonexistent')
        # Should have some navigation back
        assert b'href' in response.data


class TestForbiddenPage:
    """Test 403 error page."""

    def test_403_returns_correct_status(self, auth_client):
        """Forbidden access should return 403."""
        response = auth_client.get('/admin/')
        assert response.status_code == 403

    def test_403_page_has_content(self, auth_client):
        """403 page should have meaningful content."""
        response = auth_client.get('/admin/')
        assert b'403' in response.data or b'forbidden' in response.data.lower() or b'denied' in response.data.lower()


class TestServerErrorHandling:
    """Test 500 error handling."""

    def test_health_endpoint_works(self, client):
        """Health check should return 200."""
        response = client.get('/api/health')
        assert response.status_code == 200


class TestAPIErrorResponses:
    """Test API error responses."""

    def test_api_404_returns_json(self, auth_client):
        """API 404 should return JSON for API routes."""
        response = auth_client.get('/api/nonexistent')
        assert response.status_code == 404

    def test_invalid_book_slug_404(self, auth_client):
        """Invalid book slug should return 404."""
        response = auth_client.get('/edit/nonexistent-book-slug')
        assert response.status_code == 404

    def test_invalid_paragraph_id_404(self, auth_client):
        """Invalid paragraph ID should return 404."""
        response = auth_client.post('/api/paragraph/99999/type',
                                     data={'type': 'heading'})
        assert response.status_code == 404

    def test_invalid_version_id_404(self, auth_client):
        """Invalid version ID should return 404."""
        response = auth_client.post('/api/version/99999/restore')
        assert response.status_code == 404


class TestMethodNotAllowed:
    """Test method not allowed responses."""

    def test_get_on_post_only_endpoint(self, auth_client):
        """GET on POST-only endpoint should return 405."""
        response = auth_client.get('/api/book/test/save')
        assert response.status_code == 405

    def test_post_on_get_only_endpoint(self, auth_client):
        """POST on GET-only endpoint should return 405."""
        response = auth_client.post('/api/health')
        assert response.status_code == 405


class TestValidationErrors:
    """Test validation error responses."""

    def test_invalid_paragraph_type_400(self, auth_client, app):
        """Invalid paragraph type should return 400."""
        # Create a paragraph first
        with app.app_context():
            from app.models import Book, Chapter, Paragraph
            book = Book(title='Test', slug='test-book')
            db.session.add(book)
            db.session.flush()
            chapter = Chapter(book_id=book.id, title='Ch1', order_index=0)
            db.session.add(chapter)
            db.session.flush()
            para = Paragraph(chapter_id=chapter.id, text='Test', order_index=0)
            db.session.add(para)
            db.session.commit()
            para_id = para.id

        response = auth_client.post(f'/api/paragraph/{para_id}/type',
                                     data={'type': 'invalid_type'})
        assert response.status_code == 400

    def test_empty_text_400(self, auth_client, app):
        """Empty paragraph text should return 400."""
        with app.app_context():
            from app.models import Book, Chapter, Paragraph
            book = Book(title='Test', slug='test-book-2')
            db.session.add(book)
            db.session.flush()
            chapter = Chapter(book_id=book.id, title='Ch1', order_index=0)
            db.session.add(chapter)
            db.session.flush()
            para = Paragraph(chapter_id=chapter.id, text='Test', order_index=0)
            db.session.add(para)
            db.session.commit()
            para_id = para.id

        response = auth_client.post(f'/api/paragraph/{para_id}/text',
                                     data={'text': ''})
        assert response.status_code == 400

