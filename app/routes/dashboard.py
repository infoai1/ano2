"""Dashboard routes."""
import re
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models import db, Book, Chapter, Paragraph
from app.config import get_logger, UPLOADS_DIR
from app.services.docx_parser import parse_docx

bp = Blueprint('dashboard', __name__)
logger = get_logger()


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:100]


@bp.route('/')
@bp.route('/dashboard')
@login_required
def index():
    """Show dashboard with book list."""
    books = Book.query.order_by(Book.updated_at.desc()).all()
    logger.info("dashboard_viewed", user=current_user.username, book_count=len(books))
    return render_template('dashboard.html', books=books, user=current_user)


@bp.route('/books/upload', methods=['POST'])
@login_required
def upload_book():
    """Upload and parse a DOCX file to create a new book.

    Expects multipart form with:
        - file: The DOCX file
        - title: Book title
        - author: Book author (optional)

    Returns:
        Redirect to dashboard on success, or back with error
    """
    if 'file' not in request.files:
        flash('No file provided', 'error')
        return redirect(url_for('dashboard.index'))

    file = request.files['file']
    if not file.filename or not file.filename.endswith('.docx'):
        flash('Please upload a DOCX file', 'error')
        return redirect(url_for('dashboard.index'))

    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()

    if not title:
        title = Path(file.filename).stem.replace('-', ' ').replace('_', ' ').title()

    # Create slug and ensure uniqueness
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while Book.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Save the file
    filename = secure_filename(file.filename)
    upload_path = UPLOADS_DIR / f"{slug}_{filename}"
    file.save(upload_path)

    try:
        # Parse the DOCX
        result = parse_docx(upload_path)

        # Create the book
        book = Book(
            title=title,
            author=author or None,
            slug=slug,
            docx_path=str(upload_path),
            status='draft'
        )
        db.session.add(book)
        db.session.commit()

        # Create chapters and paragraphs
        for chapter_data in result['chapters']:
            chapter = Chapter(
                book_id=book.id,
                title=chapter_data['title'],
                order_index=chapter_data['order_index']
            )
            db.session.add(chapter)
            db.session.commit()

            # Add paragraphs for this chapter
            for para_idx in chapter_data['paragraph_indices']:
                para_data = result['paragraphs'][para_idx]
                para = Paragraph(
                    chapter_id=chapter.id,
                    text=para_data['text'],
                    type=para_data['type'],
                    level=para_data.get('level', 1),
                    order_index=para_data['order_index']
                )
                db.session.add(para)

            db.session.commit()

        logger.info("book_uploaded",
                    book_slug=slug,
                    title=title,
                    paragraph_count=len(result['paragraphs']),
                    chapter_count=len(result['chapters']),
                    user=current_user.username)

        flash(f'Book "{title}" uploaded successfully', 'success')

    except Exception as e:
        logger.error("book_upload_failed",
                     filename=filename,
                     error=str(e),
                     user=current_user.username)
        flash(f'Error parsing file: {str(e)}', 'error')
        # Clean up on failure
        if upload_path.exists():
            upload_path.unlink()

    return redirect(url_for('dashboard.index'))
