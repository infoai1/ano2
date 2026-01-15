"""Tests for dashboard routes including DOCX upload."""
import pytest
import sys
from pathlib import Path
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


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


@pytest.fixture
def logged_in_client(client):
    """Create logged-in test client."""
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    return client


class TestDashboardPage:
    """Test dashboard page rendering."""

    def test_dashboard_requires_login(self, client):
        """Dashboard should redirect unauthenticated users."""
        response = client.get('/dashboard')
        assert response.status_code in [302, 401]

    def test_dashboard_renders_when_logged_in(self, logged_in_client):
        """Dashboard should render for authenticated users."""
        response = logged_in_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Dashboard' in response.data

    def test_dashboard_has_upload_button(self, logged_in_client):
        """Dashboard should have upload button."""
        response = logged_in_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Upload DOCX' in response.data

    def test_dashboard_has_upload_modal(self, logged_in_client):
        """Dashboard should have upload modal form."""
        response = logged_in_client.get('/dashboard')
        assert response.status_code == 200
        assert b'uploadModal' in response.data
        assert b'enctype="multipart/form-data"' in response.data


class TestUploadRoute:
    """Test DOCX upload functionality."""

    def test_upload_requires_login(self, client):
        """Upload should require authentication."""
        response = client.post('/books/upload')
        assert response.status_code in [302, 401]

    def test_upload_no_file(self, logged_in_client):
        """Upload without file should return error."""
        response = logged_in_client.post('/books/upload', follow_redirects=True)
        assert response.status_code == 200
        assert b'No file provided' in response.data

    def test_upload_non_docx(self, logged_in_client):
        """Upload with non-DOCX file should return error."""
        data = {
            'file': (BytesIO(b'not a docx'), 'test.txt')
        }
        response = logged_in_client.post('/books/upload', data=data,
                                         content_type='multipart/form-data',
                                         follow_redirects=True)
        assert response.status_code == 200
        assert b'Please upload a DOCX file' in response.data

    def test_upload_success(self, logged_in_client, app):
        """Upload valid DOCX should create book."""
        docx_path = FIXTURES_DIR / 'simple.docx'
        with open(docx_path, 'rb') as f:
            data = {
                'file': (f, 'simple.docx')
            }
            response = logged_in_client.post('/books/upload', data=data,
                                             content_type='multipart/form-data',
                                             follow_redirects=True)

        assert response.status_code == 200
        assert b'uploaded successfully' in response.data

        # Verify book was created
        with app.app_context():
            from app.models import Book
            book = Book.query.first()
            assert book is not None
            assert book.status == 'draft'

    def test_upload_auto_title(self, logged_in_client, app):
        """Upload without title should auto-generate from filename."""
        docx_path = FIXTURES_DIR / 'simple.docx'
        with open(docx_path, 'rb') as f:
            data = {
                'file': (f, 'my_test_book.docx')
            }
            response = logged_in_client.post('/books/upload', data=data,
                                             content_type='multipart/form-data',
                                             follow_redirects=True)

        assert response.status_code == 200

        with app.app_context():
            from app.models import Book
            book = Book.query.first()
            assert book is not None
            assert 'My Test Book' in book.title

    def test_upload_with_title_author(self, logged_in_client, app):
        """Upload with title and author should use provided values."""
        docx_path = FIXTURES_DIR / 'simple.docx'
        with open(docx_path, 'rb') as f:
            data = {
                'file': (f, 'simple.docx'),
                'title': 'Custom Title',
                'author': 'Test Author'
            }
            response = logged_in_client.post('/books/upload', data=data,
                                             content_type='multipart/form-data',
                                             follow_redirects=True)

        assert response.status_code == 200

        with app.app_context():
            from app.models import Book
            book = Book.query.first()
            assert book is not None
            assert book.title == 'Custom Title'
            assert book.author == 'Test Author'

    def test_upload_creates_chapters(self, logged_in_client, app):
        """Upload should create chapters from DOCX structure."""
        docx_path = FIXTURES_DIR / 'with_headings.docx'
        with open(docx_path, 'rb') as f:
            data = {
                'file': (f, 'with_headings.docx'),
                'title': 'Book With Chapters'
            }
            response = logged_in_client.post('/books/upload', data=data,
                                             content_type='multipart/form-data',
                                             follow_redirects=True)

        assert response.status_code == 200

        with app.app_context():
            from app.models import Book, Chapter
            book = Book.query.first()
            assert book is not None
            chapters = Chapter.query.filter_by(book_id=book.id).all()
            assert len(chapters) >= 1

    def test_upload_creates_paragraphs(self, logged_in_client, app):
        """Upload should create paragraphs from DOCX content."""
        docx_path = FIXTURES_DIR / 'simple.docx'
        with open(docx_path, 'rb') as f:
            data = {
                'file': (f, 'simple.docx'),
                'title': 'Book With Paragraphs'
            }
            response = logged_in_client.post('/books/upload', data=data,
                                             content_type='multipart/form-data',
                                             follow_redirects=True)

        assert response.status_code == 200

        with app.app_context():
            from app.models import Book, Paragraph
            book = Book.query.first()
            assert book is not None
            # Get paragraphs through chapters
            total_paragraphs = 0
            for chapter in book.chapters:
                total_paragraphs += chapter.paragraphs.count()
            assert total_paragraphs >= 1

    def test_duplicate_title_creates_unique_slug(self, logged_in_client, app):
        """Upload with duplicate title should create unique slug."""
        docx_path = FIXTURES_DIR / 'simple.docx'

        # Upload first book
        with open(docx_path, 'rb') as f:
            data = {
                'file': (f, 'simple.docx'),
                'title': 'Same Title'
            }
            logged_in_client.post('/books/upload', data=data,
                                  content_type='multipart/form-data')

        # Upload second book with same title
        with open(docx_path, 'rb') as f:
            data = {
                'file': (f, 'simple.docx'),
                'title': 'Same Title'
            }
            logged_in_client.post('/books/upload', data=data,
                                  content_type='multipart/form-data')

        with app.app_context():
            from app.models import Book
            books = Book.query.all()
            assert len(books) == 2
            slugs = [b.slug for b in books]
            assert len(set(slugs)) == 2  # Unique slugs


class TestPDFUpload:
    """Test PDF upload functionality."""

    def test_upload_with_pdf(self, logged_in_client, app):
        """Upload DOCX with PDF should save both and set pdf_path."""
        docx_path = FIXTURES_DIR / 'simple.docx'
        pdf_path = FIXTURES_DIR / 'simple.pdf'

        with open(docx_path, 'rb') as docx_f, open(pdf_path, 'rb') as pdf_f:
            data = {
                'file': (docx_f, 'simple.docx'),
                'pdf_file': (pdf_f, 'simple.pdf'),
                'title': 'Book With PDF'
            }
            response = logged_in_client.post('/books/upload', data=data,
                                             content_type='multipart/form-data',
                                             follow_redirects=True)

        assert response.status_code == 200
        assert b'uploaded successfully' in response.data

        with app.app_context():
            from app.models import Book
            book = Book.query.first()
            assert book is not None
            assert book.pdf_path is not None
            assert 'simple.pdf' in book.pdf_path

    def test_upload_pdf_only_fails(self, logged_in_client):
        """Upload PDF without DOCX should fail."""
        pdf_path = FIXTURES_DIR / 'simple.pdf'

        with open(pdf_path, 'rb') as f:
            data = {
                'file': (f, 'simple.pdf')
            }
            response = logged_in_client.post('/books/upload', data=data,
                                             content_type='multipart/form-data',
                                             follow_redirects=True)

        assert response.status_code == 200
        assert b'Please upload a DOCX file' in response.data

    def test_upload_invalid_pdf_extension(self, logged_in_client):
        """Upload with wrong PDF extension should fail."""
        docx_path = FIXTURES_DIR / 'simple.docx'

        with open(docx_path, 'rb') as docx_f:
            data = {
                'file': (docx_f, 'simple.docx'),
                'pdf_file': (BytesIO(b'fake pdf'), 'document.txt')
            }
            response = logged_in_client.post('/books/upload', data=data,
                                             content_type='multipart/form-data',
                                             follow_redirects=True)

        assert response.status_code == 200
        assert b'PDF file must have .pdf extension' in response.data

    def test_upload_docx_only_no_pdf_path(self, logged_in_client, app):
        """Upload DOCX without PDF should have null pdf_path."""
        docx_path = FIXTURES_DIR / 'simple.docx'

        with open(docx_path, 'rb') as f:
            data = {
                'file': (f, 'simple.docx'),
                'title': 'Book Without PDF'
            }
            response = logged_in_client.post('/books/upload', data=data,
                                             content_type='multipart/form-data',
                                             follow_redirects=True)

        assert response.status_code == 200

        with app.app_context():
            from app.models import Book
            book = Book.query.first()
            assert book is not None
            assert book.pdf_path is None
