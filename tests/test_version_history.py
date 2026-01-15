"""Tests for version history save and restore."""
import pytest
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.models import db, User, Book, Chapter, Paragraph, Version


@pytest.fixture
def app():
    """Create test application."""
    app = create_app(testing=True)
    with app.app_context():
        db.create_all()
        # Create test user
        user = User(username='testuser', role='admin')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()
    yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """Create authenticated test client."""
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    return client


@pytest.fixture
def sample_book(app):
    """Create a sample book with chapters and paragraphs."""
    with app.app_context():
        book = Book(title='Test Book', slug='test-book', author='Test Author')
        db.session.add(book)
        db.session.flush()

        chapter = Chapter(book_id=book.id, title='Chapter 1', order_index=0)
        db.session.add(chapter)
        db.session.flush()

        para1 = Paragraph(chapter_id=chapter.id, text='First paragraph.', order_index=0)
        para2 = Paragraph(chapter_id=chapter.id, text='Second paragraph.', order_index=1)
        db.session.add_all([para1, para2])
        db.session.commit()

        return book.slug


class TestCreateVersion:
    """Test version creation."""

    def test_create_version_manual(self, auth_client, sample_book, app):
        """Manual version should be created via API."""
        response = auth_client.post(f'/api/book/{sample_book}/version')
        assert response.status_code == 200

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            versions = Version.query.filter_by(book_id=book.id).all()
            assert len(versions) == 1
            assert versions[0].version_type == 'manual'

    def test_create_version_auto(self, auth_client, sample_book, app):
        """Auto version can be created with type parameter."""
        response = auth_client.post(f'/api/book/{sample_book}/version',
                                     data={'type': 'auto'})
        assert response.status_code == 200

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            assert version.version_type == 'auto'

    def test_version_snapshot_is_json(self, auth_client, sample_book, app):
        """Version snapshot should be valid JSON."""
        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            # Should not raise
            snapshot = json.loads(version.snapshot)
            assert isinstance(snapshot, dict)

    def test_version_snapshot_contains_book_data(self, auth_client, sample_book, app):
        """Version snapshot should contain book metadata."""
        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            snapshot = json.loads(version.snapshot)

            assert snapshot['title'] == 'Test Book'
            assert snapshot['author'] == 'Test Author'

    def test_version_snapshot_contains_chapters(self, auth_client, sample_book, app):
        """Version snapshot should contain chapters."""
        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            snapshot = json.loads(version.snapshot)

            assert 'chapters' in snapshot
            assert len(snapshot['chapters']) == 1
            assert snapshot['chapters'][0]['title'] == 'Chapter 1'

    def test_version_snapshot_contains_paragraphs(self, auth_client, sample_book, app):
        """Version snapshot should contain paragraphs."""
        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            snapshot = json.loads(version.snapshot)

            assert 'chapters' in snapshot
            assert 'paragraphs' in snapshot['chapters'][0]
            assert len(snapshot['chapters'][0]['paragraphs']) == 2

    def test_version_has_created_by(self, auth_client, sample_book, app):
        """Version should track who created it."""
        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            assert version.created_by is not None


class TestListVersions:
    """Test version listing."""

    def test_list_versions_empty(self, auth_client, sample_book):
        """Book with no versions should return empty list."""
        response = auth_client.get(f'/api/book/{sample_book}/versions')
        assert response.status_code == 200
        data = response.get_json()
        assert data['versions'] == []

    def test_list_versions_returns_all(self, auth_client, sample_book, app):
        """Should list all versions for a book."""
        # Create multiple versions
        auth_client.post(f'/api/book/{sample_book}/version')
        auth_client.post(f'/api/book/{sample_book}/version')
        auth_client.post(f'/api/book/{sample_book}/version')

        response = auth_client.get(f'/api/book/{sample_book}/versions')
        data = response.get_json()
        assert len(data['versions']) == 3

    def test_list_versions_ordered_by_date(self, auth_client, sample_book, app):
        """Versions should be ordered by creation date."""
        auth_client.post(f'/api/book/{sample_book}/version')
        auth_client.post(f'/api/book/{sample_book}/version')

        response = auth_client.get(f'/api/book/{sample_book}/versions')
        data = response.get_json()

        # Most recent first
        assert data['versions'][0]['id'] > data['versions'][1]['id']


class TestRestoreVersion:
    """Test version restoration."""

    def test_restore_version_success(self, auth_client, sample_book, app):
        """Restoring a version should update paragraphs."""
        # Create version
        auth_client.post(f'/api/book/{sample_book}/version')

        # Get version ID
        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            version_id = version.id

        # Modify a paragraph
        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            chapter = book.chapters.first()
            para = chapter.paragraphs.first()
            para.text = 'Modified text!'
            db.session.commit()

        # Restore
        response = auth_client.post(f'/api/version/{version_id}/restore')
        assert response.status_code == 200

        # Check restoration
        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            chapter = book.chapters.first()
            para = chapter.paragraphs.first()
            assert para.text == 'First paragraph.'

    def test_restore_creates_backup(self, auth_client, sample_book, app):
        """Restoring should create a backup version first."""
        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            version_id = version.id
            initial_count = Version.query.filter_by(book_id=book.id).count()

        auth_client.post(f'/api/version/{version_id}/restore')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            final_count = Version.query.filter_by(book_id=book.id).count()
            # One more version (backup before restore)
            assert final_count == initial_count + 1

    def test_restore_invalid_version_404(self, auth_client):
        """Restoring non-existent version should 404."""
        response = auth_client.post('/api/version/99999/restore')
        assert response.status_code == 404

    def test_restore_returns_message(self, auth_client, sample_book, app):
        """Restore should return success message."""
        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            version_id = version.id

        response = auth_client.post(f'/api/version/{version_id}/restore')
        data = response.get_json()
        assert 'restored' in data.get('message', '').lower() or data.get('status') == 'ok'


class TestDeleteVersion:
    """Test version deletion."""

    def test_delete_version_success(self, auth_client, sample_book, app):
        """Should be able to delete a version."""
        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            version_id = version.id

        response = auth_client.delete(f'/api/version/{version_id}')
        assert response.status_code == 200

        with app.app_context():
            version = Version.query.get(version_id)
            assert version is None

    def test_delete_invalid_version_404(self, auth_client):
        """Deleting non-existent version should 404."""
        response = auth_client.delete('/api/version/99999')
        assert response.status_code == 404


class TestVersionContent:
    """Test version snapshot content."""

    def test_snapshot_preserves_paragraph_types(self, auth_client, sample_book, app):
        """Snapshot should preserve paragraph types."""
        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            chapter = book.chapters.first()
            para = chapter.paragraphs.first()
            para.type = 'heading'
            db.session.commit()

        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            snapshot = json.loads(version.snapshot)
            para_type = snapshot['chapters'][0]['paragraphs'][0]['type']
            assert para_type == 'heading'

    def test_snapshot_preserves_page_numbers(self, auth_client, sample_book, app):
        """Snapshot should preserve page numbers."""
        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            chapter = book.chapters.first()
            para = chapter.paragraphs.first()
            para.page_number = 42
            db.session.commit()

        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            snapshot = json.loads(version.snapshot)
            page = snapshot['chapters'][0]['paragraphs'][0].get('page_number')
            assert page == 42

    def test_restore_preserves_paragraph_order(self, auth_client, sample_book, app):
        """Restored paragraphs should maintain order."""
        auth_client.post(f'/api/book/{sample_book}/version')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            version = Version.query.filter_by(book_id=book.id).first()
            version_id = version.id

        auth_client.post(f'/api/version/{version_id}/restore')

        with app.app_context():
            book = Book.query.filter_by(slug=sample_book).first()
            chapter = book.chapters.first()
            paragraphs = chapter.paragraphs.order_by(Paragraph.order_index).all()
            assert paragraphs[0].order_index < paragraphs[1].order_index

