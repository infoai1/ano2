"""API routes for HTMX endpoints."""
import json
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user

from flask import Response

from app.models import db, Book, Chapter, Paragraph, Version, Reference, Group
from app.config import get_logger
from app.services.exporter import export_book_json, export_lightrag_json

bp = Blueprint('api', __name__, url_prefix='/api')
logger = get_logger()

VALID_PARAGRAPH_TYPES = {'paragraph', 'heading', 'subheading', 'quote'}


@bp.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'ok'}


@bp.route('/paragraph/<int:para_id>/type', methods=['POST'])
@login_required
def update_paragraph_type(para_id):
    """Update a paragraph's type.

    Args:
        para_id: Paragraph ID

    Returns:
        Updated paragraph HTML fragment or error
    """
    para = Paragraph.query.get_or_404(para_id)
    new_type = request.form.get('type', '').strip()

    if new_type not in VALID_PARAGRAPH_TYPES:
        logger.warning("invalid_paragraph_type",
                       para_id=para_id,
                       attempted_type=new_type,
                       user=current_user.username)
        return jsonify({'error': 'Invalid paragraph type'}), 400

    old_type = para.type
    para.type = new_type
    db.session.commit()

    logger.info("paragraph_type_updated",
                para_id=para_id,
                old_type=old_type,
                new_type=new_type,
                user=current_user.username)

    # Return the updated paragraph card for HTMX
    return render_template('components/paragraph.html', para=para)


@bp.route('/paragraph/<int:para_id>/page', methods=['POST'])
@login_required
def update_paragraph_page(para_id):
    """Update a paragraph's page number manually.

    Args:
        para_id: Paragraph ID

    Returns:
        Updated paragraph HTML
    """
    para = Paragraph.query.get_or_404(para_id)
    page_str = request.form.get('page', '').strip()

    if page_str:
        try:
            para.page_number = int(page_str)
            para.page_confidence = 1.0  # Manual = 100% confidence
        except ValueError:
            return jsonify({'error': 'Invalid page number'}), 400
    else:
        para.page_number = None
        para.page_confidence = None

    db.session.commit()

    logger.info("paragraph_page_updated",
                para_id=para_id,
                page_number=para.page_number,
                user=current_user.username)

    return render_template('components/paragraph.html', para=para)


@bp.route('/paragraph/<int:para_id>/text', methods=['POST'])
@login_required
def update_paragraph_text(para_id):
    """Update a paragraph's text content.

    Args:
        para_id: Paragraph ID

    Returns:
        Success response or error
    """
    para = Paragraph.query.get_or_404(para_id)
    new_text = request.form.get('text', '').strip()

    if not new_text:
        logger.warning("empty_paragraph_text",
                       para_id=para_id,
                       user=current_user.username)
        return jsonify({'error': 'Text cannot be empty'}), 400

    para.text = new_text
    db.session.commit()

    logger.info("paragraph_text_updated",
                para_id=para_id,
                text_length=len(new_text),
                user=current_user.username)

    return jsonify({'status': 'ok', 'para_id': para_id})


@bp.route('/paragraph/<int:para_id>', methods=['DELETE'])
@login_required
def delete_paragraph(para_id):
    """Soft-delete a paragraph.

    Args:
        para_id: Paragraph ID

    Returns:
        Empty response for HTMX to remove the element
    """
    para = Paragraph.query.get_or_404(para_id)
    para.deleted = True
    db.session.commit()

    logger.info("paragraph_deleted",
                para_id=para_id,
                user=current_user.username)

    # Return empty string so HTMX removes the element
    return ''


@bp.route('/book/<slug>/save', methods=['POST'])
@login_required
def save_book(slug):
    """Save book (update timestamp).

    This endpoint is called when the user explicitly saves.
    Individual changes are auto-saved, but this updates the book's
    updated_at timestamp for tracking purposes.

    Args:
        slug: Book slug

    Returns:
        Success response
    """
    book = Book.query.filter_by(slug=slug).first_or_404()
    book.updated_at = datetime.utcnow()
    db.session.commit()

    logger.info("book_saved",
                book_slug=slug,
                user=current_user.username)

    return jsonify({'status': 'ok', 'message': 'Book saved'})


def _create_book_snapshot(book):
    """Create a JSON snapshot of a book's current state.

    Args:
        book: Book model instance

    Returns:
        Dict containing complete book state
    """
    snapshot = {
        'title': book.title,
        'author': book.author,
        'slug': book.slug,
        'status': book.status,
        'chapters': []
    }

    for chapter in book.chapters.order_by(Chapter.order_index).all():
        chapter_data = {
            'title': chapter.title,
            'order_index': chapter.order_index,
            'paragraphs': []
        }

        for para in chapter.paragraphs.filter_by(deleted=False).order_by(Paragraph.order_index).all():
            para_data = {
                'text': para.text,
                'type': para.type,
                'level': para.level,
                'page_number': para.page_number,
                'page_confidence': para.page_confidence,
                'reviewed': para.reviewed,
                'order_index': para.order_index,
            }
            chapter_data['paragraphs'].append(para_data)

        snapshot['chapters'].append(chapter_data)

    return snapshot


def _restore_book_from_snapshot(book, snapshot):
    """Restore a book's state from a snapshot.

    Args:
        book: Book model instance
        snapshot: Dict containing book state
    """
    # Update book metadata
    book.title = snapshot.get('title', book.title)
    book.author = snapshot.get('author', book.author)
    book.status = snapshot.get('status', book.status)

    # Delete existing chapters and paragraphs
    for chapter in book.chapters.all():
        for para in chapter.paragraphs.all():
            db.session.delete(para)
        db.session.delete(chapter)

    db.session.flush()

    # Recreate chapters and paragraphs
    for chapter_data in snapshot.get('chapters', []):
        chapter = Chapter(
            book_id=book.id,
            title=chapter_data.get('title'),
            order_index=chapter_data.get('order_index', 0)
        )
        db.session.add(chapter)
        db.session.flush()

        for para_data in chapter_data.get('paragraphs', []):
            para = Paragraph(
                chapter_id=chapter.id,
                text=para_data.get('text', ''),
                type=para_data.get('type', 'paragraph'),
                level=para_data.get('level', 1),
                page_number=para_data.get('page_number'),
                page_confidence=para_data.get('page_confidence'),
                reviewed=para_data.get('reviewed', False),
                order_index=para_data.get('order_index', 0),
                deleted=False
            )
            db.session.add(para)


@bp.route('/book/<slug>/version', methods=['POST'])
@login_required
def create_version(slug):
    """Create a version snapshot for a book.

    Args:
        slug: Book slug

    Returns:
        Success response with version ID
    """
    book = Book.query.filter_by(slug=slug).first_or_404()
    version_type = request.form.get('type', 'manual')

    snapshot = _create_book_snapshot(book)

    version = Version(
        book_id=book.id,
        snapshot=json.dumps(snapshot, ensure_ascii=False),
        version_type=version_type,
        created_by=current_user.id
    )
    db.session.add(version)
    db.session.commit()

    logger.info("version_created",
                book_slug=slug,
                version_id=version.id,
                version_type=version_type,
                user=current_user.username)

    return jsonify({
        'status': 'ok',
        'version_id': version.id,
        'message': 'Version created'
    })


@bp.route('/book/<slug>/versions', methods=['GET'])
@login_required
def list_versions(slug):
    """List all versions for a book.

    Args:
        slug: Book slug

    Returns:
        HTML list of versions (for HTMX) or JSON
    """
    book = Book.query.filter_by(slug=slug).first_or_404()

    versions = Version.query.filter_by(book_id=book.id)\
        .order_by(Version.created_at.desc()).all()

    # Return JSON for API clients
    if request.headers.get('Accept') == 'application/json' or 'HX-Request' not in request.headers:
        version_list = []
        for v in versions:
            version_list.append({
                'id': v.id,
                'version_type': v.version_type,
                'created_at': v.created_at.isoformat() if v.created_at else None,
                'created_by': v.created_by
            })
        return jsonify({'versions': version_list})

    # Return HTML for HTMX
    html_parts = []
    for v in versions:
        created = v.created_at.strftime('%b %d %H:%M') if v.created_at else 'Unknown'
        type_badge = 'auto' if v.version_type == 'auto' else 'manual'
        html_parts.append(f'''
            <div class="version-item" data-version-id="{v.id}">
                <span class="version-badge version-{type_badge}">{type_badge}</span>
                <span class="version-date">{created}</span>
                <button class="btn-icon"
                        hx-post="/api/version/{v.id}/restore"
                        hx-swap="none"
                        hx-confirm="Restore this version? Current state will be backed up."
                        title="Restore">↩</button>
            </div>
        ''')

    if not html_parts:
        return '<p class="empty-state">No versions yet</p>'

    return '\n'.join(html_parts)


@bp.route('/version/<int:version_id>/restore', methods=['POST'])
@login_required
def restore_version(version_id):
    """Restore a book to a previous version.

    Creates a backup before restoring.

    Args:
        version_id: Version ID to restore

    Returns:
        Success response
    """
    version = Version.query.get_or_404(version_id)
    book = Book.query.get(version.book_id)

    # Create backup before restore
    backup_snapshot = _create_book_snapshot(book)
    backup = Version(
        book_id=book.id,
        snapshot=json.dumps(backup_snapshot, ensure_ascii=False),
        version_type='auto',
        created_by=current_user.id
    )
    db.session.add(backup)

    # Restore from version
    snapshot = json.loads(version.snapshot)
    _restore_book_from_snapshot(book, snapshot)

    book.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    logger.info("version_restored",
                version_id=version_id,
                book_slug=book.slug,
                backup_version_id=backup.id,
                user=current_user.username)

    return jsonify({
        'status': 'ok',
        'message': 'Version restored successfully',
        'backup_version_id': backup.id
    })


@bp.route('/version/<int:version_id>', methods=['DELETE'])
@login_required
def delete_version(version_id):
    """Delete a version.

    Args:
        version_id: Version ID

    Returns:
        Success response
    """
    version = Version.query.get_or_404(version_id)

    logger.info("version_deleted",
                version_id=version_id,
                book_id=version.book_id,
                user=current_user.username)

    db.session.delete(version)
    db.session.commit()

    return jsonify({'status': 'ok', 'message': 'Version deleted'})


@bp.route('/reference/<int:ref_id>/verify', methods=['POST'])
@login_required
def verify_reference(ref_id):
    """Toggle verification status of a reference.

    Args:
        ref_id: Reference ID

    Returns:
        Updated paragraph HTML for HTMX
    """
    ref = Reference.query.get_or_404(ref_id)
    ref.verified = not ref.verified
    db.session.commit()

    logger.info("reference_verified",
                ref_id=ref_id,
                verified=ref.verified,
                user=current_user.username)

    # Return the updated paragraph HTML
    para = ref.paragraph
    return render_template('components/paragraph.html', para=para)


@bp.route('/reference/<int:ref_id>', methods=['DELETE'])
@login_required
def delete_reference(ref_id):
    """Delete a reference.

    Args:
        ref_id: Reference ID

    Returns:
        Success response
    """
    ref = Reference.query.get_or_404(ref_id)

    logger.info("reference_deleted",
                ref_id=ref_id,
                ref_type=ref.ref_type,
                paragraph_id=ref.paragraph_id,
                user=current_user.username)

    db.session.delete(ref)
    db.session.commit()

    return jsonify({'status': 'ok', 'message': 'Reference deleted'})


@bp.route('/book/<slug>', methods=['DELETE'])
@login_required
def delete_book(slug):
    """Delete a book and all its content.

    Args:
        slug: Book slug

    Returns:
        Success response
    """
    book = Book.query.filter_by(slug=slug).first_or_404()

    logger.info("book_deleted",
                book_slug=slug,
                title=book.title,
                user=current_user.username)

    # Cascade delete handles chapters, paragraphs, groups, versions, references
    db.session.delete(book)
    db.session.commit()

    return jsonify({'status': 'ok', 'message': f'Book "{book.title}" deleted'})


def _build_export_data(book):
    """Build export data dict from Book model.

    Args:
        book: Book model instance

    Returns:
        Dict suitable for export functions
    """
    data = {
        'title': book.title,
        'author': book.author,
        'slug': book.slug,
        'paragraphs': [],
        'groups': [],
    }

    # Build paragraphs list
    for chapter in book.chapters.order_by(Chapter.order_index).all():
        for para in chapter.paragraphs.filter_by(deleted=False).order_by(Paragraph.order_index).all():
            para_data = {
                'id': para.id,
                'text': para.text,
                'order_index': para.order_index,
                'chapter_title': chapter.title,
                'page_number': para.page_number,
                'is_heading': para.type in ('heading', 'subheading'),
                'heading_level': para.level if para.type in ('heading', 'subheading') else None,
                'quran_refs': [],
                'hadith_refs': [],
                'group_id': para.group_id,
            }

            # Add references
            for ref in para.references.all():
                if ref.ref_type == 'quran':
                    para_data['quran_refs'].append({
                        'surah': ref.surah,
                        'ayah': ref.ayah_start,
                        'ayah_end': ref.ayah_end,
                        'surah_name': ref.surah_name,
                        'verified': ref.verified,
                    })
                elif ref.ref_type == 'hadith':
                    para_data['hadith_refs'].append({
                        'collection': ref.collection,
                        'hadith_number': ref.hadith_number,
                        'verified': ref.verified,
                    })

            data['paragraphs'].append(para_data)

    # Build groups list
    groups = Group.query.filter_by(book_id=book.id).order_by(Group.order_index).all()
    for group in groups:
        group_paras = [p for p in data['paragraphs'] if p['group_id'] == group.id]
        data['groups'].append({
            'order_index': group.order_index,
            'token_count': group.token_count,
            'paragraphs': group_paras,
        })

    return data


@bp.route('/book/<slug>/export/book-json')
@login_required
def export_book_json_route(slug):
    """Export book as Book JSON format.

    Args:
        slug: Book slug

    Returns:
        JSON file download
    """
    book = Book.query.filter_by(slug=slug).first_or_404()
    data = _build_export_data(book)
    json_str = export_book_json(data)

    logger.info("book_exported",
                book_slug=slug,
                format='book_json',
                user=current_user.username)

    return Response(
        json_str,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="{slug}_book.json"'}
    )


@bp.route('/book/<slug>/export/lightrag')
@login_required
def export_lightrag_route(slug):
    """Export book as LightRAG JSON format.

    Args:
        slug: Book slug

    Returns:
        JSON file download
    """
    book = Book.query.filter_by(slug=slug).first_or_404()
    data = _build_export_data(book)
    json_str = export_lightrag_json(data)

    logger.info("book_exported",
                book_slug=slug,
                format='lightrag',
                user=current_user.username)

    return Response(
        json_str,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="{slug}_lightrag.json"'}
    )
