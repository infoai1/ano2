"""Tests for database models."""
import pytest
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app():
    """Create test Flask app with in-memory database."""
    from app import create_app
    app = create_app(testing=True)
    with app.app_context():
        from app.models import db
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def db_session(app):
    """Get database session."""
    from app.models import db
    with app.app_context():
        yield db.session


class TestUserModel:
    """Test User model."""

    def test_create_user(self, app):
        """Can create a user."""
        from app.models import db, User
        with app.app_context():
            user = User(username='testuser', role='admin')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.username == 'testuser'
            assert user.role == 'admin'

    def test_password_hashing(self, app):
        """Password should be hashed, not stored plain."""
        from app.models import db, User
        with app.app_context():
            user = User(username='hashtest')
            user.set_password('mypassword')
            db.session.add(user)
            db.session.commit()

            assert user.password_hash != 'mypassword'
            assert user.check_password('mypassword')
            assert not user.check_password('wrongpassword')

    def test_user_created_at(self, app):
        """User should have created_at timestamp."""
        from app.models import db, User
        with app.app_context():
            user = User(username='timestamp_test')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()

            assert user.created_at is not None
            assert isinstance(user.created_at, datetime)


class TestBookModel:
    """Test Book model."""

    def test_create_book(self, app):
        """Can create a book."""
        from app.models import db, Book
        with app.app_context():
            book = Book(
                title='Peace in Kashmir',
                author='Maulana Wahiduddin Khan',
                slug='peace-in-kashmir'
            )
            db.session.add(book)
            db.session.commit()

            assert book.id is not None
            assert book.title == 'Peace in Kashmir'
            assert book.slug == 'peace-in-kashmir'

    def test_book_status_default(self, app):
        """Book status should default to 'draft'."""
        from app.models import db, Book
        with app.app_context():
            book = Book(title='Test', slug='test')
            db.session.add(book)
            db.session.commit()

            assert book.status == 'draft'

    def test_book_locking(self, app):
        """Book should support locking."""
        from app.models import db, Book, User
        with app.app_context():
            user = User(username='locker')
            user.set_password('pass')
            book = Book(title='Lockable', slug='lockable')
            db.session.add_all([user, book])
            db.session.commit()

            book.locked_by = user.id
            db.session.commit()

            assert book.locked_by == user.id


class TestChapterModel:
    """Test Chapter model."""

    def test_create_chapter(self, app):
        """Can create a chapter linked to a book."""
        from app.models import db, Book, Chapter
        with app.app_context():
            book = Book(title='Test Book', slug='test-book')
            db.session.add(book)
            db.session.commit()

            chapter = Chapter(
                book_id=book.id,
                title='Introduction',
                order_index=1
            )
            db.session.add(chapter)
            db.session.commit()

            assert chapter.id is not None
            assert chapter.book_id == book.id
            assert chapter.order_index == 1


class TestParagraphModel:
    """Test Paragraph model."""

    def test_create_paragraph(self, app):
        """Can create a paragraph."""
        from app.models import db, Book, Chapter, Paragraph
        with app.app_context():
            book = Book(title='Test', slug='test')
            db.session.add(book)
            db.session.commit()

            chapter = Chapter(book_id=book.id, title='Ch1', order_index=1)
            db.session.add(chapter)
            db.session.commit()

            para = Paragraph(
                chapter_id=chapter.id,
                text='This is a test paragraph.',
                type='paragraph',
                order_index=1
            )
            db.session.add(para)
            db.session.commit()

            assert para.id is not None
            assert para.text == 'This is a test paragraph.'

    def test_paragraph_page_info(self, app):
        """Paragraph should store page number."""
        from app.models import db, Book, Chapter, Paragraph
        with app.app_context():
            book = Book(title='Test', slug='test')
            chapter = Chapter(book_id=1, title='Ch1', order_index=1)
            db.session.add(book)
            db.session.commit()
            chapter.book_id = book.id
            db.session.add(chapter)
            db.session.commit()

            para = Paragraph(
                chapter_id=chapter.id,
                text='Text on page 42',
                type='paragraph',
                order_index=1,
                page_number=42
            )
            db.session.add(para)
            db.session.commit()

            assert para.page_number == 42

    def test_paragraph_reviewed_flag(self, app):
        """Paragraph should have reviewed flag."""
        from app.models import db, Book, Chapter, Paragraph
        with app.app_context():
            book = Book(title='Test', slug='test')
            db.session.add(book)
            db.session.commit()

            chapter = Chapter(book_id=book.id, title='Ch1', order_index=1)
            db.session.add(chapter)
            db.session.commit()

            para = Paragraph(
                chapter_id=chapter.id,
                text='Review me',
                type='paragraph',
                order_index=1
            )
            db.session.add(para)
            db.session.commit()

            assert para.reviewed is False
            para.reviewed = True
            db.session.commit()
            assert para.reviewed is True


class TestGroupModel:
    """Test Group model."""

    def test_create_group(self, app):
        """Can create a group."""
        from app.models import db, Book, Group
        with app.app_context():
            book = Book(title='Test', slug='test')
            db.session.add(book)
            db.session.commit()

            group = Group(
                book_id=book.id,
                token_count=650,
                order_index=1
            )
            db.session.add(group)
            db.session.commit()

            assert group.id is not None
            assert group.token_count == 650


class TestReferenceModel:
    """Test Reference model."""

    def test_create_quran_reference(self, app):
        """Can create a Quran reference."""
        from app.models import db, Book, Chapter, Paragraph, Reference
        with app.app_context():
            book = Book(title='Test', slug='test')
            db.session.add(book)
            db.session.commit()

            chapter = Chapter(book_id=book.id, title='Ch1', order_index=1)
            db.session.add(chapter)
            db.session.commit()

            para = Paragraph(
                chapter_id=chapter.id,
                text='See Quran 2:255',
                type='paragraph',
                order_index=1
            )
            db.session.add(para)
            db.session.commit()

            ref = Reference(
                paragraph_id=para.id,
                ref_type='quran',
                surah=2,
                ayah_start=255,
                auto_detected=True
            )
            db.session.add(ref)
            db.session.commit()

            assert ref.id is not None
            assert ref.ref_type == 'quran'
            assert ref.surah == 2

    def test_create_hadith_reference(self, app):
        """Can create a Hadith reference."""
        from app.models import db, Book, Chapter, Paragraph, Reference
        with app.app_context():
            book = Book(title='Test', slug='test')
            db.session.add(book)
            db.session.commit()

            chapter = Chapter(book_id=book.id, title='Ch1', order_index=1)
            db.session.add(chapter)
            db.session.commit()

            para = Paragraph(
                chapter_id=chapter.id,
                text='Bukhari 1234',
                type='paragraph',
                order_index=1
            )
            db.session.add(para)
            db.session.commit()

            ref = Reference(
                paragraph_id=para.id,
                ref_type='hadith',
                collection='bukhari',
                hadith_number='1234',
                auto_detected=True
            )
            db.session.add(ref)
            db.session.commit()

            assert ref.ref_type == 'hadith'
            assert ref.collection == 'bukhari'


class TestVersionModel:
    """Test Version model."""

    def test_create_version(self, app):
        """Can create a version snapshot."""
        from app.models import db, Book, User, Version
        with app.app_context():
            user = User(username='snapper')
            user.set_password('pass')
            book = Book(title='Test', slug='test')
            db.session.add_all([user, book])
            db.session.commit()

            version = Version(
                book_id=book.id,
                snapshot='{"paragraphs": []}',
                version_type='auto',
                created_by=user.id
            )
            db.session.add(version)
            db.session.commit()

            assert version.id is not None
            assert version.version_type == 'auto'
