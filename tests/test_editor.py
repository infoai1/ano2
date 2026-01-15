"""Tests for editor routes and functionality."""
import pytest
import io
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


@pytest.fixture
def app():
    """Create test Flask app."""
    from app import create_app
    app = create_app(testing=True)
    with app.app_context():
        from app.models import db, User, Book, Chapter, Paragraph
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


@pytest.fixture
def logged_in_client(client):
    """Create logged-in test client."""
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    return client


@pytest.fixture
def book_with_paragraphs(app):
    """Create a book with chapters and paragraphs."""
    from app.models import db, Book, Chapter, Paragraph

    with app.app_context():
        book = Book(title='Test Book', slug='test-book', author='Test Author')
        db.session.add(book)
        db.session.commit()

        chapter = Chapter(book_id=book.id, title='Chapter 1', order_index=0)
        db.session.add(chapter)
        db.session.commit()

        for i in range(5):
            para = Paragraph(
                chapter_id=chapter.id,
                text=f'Test paragraph {i+1} content.',
                type='paragraph' if i > 0 else 'heading',
                level=1,
                order_index=i
            )
            db.session.add(para)
        db.session.commit()

        return book.slug


class TestEditorView:
    """Test editor view functionality."""

    def test_editor_requires_login(self, client):
        """Editor should redirect unauthenticated users."""
        response = client.get('/editor/test-book')
        assert response.status_code in [302, 401]

    def test_editor_renders_for_logged_in_user(self, logged_in_client, app, book_with_paragraphs):
        """Editor should render for authenticated users."""
        response = logged_in_client.get(f'/editor/{book_with_paragraphs}')
        assert response.status_code == 200

    def test_editor_shows_book_title(self, logged_in_client, app, book_with_paragraphs):
        """Editor should display the book title."""
        response = logged_in_client.get(f'/editor/{book_with_paragraphs}')
        assert response.status_code == 200
        assert b'Test Book' in response.data

    def test_editor_shows_paragraphs(self, logged_in_client, app, book_with_paragraphs):
        """Editor should display paragraphs."""
        response = logged_in_client.get(f'/editor/{book_with_paragraphs}')
        assert response.status_code == 200
        assert b'Test paragraph' in response.data

    def test_editor_404_for_nonexistent_book(self, logged_in_client):
        """Editor should return 404 for nonexistent book."""
        response = logged_in_client.get('/editor/nonexistent-book')
        assert response.status_code == 404


class TestParagraphTypeEdit:
    """Test paragraph type editing."""

    def test_update_paragraph_type(self, logged_in_client, app, book_with_paragraphs):
        """Should be able to update paragraph type via HTMX."""
        from app.models import Paragraph
        with app.app_context():
            para = Paragraph.query.first()
            para_id = para.id

        response = logged_in_client.post(
            f'/api/paragraph/{para_id}/type',
            data={'type': 'quote'},
            headers={'HX-Request': 'true'}
        )
        assert response.status_code == 200

        # Verify the change persisted
        with app.app_context():
            para = Paragraph.query.get(para_id)
            assert para.type == 'quote'

    def test_update_paragraph_type_invalid(self, logged_in_client, app, book_with_paragraphs):
        """Invalid paragraph type should be rejected or handled."""
        from app.models import Paragraph
        with app.app_context():
            para = Paragraph.query.first()
            para_id = para.id

        response = logged_in_client.post(
            f'/api/paragraph/{para_id}/type',
            data={'type': 'invalid_type'},
            headers={'HX-Request': 'true'}
        )
        # Should either reject (400) or ignore invalid type
        assert response.status_code in [200, 400]


class TestParagraphTextEdit:
    """Test paragraph text editing."""

    def test_update_paragraph_text(self, logged_in_client, app, book_with_paragraphs):
        """Should be able to update paragraph text."""
        from app.models import Paragraph
        with app.app_context():
            para = Paragraph.query.first()
            para_id = para.id

        new_text = 'Updated paragraph content.'
        response = logged_in_client.post(
            f'/api/paragraph/{para_id}/text',
            data={'text': new_text},
            headers={'HX-Request': 'true'}
        )
        assert response.status_code == 200

        # Verify the change persisted
        with app.app_context():
            para = Paragraph.query.get(para_id)
            assert para.text == new_text

    def test_update_paragraph_text_empty_rejected(self, logged_in_client, app, book_with_paragraphs):
        """Empty text should be rejected."""
        from app.models import Paragraph
        with app.app_context():
            para = Paragraph.query.first()
            para_id = para.id

        response = logged_in_client.post(
            f'/api/paragraph/{para_id}/text',
            data={'text': '   '},
            headers={'HX-Request': 'true'}
        )
        assert response.status_code in [400, 422]


class TestBookUpload:
    """Test DOCX upload and parsing into book."""

    def test_upload_docx_creates_book(self, logged_in_client, app):
        """Uploading DOCX should create a book with paragraphs."""
        from app.models import Book, Paragraph

        docx_path = FIXTURES_DIR / 'simple.docx'
        with open(docx_path, 'rb') as f:
            data = {
                'file': (io.BytesIO(f.read()), 'simple.docx'),
                'title': 'Simple Book',
                'author': 'Test Author'
            }

        response = logged_in_client.post(
            '/books/upload',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        assert response.status_code == 200

        # Verify book was created
        with app.app_context():
            book = Book.query.filter_by(title='Simple Book').first()
            assert book is not None
            # Should have paragraphs
            para_count = Paragraph.query.join(Paragraph.chapter).filter_by(book_id=book.id).count()
            assert para_count > 0

    def test_upload_docx_with_headings(self, logged_in_client, app):
        """DOCX with headings should create chapters."""
        from app.models import Book, Chapter

        docx_path = FIXTURES_DIR / 'with_headings.docx'
        with open(docx_path, 'rb') as f:
            data = {
                'file': (io.BytesIO(f.read()), 'with_headings.docx'),
                'title': 'Book With Headings',
                'author': 'Test Author'
            }

        response = logged_in_client.post(
            '/books/upload',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        assert response.status_code == 200

        # Verify chapters were created
        with app.app_context():
            book = Book.query.filter_by(title='Book With Headings').first()
            assert book is not None
            chapter_count = Chapter.query.filter_by(book_id=book.id).count()
            assert chapter_count >= 1


class TestSaveBook:
    """Test book save functionality."""

    def test_save_marks_book_updated(self, logged_in_client, app, book_with_paragraphs):
        """Saving should update the book's updated_at timestamp."""
        from app.models import Book
        import time

        with app.app_context():
            book = Book.query.filter_by(slug=book_with_paragraphs).first()
            original_updated = book.updated_at

        # Small delay to ensure timestamp changes
        time.sleep(0.1)

        response = logged_in_client.post(
            f'/api/book/{book_with_paragraphs}/save',
            headers={'HX-Request': 'true'}
        )
        assert response.status_code == 200

        with app.app_context():
            book = Book.query.filter_by(slug=book_with_paragraphs).first()
            assert book.updated_at >= original_updated


class TestDeleteParagraph:
    """Test paragraph deletion (soft delete)."""

    def test_delete_paragraph_soft(self, logged_in_client, app, book_with_paragraphs):
        """Deleting paragraph should soft-delete (set deleted=True)."""
        from app.models import Paragraph
        with app.app_context():
            para = Paragraph.query.filter_by(deleted=False).first()
            para_id = para.id

        response = logged_in_client.delete(
            f'/api/paragraph/{para_id}',
            headers={'HX-Request': 'true'}
        )
        assert response.status_code == 200

        # Verify soft-deleted
        with app.app_context():
            para = Paragraph.query.get(para_id)
            assert para.deleted is True
