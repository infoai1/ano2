"""Editor routes for book annotation."""
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.models import db, Book, Chapter, Paragraph
from app.config import get_logger

bp = Blueprint('editor', __name__)
logger = get_logger()


@bp.route('/editor/<slug>')
@login_required
def edit(slug):
    """Edit a book's annotations.

    Args:
        slug: The book's URL slug

    Returns:
        Rendered editor template with book data
    """
    book = Book.query.filter_by(slug=slug).first()
    if not book:
        logger.warning("book_not_found", slug=slug, user=current_user.username)
        abort(404)

    # Get all chapters with their paragraphs (excluding soft-deleted)
    chapters = Chapter.query.filter_by(book_id=book.id).order_by(Chapter.order_index).all()

    chapters_data = []
    for chapter in chapters:
        paragraphs = Paragraph.query.filter_by(
            chapter_id=chapter.id,
            deleted=False
        ).order_by(Paragraph.order_index).all()
        chapters_data.append({
            'chapter': chapter,
            'paragraphs': paragraphs
        })

    logger.info("editor_viewed",
                book_slug=slug,
                user=current_user.username,
                chapter_count=len(chapters),
                paragraph_count=sum(len(c['paragraphs']) for c in chapters_data))

    return render_template('editor.html',
                           book=book,
                           chapters_data=chapters_data,
                           user=current_user)
