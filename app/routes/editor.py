"""Editor routes for book annotation."""
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app.models import db, Book, Chapter, Paragraph, Group
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


@bp.route('/editor/<slug>/groups')
@login_required
def groups_view(slug):
    """View book organized by groups.

    Args:
        slug: The book's URL slug

    Returns:
        Rendered groups template
    """
    book = Book.query.filter_by(slug=slug).first()
    if not book:
        abort(404)

    # Get all groups with their paragraphs
    groups = Group.query.filter_by(book_id=book.id).order_by(Group.order_index).all()

    groups_data = []
    for group in groups:
        paragraphs = Paragraph.query.filter_by(
            group_id=group.id,
            deleted=False
        ).order_by(Paragraph.order_index).all()
        groups_data.append({
            'group': group,
            'paragraphs': paragraphs
        })

    # Also get ungrouped paragraphs
    ungrouped = []
    for chapter in book.chapters.all():
        paras = Paragraph.query.filter_by(
            chapter_id=chapter.id,
            group_id=None,
            deleted=False
        ).order_by(Paragraph.order_index).all()
        ungrouped.extend(paras)

    logger.info("groups_view",
                book_slug=slug,
                user=current_user.username,
                group_count=len(groups))

    return render_template('groups.html',
                           book=book,
                           groups_data=groups_data,
                           ungrouped=ungrouped,
                           user=current_user)


@bp.route('/editor/<slug>/paragraphs')
@login_required
def paragraphs_view(slug):
    """View all paragraphs in a flat list.

    Args:
        slug: The book's URL slug

    Returns:
        Rendered paragraphs template
    """
    book = Book.query.filter_by(slug=slug).first()
    if not book:
        abort(404)

    # Get all paragraphs across all chapters
    paragraphs = []
    for chapter in book.chapters.order_by(Chapter.order_index).all():
        paras = Paragraph.query.filter_by(
            chapter_id=chapter.id,
            deleted=False
        ).order_by(Paragraph.order_index).all()
        for para in paras:
            paragraphs.append({
                'para': para,
                'chapter': chapter
            })

    logger.info("paragraphs_view",
                book_slug=slug,
                user=current_user.username,
                paragraph_count=len(paragraphs))

    return render_template('paragraphs.html',
                           book=book,
                           paragraphs=paragraphs,
                           user=current_user)
