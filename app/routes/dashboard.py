"""Dashboard routes."""
import re
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.models import db, Book, Chapter, Paragraph, Reference, Group
from app.config import get_logger, UPLOADS_DIR
from app.services.docx_parser import parse_docx
from app.services.pdf_matcher import match_paragraphs_to_pdf
from app.services.quran_detector import detect_quran_refs
from app.services.hadith_detector import detect_hadith_refs
from app.services.footnote_linker import detect_footnote_markers, detect_footnotes, link_footnotes
from app.services.grouping import create_groups, count_tokens

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

    # Optional PDF file for page matching
    pdf_file = request.files.get('pdf_file')
    if pdf_file and pdf_file.filename:
        if not pdf_file.filename.endswith('.pdf'):
            flash('PDF file must have .pdf extension', 'error')
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

    # Save the DOCX file
    filename = secure_filename(file.filename)
    upload_path = UPLOADS_DIR / f"{slug}_{filename}"
    file.save(upload_path)

    # Save PDF file if provided
    pdf_upload_path = None
    if pdf_file and pdf_file.filename:
        pdf_filename = secure_filename(pdf_file.filename)
        pdf_upload_path = UPLOADS_DIR / f"{slug}_{pdf_filename}"
        pdf_file.save(pdf_upload_path)

    try:
        # Parse the DOCX
        result = parse_docx(upload_path)

        # Create the book
        book = Book(
            title=title,
            author=author or None,
            slug=slug,
            docx_path=str(upload_path),
            pdf_path=str(pdf_upload_path) if pdf_upload_path else None,
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

        # PDF page matching (if PDF provided)
        if pdf_upload_path:
            all_paragraphs = []
            for chapter in book.chapters:
                for para in chapter.paragraphs:
                    all_paragraphs.append({'id': para.id, 'text': para.text})

            if all_paragraphs:
                match_results = match_paragraphs_to_pdf(all_paragraphs, pdf_upload_path)
                for match in match_results:
                    para = Paragraph.query.get(match['paragraph_id'])
                    if para:
                        para.page_number = match['page_number']
                        para.page_confidence = match['confidence']
                db.session.commit()
                logger.info("pdf_matching_complete",
                            book_slug=slug,
                            matched_count=sum(1 for m in match_results if m['page_number']))

        # Reference detection (Quran and Hadith)
        ref_count = 0
        for chapter in book.chapters:
            for para in chapter.paragraphs:
                # Detect Quran references
                quran_refs = detect_quran_refs(para.text)
                for ref in quran_refs:
                    db_ref = Reference(
                        paragraph_id=para.id,
                        ref_type='quran',
                        surah=ref.get('surah'),
                        ayah_start=ref.get('ayah_start'),
                        ayah_end=ref.get('ayah_end'),
                        surah_name=ref.get('surah_name'),
                        raw_text=ref.get('raw_text'),
                        auto_detected=True
                    )
                    db.session.add(db_ref)
                    ref_count += 1

                # Detect Hadith references
                hadith_refs = detect_hadith_refs(para.text)
                for ref in hadith_refs:
                    db_ref = Reference(
                        paragraph_id=para.id,
                        ref_type='hadith',
                        collection=ref.get('collection'),
                        hadith_number=ref.get('hadith_number'),
                        raw_text=ref.get('raw_text'),
                        auto_detected=True
                    )
                    db.session.add(db_ref)
                    ref_count += 1

        db.session.commit()
        if ref_count > 0:
            logger.info("references_detected",
                        book_slug=slug,
                        reference_count=ref_count)

        # Footnote detection and linking
        footnote_count = 0
        for chapter in book.chapters:
            # Collect all paragraph texts to find footnote definitions
            all_paras = list(chapter.paragraphs.all())
            footnote_text = ""

            # Look for paragraphs that appear to be footnote definitions
            for para in all_paras:
                # Check if paragraph starts with footnote-like pattern
                if re.match(r'^\s*(\d+[.)]\s|^\[?\d+\]?\s)', para.text):
                    footnote_text += para.text + "\n"

            # Detect footnotes from collected text
            footnotes = detect_footnotes(footnote_text) if footnote_text else []

            if footnotes:
                # Link footnotes to paragraphs with markers
                for para in all_paras:
                    links = link_footnotes(para.text, footnotes)
                    for link in links:
                        db_ref = Reference(
                            paragraph_id=para.id,
                            ref_type='footnote',
                            raw_text=f"[{link['marker']}] {link['content'][:100]}",
                            auto_detected=True
                        )
                        db.session.add(db_ref)
                        footnote_count += 1

        db.session.commit()
        if footnote_count > 0:
            logger.info("footnotes_linked",
                        book_slug=slug,
                        footnote_count=footnote_count)

        # Create groups for chunking
        all_paras_for_grouping = []
        for chapter in book.chapters:
            for para in chapter.paragraphs:
                all_paras_for_grouping.append({
                    'id': para.id,
                    'text': para.text,
                    'token_count': count_tokens(para.text)
                })

        if all_paras_for_grouping:
            groups_data = create_groups(all_paras_for_grouping)
            for group_data in groups_data:
                group = Group(
                    book_id=book.id,
                    order_index=group_data['order_index'],
                    token_count=group_data['token_count']
                )
                db.session.add(group)
                db.session.flush()

                # Update paragraphs with group_id
                for para_data in group_data['paragraphs']:
                    para = Paragraph.query.get(para_data['id'])
                    if para:
                        para.group_id = group.id

            db.session.commit()
            logger.info("groups_created",
                        book_slug=slug,
                        group_count=len(groups_data))

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
        if pdf_upload_path and pdf_upload_path.exists():
            pdf_upload_path.unlink()

    return redirect(url_for('dashboard.index'))
