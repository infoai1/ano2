"""Database models for Annotation Tool v2."""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(20), default='annotator')  # admin, annotator, reviewer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Book(db.Model):
    """Book model for uploaded documents."""
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft, in_progress, review, approved
    locked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    locked_at = db.Column(db.DateTime, nullable=True)
    docx_path = db.Column(db.String(500), nullable=True)
    pdf_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    chapters = db.relationship('Chapter', backref='book', lazy='dynamic', cascade='all, delete-orphan')
    groups = db.relationship('Group', backref='book', lazy='dynamic', cascade='all, delete-orphan')
    versions = db.relationship('Version', backref='book', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Book {self.slug}>'


class Chapter(db.Model):
    """Chapter model for book structure."""
    __tablename__ = 'chapters'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    title = db.Column(db.String(300), nullable=True)
    order_index = db.Column(db.Integer, nullable=False)

    # Relationships
    paragraphs = db.relationship('Paragraph', backref='chapter', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Chapter {self.title}>'


class Paragraph(db.Model):
    """Paragraph model for text content."""
    __tablename__ = 'paragraphs'

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(30), default='paragraph')  # paragraph, heading, subheading, quote
    level = db.Column(db.Integer, default=1)  # 1-3 for heading levels
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    page_number = db.Column(db.Integer, nullable=True)
    page_confidence = db.Column(db.Float, nullable=True)
    reviewed = db.Column(db.Boolean, default=False)
    deleted = db.Column(db.Boolean, default=False)
    order_index = db.Column(db.Integer, nullable=False)

    # Relationships
    references = db.relationship('Reference', backref='paragraph', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Paragraph {self.id}>'


class Group(db.Model):
    """Group model for token-based grouping."""
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    token_count = db.Column(db.Integer, default=0)
    order_index = db.Column(db.Integer, nullable=False)

    # Relationships
    paragraphs = db.relationship('Paragraph', backref='group', lazy='dynamic')

    def __repr__(self):
        return f'<Group {self.id} ({self.token_count} tokens)>'


class Reference(db.Model):
    """Reference model for Quran/Hadith citations."""
    __tablename__ = 'references'

    id = db.Column(db.Integer, primary_key=True)
    paragraph_id = db.Column(db.Integer, db.ForeignKey('paragraphs.id'), nullable=False)
    ref_type = db.Column(db.String(20), nullable=False)  # quran, hadith, footnote

    # Quran fields
    surah = db.Column(db.Integer, nullable=True)
    ayah_start = db.Column(db.Integer, nullable=True)
    ayah_end = db.Column(db.Integer, nullable=True)
    surah_name = db.Column(db.String(50), nullable=True)

    # Hadith fields
    collection = db.Column(db.String(50), nullable=True)  # bukhari, muslim, etc.
    hadith_number = db.Column(db.String(50), nullable=True)

    # Common fields
    verified = db.Column(db.Boolean, default=False)
    auto_detected = db.Column(db.Boolean, default=True)
    raw_text = db.Column(db.String(500), nullable=True)  # Original text that triggered detection

    def __repr__(self):
        return f'<Reference {self.ref_type}:{self.id}>'


class Version(db.Model):
    """Version model for snapshots."""
    __tablename__ = 'versions'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    snapshot = db.Column(db.Text, nullable=False)  # JSON blob
    version_type = db.Column(db.String(20), default='auto')  # auto, manual
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Version {self.id} ({self.version_type})>'
