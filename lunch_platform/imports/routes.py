from __future__ import annotations

import tempfile
from pathlib import Path

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for

from ..core.auth import current_account, login_required, require_role
from ..services.imports import (
    add_preview_item,
    apply_preview_import,
    delete_preview_item,
    discard_preview_report,
    get_current_menu_pdf_meta,
    get_current_menu_pdf_path,
    get_preview_pdf_path,
    load_preview_report,
    parse_menu_pdf_preview,
    preview_pdf_exists,
    save_preview_pdf,
    save_preview_report,
    update_preview_item,
    validate_pdf_upload,
)

bp = Blueprint("imports", __name__, url_prefix="/admin/imports")


@bp.route("/preview", methods=["POST"])
@require_role("manager")
def preview_menu_pdf():
    storage = request.files.get("pdf_file")
    error = validate_pdf_upload(storage)
    if error:
        flash(error, "error")
        return redirect(url_for("admin.dashboard"))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        storage.save(tmp.name)
        tmp_path = Path(tmp.name)
    try:
        report = parse_menu_pdf_preview(str(tmp_path), original_filename=storage.filename or "menu.pdf")
        preview_id = save_preview_report(report)
        save_preview_pdf(preview_id, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return redirect(url_for("imports.show_preview", preview_id=preview_id))


@bp.route("/preview/<preview_id>")
@require_role("manager")
def show_preview(preview_id: str):
    report = load_preview_report(preview_id)
    if not report:
        abort(404)
    return render_template(
        "admin/import_preview.html",
        account=current_account(),
        preview_id=preview_id,
        report=report,
        preview_pdf_available=preview_pdf_exists(preview_id),
        current_menu_pdf_meta=get_current_menu_pdf_meta(),
        active_page="admin",
    )


@bp.route("/preview/<preview_id>/item/<item_id>/update", methods=["POST"])
@require_role("manager")
def update_preview_item_route(preview_id: str, item_id: str):
    day = request.form.get("day", "")
    dish_name = request.form.get("dish_name", "")
    price_text = request.form.get("price_text", "")
    report = update_preview_item(preview_id, item_id, day=day, dish_name=dish_name, price_text=price_text)
    if not report:
        flash("Preview item not found.", "error")
    else:
        flash("Preview položka byla upravena.")
    return redirect(url_for("imports.show_preview", preview_id=preview_id))


@bp.route("/preview/<preview_id>/item/<item_id>/delete", methods=["POST"])
@require_role("manager")
def delete_preview_item_route(preview_id: str, item_id: str):
    report = delete_preview_item(preview_id, item_id)
    if not report:
        flash("Preview item not found.", "error")
    else:
        flash("Preview položka byla odstraněna.")
    return redirect(url_for("imports.show_preview", preview_id=preview_id))


@bp.route("/preview/<preview_id>/item/add", methods=["POST"])
@require_role("manager")
def add_preview_item_route(preview_id: str):
    day = request.form.get("day", "")
    dish_name = request.form.get("dish_name", "")
    price_text = request.form.get("price_text", "")
    report = add_preview_item(preview_id, day=day, dish_name=dish_name, price_text=price_text)
    if not report:
        flash("Preview not found.", "error")
    else:
        flash("Nová preview položka byla přidána.")
    return redirect(url_for("imports.show_preview", preview_id=preview_id))


@bp.route("/apply/<preview_id>", methods=["POST"])
@require_role("manager")
def apply_preview(preview_id: str):
    report = load_preview_report(preview_id)
    if not report:
        flash("Import preview not found.", "error")
        return redirect(url_for("admin.dashboard"))
    count = apply_preview_import(current_account(), report, preview_id=preview_id)
    discard_preview_report(preview_id)
    flash(f"Imported {count} dishes from preview.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/discard/<preview_id>", methods=["POST"])
@require_role("manager")
def discard_preview(preview_id: str):
    discard_preview_report(preview_id)
    flash("Import preview discarded.")
    return redirect(url_for("admin.dashboard"))


@bp.route("/pdf/current")
@login_required
def current_menu_pdf():
    path = get_current_menu_pdf_path()
    meta = get_current_menu_pdf_meta()
    if not path.exists():
        abort(404)
    return send_file(path, mimetype="application/pdf", download_name=str(meta.get("filename") or "menu.pdf"))


@bp.route("/pdf/preview/<preview_id>")
@require_role("manager")
def preview_menu_pdf_file(preview_id: str):
    path = get_preview_pdf_path(preview_id)
    if not path.exists():
        abort(404)
    report = load_preview_report(preview_id) or {}
    original_name = str(report.get("meta", {}).get("original_filename", "menu-preview.pdf"))
    return send_file(path, mimetype="application/pdf", download_name=original_name)
