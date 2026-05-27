from __future__ import annotations

import io
import os
import re
import secrets
from datetime import datetime
from functools import wraps
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from werkzeug.utils import secure_filename

from analytics import compute_dashboard
from config import DATA_BACKEND, MAX_UPLOAD_MB, NEW_YEAR_TEMPLATE_FILE, SECRET_KEY, SESSION_COOKIE_SECURE
from database import Storage, StorageError
from excel_export import export_table_workbook, export_workbook, import_workbook
from seed_data import GRADE_LABELS, LEVELS

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    MAX_CONTENT_LENGTH=MAX_UPLOAD_MB * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
)
storage = Storage()


def current_account() -> dict[str, Any] | None:
    if not session.get("account_id"):
        return None
    return next((account for account in storage.list_accounts() if int(account["id"]) == int(session["account_id"])), None)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("account_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Please log in again."}), 401
            return redirect(url_for("login_page"))
        return view(*args, **kwargs)
    return wrapped


def csrf_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if request.headers.get("X-CSRF-Token") != session.get("csrf_token"):
            return jsonify({"error": "Your session security token has expired. Please refresh and try again."}), 403
        return view(*args, **kwargs)
    return wrapped


def log(action: str, section: str, affected: str = "", details: str = "") -> None:
    storage.log_activity(current_account(), action, section, affected, details)


def clean_avatar(value: Any) -> str | None:
    if value is None:
        return None
    avatar = str(value).strip()
    if not avatar:
        return ""
    if avatar.startswith("data:image/") and len(avatar) <= 450_000:
        return avatar
    if avatar.startswith("/static/") or avatar.startswith("https://"):
        return avatar
    raise StorageError("Profile photo is too large or is not a supported image.")


def baseline_year_for_graduating_year(school_year: str) -> str | None:
    """Return the Grade 7 cohort school year for a Grade 12 graduating year."""
    match = re.fullmatch(r"(\d{4})-(\d{4})", str(school_year).strip())
    if not match:
        return None
    start_year = int(match.group(1)) - 5
    return f"{start_year}-{start_year + 1}"


def derive_cohort_baseline(school_year: str, records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Find a cohort baseline directly from stored Grade 7 enrollment data."""
    baseline_year = baseline_year_for_graduating_year(school_year)
    rows = records if records is not None else storage.list_records()
    baseline_row = next(
        (row for row in rows if row.get("school_year") == baseline_year and row.get("grade_level") == "Grade 7"),
        None,
    )
    grade12_row = next(
        (row for row in rows if row.get("school_year") == school_year and row.get("grade_level") == "Grade 12"),
        None,
    )
    return {
        "baseline_year": baseline_year,
        "grade7_baseline": int(baseline_row.get("enrollment") or 0) if baseline_row else None,
        "grade12_current": int(grade12_row.get("enrollment") or 0) if grade12_row else None,
    }


def synchronize_automatic_cohorts(username: str, years: list[str] | None = None) -> list[str]:
    """Create/update cohort records where a corresponding stored Grade 7 baseline exists.

    This ensures dashboard edits and Excel uploads both use the same recorded data
    for automatic baseline values. It never invents a missing historical baseline.
    """
    records = storage.list_records()
    target_years = years or sorted({str(row.get("school_year")) for row in records if row.get("school_year")})
    generated: list[str] = []
    for school_year in target_years:
        derived = derive_cohort_baseline(school_year, records)
        if derived["baseline_year"] and derived["grade7_baseline"] is not None and derived["grade12_current"] is not None:
            storage.upsert_cohort(
                school_year,
                derived["baseline_year"],
                derived["grade7_baseline"],
                derived["grade12_current"],
                username,
            )
            generated.append(school_year)
    return generated


@app.after_request
def secure_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/")
def login_page():
    if session.get("account_id"):
        return redirect(url_for("dashboard"))
    return render_template("login.html", settings=storage.get_settings(), error=None)


@app.post("/login")
def login():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    account = storage.authenticate(username, password)
    if not account:
        return render_template("login.html", settings=storage.get_settings(), error="Incorrect username or password."), 401
    session.clear()
    session["account_id"] = account["id"]
    session["username"] = account["username"]
    session["full_name"] = account["full_name"]
    session["csrf_token"] = secrets.token_urlsafe(28)
    storage.log_activity(account, "Logged in", "Logins", "", "Signed in to the dashboard.")
    return redirect(url_for("dashboard"))


@app.get("/logout")
def logout():
    account = current_account()
    if account:
        storage.log_activity(account, "Logged out", "Logins", "", "Signed out of the dashboard.")
    session.clear()
    return redirect(url_for("login_page"))


@app.get("/dashboard")
@login_required
def dashboard():
    account = current_account()
    if not account:
        session.clear()
        return redirect(url_for("login_page"))
    initials = "".join(piece[0] for piece in account["full_name"].split()[:2]).upper()
    return render_template("dashboard.html", settings=storage.get_settings(), account=account, initials=initials, csrf_token=session["csrf_token"], backend=DATA_BACKEND)


@app.get("/api/dashboard")
@login_required
def api_dashboard():
    years_arg = (request.args.get("years") or "").strip()
    selected = [item for item in years_arg.split(",") if item] or None
    level = request.args.get("level", "All")
    if level not in {"All", "JHS", "SHS"}:
        level = "All"
    data = compute_dashboard(storage.list_records(), storage.list_resources(), storage.list_cohort(), selected, level)
    return jsonify({
        "analytics": data, "settings": storage.get_settings(), "records": storage.list_records(),
        "resources": storage.list_resources(), "room_sizes": storage.list_room_sizes(), "cohort": storage.list_cohort(),
        "actions": storage.list_actions(), "accounts": storage.list_accounts(), "activity": storage.list_activity(150), "backend": DATA_BACKEND,
    })


@app.post("/api/records")
@csrf_required
def api_save_record():
    payload = request.get_json(force=True)
    required = ["school_year", "level", "grade_level"]
    if any(not str(payload.get(key, "")).strip() for key in required):
        return jsonify({"error": "School year, level, and grade level are required."}), 400
    if payload["grade_level"] not in GRADE_LABELS or payload["level"] not in {"JHS", "SHS"}:
        return jsonify({"error": "Select a valid grade level and school level."}), 400
    storage.snapshot_data(f"Edit school record: {payload['school_year']} / {payload['grade_level']}", session["username"])
    row = storage.upsert_record(payload, session["username"])
    synchronize_automatic_cohorts(session["username"])
    log("Updated school records", "Records", f"{payload['school_year']} / {payload['grade_level']}", "Saved enrollment, dropout, repeater, or teacher values. Applicable cohort baselines were refreshed from stored Grade 7 data.")
    return jsonify({"message": "School record saved.", "record": row})


@app.post("/api/years")
@csrf_required
def api_add_year():
    payload = request.get_json(force=True)
    year = str(payload.get("school_year", "")).strip()
    grade_rows = payload.get("grades", [])
    if not year or len(grade_rows) != 6:
        return jsonify({"error": "Enter one complete row for each grade level."}), 400
    storage.snapshot_data(f"Add or replace school year: {year}", session["username"])
    for index, grade in enumerate(GRADE_LABELS):
        item = grade_rows[index]
        storage.upsert_record({
            "school_year": year, "level": LEVELS[index], "grade_level": grade,
            "enrollment": int(item.get("enrollment") or 0), "dropouts": int(item.get("dropouts") or 0),
            "repeaters": int(item.get("repeaters") or 0), "teachers": int(item.get("teachers") or 0),
        }, session["username"])
    resource = payload.get("resources", {})
    storage.upsert_resource(year, int(resource.get("jhs_classrooms") or 0), int(resource.get("shs_classrooms") or 0), session["username"])
    auto_years = synchronize_automatic_cohorts(session["username"], [year])
    cohort_message = ""
    if year in auto_years:
        derived = derive_cohort_baseline(year)
        cohort_message = f"Cohort baseline was automatically generated from Grade 7 enrollment in SY {derived['baseline_year']}."
    else:
        cohort = payload.get("cohort") or {}
        if cohort.get("grade7_baseline") and cohort.get("grade12_current"):
            storage.upsert_cohort(year, str(cohort.get("baseline_year", "")), int(cohort["grade7_baseline"]), int(cohort["grade12_current"]), session["username"])
            cohort_message = "No matching stored Grade 7 baseline was found; the official manually entered cohort baseline was saved."
        else:
            cohort_message = "No matching stored Grade 7 baseline was found; cohort survival will remain unavailable until an official baseline is entered."
    log("Added school year", "Records", year, f"New school-year records were saved and now appear in dashboard analytics and Excel exports. {cohort_message}")
    return jsonify({"message": f"SY {year} was added successfully.", "cohort_message": cohort_message, "auto_baseline": year in auto_years})


@app.post("/api/resources")
@csrf_required
def api_save_resources():
    payload = request.get_json(force=True)
    year = str(payload.get("school_year", "")).strip()
    storage.snapshot_data(f"Edit classrooms: {year}", session["username"])
    storage.upsert_resource(year, int(payload.get("jhs_classrooms") or 0), int(payload.get("shs_classrooms") or 0), session["username"])
    log("Updated resources", "Records", year, "Saved classroom totals.")
    return jsonify({"message": "Resource record saved."})


@app.post("/api/room-sizes")
@csrf_required
def api_save_room_size():
    payload = request.get_json(force=True)
    storage.snapshot_data(f"Edit room size: {payload['grade_level']}", session["username"])
    storage.upsert_room_size(str(payload["grade_level"]), float(payload.get("room_length") or 0), float(payload.get("room_width") or 0), session["username"])
    log("Updated room size", "Records", str(payload["grade_level"]), "Saved classroom dimensions.")
    return jsonify({"message": "Room-size record saved."})


@app.post("/api/cohort")
@csrf_required
def api_save_cohort():
    payload = request.get_json(force=True)
    storage.snapshot_data(f"Edit cohort record: {payload['school_year']}", session["username"])
    storage.upsert_cohort(str(payload["school_year"]), str(payload.get("baseline_year", "")), int(payload.get("grade7_baseline") or 0), int(payload.get("grade12_current") or 0), session["username"])
    log("Updated cohort records", "Records", str(payload["school_year"]), "Saved cohort baseline and Grade 12 values.")
    return jsonify({"message": "Cohort record saved."})


@app.post("/api/actions")
@csrf_required
def api_create_action():
    payload = request.get_json(force=True)
    storage.snapshot_data(f"Add action plan: {payload.get('focus_area', '')}", session["username"])
    item = storage.create_action(payload, session["username"])
    log("Added action plan", "Action Plans", payload.get("focus_area", ""), payload.get("suggested_action", ""))
    return jsonify({"message": "Action plan saved.", "action": item})


@app.patch("/api/actions/<int:action_id>")
@csrf_required
def api_update_action(action_id: int):
    payload = request.get_json(force=True)
    storage.snapshot_data(f"Edit action plan: {payload.get('focus_area', '')}", session["username"])
    item = storage.update_action(action_id, payload, session["username"])
    log("Updated action plan", "Action Plans", payload.get("focus_area", ""), payload.get("suggested_action", ""))
    return jsonify({"message": "Action plan updated.", "action": item})


@app.post("/api/accounts")
@csrf_required
def api_create_account():
    payload = request.get_json(force=True)
    name, username, password = str(payload.get("full_name", "")).strip(), str(payload.get("username", "")).strip(), str(payload.get("password", ""))
    if len(name) < 2 or len(username) < 3 or len(password) < 8:
        return jsonify({"error": "Enter a name, username of at least 3 characters, and password of at least 8 characters."}), 400
    try:
        item = storage.create_account(name, username, password, clean_avatar(payload.get("avatar_url")) or "")
    except StorageError as error:
        return jsonify({"error": str(error)}), 400
    log("Added account holder", "Accounts", username, f"Created login account for {name}.")
    return jsonify({"message": "Account holder added.", "account": item})


@app.patch("/api/accounts/<int:account_id>")
@csrf_required
def api_update_account(account_id: int):
    payload = request.get_json(force=True)
    password = str(payload.get("password", "")) or None
    if password and len(password) < 8:
        return jsonify({"error": "New password must be at least 8 characters."}), 400
    try:
        avatar = clean_avatar(payload.get("avatar_url")) if "avatar_url" in payload else None
        item = storage.update_account(account_id, str(payload.get("full_name", "")).strip(), str(payload.get("username", "")).strip(), password, avatar)
    except StorageError as error:
        return jsonify({"error": str(error)}), 400
    if int(account_id) == int(session["account_id"]):
        session["full_name"], session["username"] = item["full_name"], item["username"]
    log("Edited account holder", "Accounts", item["username"], f"Updated account details for {item['full_name']}.")
    return jsonify({"message": "Account holder updated.", "account": item})


@app.delete("/api/accounts/<int:account_id>")
@csrf_required
def api_delete_account(account_id: int):
    if int(account_id) == int(session["account_id"]):
        return jsonify({"error": "You cannot delete the account currently signed in."}), 400
    try:
        storage.delete_account(account_id)
    except StorageError as error:
        return jsonify({"error": str(error)}), 400
    log("Deleted account holder", "Accounts", str(account_id), "Removed a dashboard login account.")
    return jsonify({"message": "Account holder deleted."})


@app.delete("/api/years/<path:school_year>")
@csrf_required
def api_delete_year(school_year: str):
    existing_years = {row["school_year"] for row in storage.list_records()}
    if school_year not in existing_years:
        return jsonify({"error": "School year was not found."}), 404
    storage.snapshot_data(f"Delete school year: {school_year}", session["username"])
    deleted = storage.delete_school_year(school_year)
    log("Deleted school year", "Records", school_year, "Removed the selected year's stored records. Use Undo Last Data Change to restore it if needed.")
    return jsonify({"message": f"SY {school_year} was deleted.", "deleted": deleted})


@app.delete("/api/actions/<int:action_id>")
@csrf_required
def api_delete_action(action_id: int):
    action = next((item for item in storage.list_actions() if int(item["id"]) == action_id), None)
    if not action:
        return jsonify({"error": "Action plan was not found."}), 404
    storage.snapshot_data(f"Delete action plan: {action.get('focus_area', '')}", session["username"])
    storage.delete_action(action_id)
    log("Deleted action plan", "Action Plans", action.get("focus_area", ""), "Removed an action plan. Use Undo Last Data Change to restore it if needed.")
    return jsonify({"message": "Action plan deleted."})


@app.post("/api/undo")
@csrf_required
def api_undo_data_change():
    try:
        restored = storage.undo_last_data_change(session["username"])
    except StorageError as error:
        return jsonify({"error": str(error)}), 400
    log("Undid data change", "Records", restored, "Restored saved data to the state before the last important change.")
    return jsonify({"message": f"Restored data before: {restored}."})


@app.patch("/api/settings")
@csrf_required
def api_settings():
    updated = storage.update_settings(request.get_json(force=True), session["username"])
    log("Changed dashboard display settings", "Accounts", "Display Settings", "Updated title, subtitle, or dashboard colors.")
    return jsonify({"message": "Display settings updated.", "settings": updated})


@app.post("/api/upload-excel")
@csrf_required
def api_upload_excel():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename.lower().endswith(".xlsx"):
        return jsonify({"error": "Upload an .xlsx workbook file."}), 400
    before = {record["school_year"] for record in storage.list_records()}
    sync_mode = (request.form.get("sync_mode") or "merge").strip().lower()
    if sync_mode not in {"merge", "replace"}:
        return jsonify({"error": "Choose a valid Excel synchronization option."}), 400
    try:
        imported = import_workbook(uploaded.stream)
        if not imported["records"]:
            return jsonify({"error": "The workbook does not contain school records to upload."}), 400
        storage.snapshot_data(f"Upload Excel workbook ({sync_mode}): {secure_filename(uploaded.filename)}", session["username"])
        if sync_mode == "replace":
            storage.replace_school_data_from_workbook(imported, session["username"])
        else:
            for record in imported["records"]:
                storage.upsert_record(record, session["username"])
            for resource in imported["resources"]:
                storage.upsert_resource(resource["school_year"], resource["jhs_classrooms"], resource["shs_classrooms"], session["username"])
            for cohort in imported["cohorts"]:
                storage.upsert_cohort(cohort["school_year"], cohort["baseline_year"], cohort["grade7_baseline"], cohort["grade12_current"], session["username"])
            for action in imported.get("actions", []):
                storage.upsert_action(action, session["username"])
        auto_baselines = synchronize_automatic_cohorts(session["username"])
    except (ValueError, StorageError) as error:
        return jsonify({"error": str(error)}), 400
    added = sorted(set(imported["years"]) - before)
    years = ", ".join(imported["years"])
    action_label = "Replaced dashboard data from Excel" if sync_mode == "replace" else "Uploaded Excel workbook"
    detail = ("Replaced school records so workbook additions, updates and removals now match the dashboard." if sync_mode == "replace" else f"Imported or updated records for: {years}.")
    log(action_label, "Records", secure_filename(uploaded.filename), detail)
    return jsonify({"message": "Workbook synchronized and dashboard data refreshed." if sync_mode == "replace" else "Workbook uploaded and dashboard data refreshed.", "years": imported["years"], "new_years": added, "record_count": len(imported["records"]), "sync_mode": sync_mode, "auto_baselines": sorted(set(auto_baselines) & set(imported["years"]))})


@app.get("/api/export/template/new-year")
@login_required
def api_export_new_year_template():
    filename = "SRNHS_New_School_Year_Upload_Template.xlsx"
    if not NEW_YEAR_TEMPLATE_FILE.exists():
        return jsonify({"error": "New school year template file is not available."}), 404
    storage.save_report_export("New School Year Excel Template", session["username"], [], "Excel")
    log("Downloaded new-year Excel template", "Reports", filename, "Blank Excel upload format for adding one new school year.")
    return send_file(NEW_YEAR_TEMPLATE_FILE, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/api/export/excel")
@login_required
def api_export_excel():
    filename = f"SRNHS_Dashboard_Updated_Data_{datetime.now().strftime('%Y%m%d')}.xlsx"
    years = sorted({record["school_year"] for record in storage.list_records()})
    content = export_workbook(storage, storage.get_settings())
    storage.save_workbook_export(session["username"], filename, years)
    log("Downloaded updated Excel workbook", "Reports", filename, f"Included school years: {', '.join(years)}.")
    return send_file(content, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/api/export/xlsx/<table_name>")
@login_required
def api_export_table_xlsx(table_name: str):
    supported = {"records": storage.list_records, "actions": storage.list_actions, "activity": lambda: storage.list_activity(500)}
    if table_name not in supported:
        return jsonify({"error": "Export not found."}), 404
    content = export_table_workbook(table_name, supported[table_name]())
    filename = f"SRNHS_{table_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    storage.save_report_export(table_name, session["username"], [], "Excel")
    log("Downloaded table export", "Reports", filename, "Excel export generated.")
    return send_file(content, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def graph_title(text: str, width: float) -> Drawing:
    drawing = Drawing(width, 26)
    drawing.add(String(0, 10, text, fontName="Helvetica-Bold", fontSize=11, fillColor=colors.HexColor("#0B3D24")))
    return drawing


def bar_drawing(labels: list[str], values: list[float], width: float = 345, height: float = 155, fill: str = "#168447") -> Drawing:
    drawing = Drawing(width, height)
    margin_left, base_y, chart_h, chart_w = 38, 30, height - 42, width - 46
    maximum = max(values or [1]) or 1
    drawing.add(Line(margin_left, base_y, margin_left, base_y + chart_h, strokeColor=colors.HexColor("#DCE8E0")))
    drawing.add(Line(margin_left, base_y, margin_left + chart_w, base_y, strokeColor=colors.HexColor("#DCE8E0")))
    bar_w = chart_w / max(len(values), 1) * .58
    step = chart_w / max(len(values), 1)
    for index, value in enumerate(values):
        x = margin_left + index * step + (step - bar_w) / 2
        h = max(2, value / maximum * chart_h)
        drawing.add(Rect(x, base_y, bar_w, h, fillColor=colors.HexColor(fill), strokeColor=None, rx=4, ry=4))
        drawing.add(String(x + bar_w / 2, base_y - 14, labels[index][-4:], textAnchor="middle", fontSize=7.5, fillColor=colors.HexColor("#52665A")))
        drawing.add(String(x + bar_w / 2, base_y + h + 4, f"{int(value):,}", textAnchor="middle", fontSize=7, fillColor=colors.HexColor("#0B3D24")))
    return drawing


def line_drawing(labels: list[str], values: list[float | None], width: float = 345, height: float = 155, fill: str = "#168447", suffix: str = "") -> Drawing:
    drawing = Drawing(width, height)
    margin_left, base_y, chart_h, chart_w = 38, 30, height - 42, width - 46
    clean = [float(v) for v in values if v is not None]
    maximum, minimum = max(clean or [1]), min(clean or [0])
    span = max(maximum - minimum, 1)
    drawing.add(Line(margin_left, base_y, margin_left, base_y + chart_h, strokeColor=colors.HexColor("#DCE8E0")))
    drawing.add(Line(margin_left, base_y, margin_left + chart_w, base_y, strokeColor=colors.HexColor("#DCE8E0")))
    points = []
    step = chart_w / max(len(labels) - 1, 1)
    for index, value in enumerate(values):
        if value is None:
            continue
        x = margin_left + index * step
        y = base_y + ((float(value) - minimum) / span) * (chart_h - 14) + 4
        points.extend([x, y])
        drawing.add(Rect(x - 3, y - 3, 6, 6, fillColor=colors.HexColor(fill), strokeColor=None, rx=3, ry=3))
        drawing.add(String(x, base_y - 14, labels[index][-4:], textAnchor="middle", fontSize=7.5, fillColor=colors.HexColor("#52665A")))
        drawing.add(String(x, y + 7, f"{float(value):.1f}{suffix}", textAnchor="middle", fontSize=7, fillColor=colors.HexColor("#0B3D24")))
    if len(points) >= 4:
        drawing.add(PolyLine(points, strokeColor=colors.HexColor(fill), strokeWidth=2.5))
    return drawing


@app.get("/api/export/pdf")
@app.get("/api/export/pdf/dashboard")
@login_required
def api_export_pdf():
    years = (request.args.get("years") or "").split(",") if request.args.get("years") else None
    level = request.args.get("level", "All")
    analytics = compute_dashboard(storage.list_records(), storage.list_resources(), storage.list_cohort(), years, level)
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=34, rightMargin=34, topMargin=26, bottomMargin=26)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleGreen", parent=styles["Title"], textColor=colors.HexColor("#0B3D24"), fontSize=24, leading=29, spaceAfter=5)
    sub = ParagraphStyle("Sub", parent=styles["BodyText"], textColor=colors.HexColor("#52665A"), fontSize=10.5, leading=14)
    body = ParagraphStyle("Body", parent=styles["BodyText"], textColor=colors.HexColor("#25382F"), fontSize=9.2, leading=13)
    heading = ParagraphStyle("Heading", parent=styles["Heading2"], textColor=colors.HexColor("#0B3D24"), fontSize=15, leading=19, spaceBefore=10, spaceAfter=8)
    story = [Paragraph("SRNHS School Profile Analysis Dashboard Summary", title), Paragraph(f"Selected view: {analytics['selection_caption']} · Level: {level} · Generated: {datetime.now().strftime('%B %d, %Y')}", sub), Spacer(1, 13)]
    table_data = [["School Year", "Enrollment", "Dropouts", "Dropout Rate", "Repeaters", "Repeater Rate", "Teachers", "Students / Teacher", "Cohort", "Transition"]]
    for row in analytics["summary"]:
        table_data.append([row["school_year"], f"{row['enrollment']:,}", row["dropouts"], f"{row['dropout_rate']:.2f}%", row["repeaters"], f"{row['repeater_rate']:.2f}%", row["teachers"], f"{row['student_teacher_ratio']:.1f}:1", f"{row['cohort_survival']:.2f}%" if row["cohort_survival"] is not None else "—", f"{row['transition_rate']:.2f}%" if row["transition_rate"] is not None else "—"])
    table = Table(table_data, repeatRows=1, colWidths=[75,70,55,66,58,70,54,78,56,62])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#168447")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8.2),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#DCE8E0")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4FBF6")]),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    story.append(table); story.append(Spacer(1, 16))
    story.append(Paragraph("Visual Summary", heading)); story.append(PageBreak())
    story.append(Paragraph("Dashboard Visual Summary", title))
    labels = [row["school_year"] for row in analytics["summary"]]
    graphs = Table([
        [[graph_title("Enrollment Trend", 345), bar_drawing(labels, [row["enrollment"] for row in analytics["summary"]], fill="#168447")], [graph_title("Repeaters by Year", 345), bar_drawing(labels, [row["repeaters"] for row in analytics["summary"]], fill="#0F633B")]],
        [[graph_title("Cohort Survival", 345), line_drawing(labels, [row.get("cohort_survival") for row in analytics["summary"]], fill="#168447", suffix="%")], [graph_title("Students per Teacher", 345), line_drawing(labels, [row.get("student_teacher_ratio") for row in analytics["summary"]], fill="#0F633B")]],
    ], colWidths=[365,365])
    graphs.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BOX",(0,0),(-1,-1),.4,colors.HexColor("#DCE8E0")),("INNERGRID",(0,0),(-1,-1),.4,colors.HexColor("#DCE8E0")),("BACKGROUND",(0,0),(-1,-1),colors.white),("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story.append(graphs); story.append(PageBreak())
    story.append(Paragraph("Business Intelligence Findings", title))
    for tab_label, tab_key in [("Enrollment", "enrollment"), ("Dropouts & Repeaters", "retention"), ("Cohort & Transition", "continuity"), ("Teachers", "teachers"), ("Resources", "resources")]:
        story.append(Paragraph(tab_label, heading))
        for analysis_type in ["descriptive", "diagnostic", "predictive", "prescriptive"]:
            for item in analytics["bi_tabs"][tab_key][analysis_type][:2]:
                story.append(Paragraph(f"<b>{analysis_type.title()} · {item['title']}:</b> {item['text']}", body))
                story.append(Spacer(1, 4))
    story.append(PageBreak()); story.append(Paragraph("Suggested Actions and Ongoing Monitoring", title))
    action_rows = [["Action", "Data Basis", "Monitoring Focus", "Period"]]
    for action in analytics["suggested_actions"]:
        action_rows.append([Paragraph(action["title"] + ": " + action["action"], body), Paragraph(action["basis"], body), Paragraph(action["monitor"], body), Paragraph(action["period"], body)])
    actions_table = Table(action_rows, colWidths=[270,165,145,110], repeatRows=1)
    actions_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0B3D24")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),9),("GRID",(0,0),(-1,-1),.3,colors.HexColor("#DCE8E0")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4FBF6")]),("VALIGN",(0,0),(-1,-1),"TOP"),("PADDING",(0,0),(-1,-1),8)]))
    story.append(actions_table); story.append(Spacer(1, 15)); story.append(Paragraph(analytics["formula_notes"]["forecast"], sub))
    doc.build(story); output.seek(0)
    filename = f"SRNHS_Dashboard_Summary_Paper_{datetime.now().strftime('%Y%m%d')}.pdf"
    storage.save_report_export("Dashboard Summary Paper", session["username"], analytics["selected_years"], "PDF")
    log("Downloaded dashboard summary paper", "Reports", filename, "PDF report with visual and analytical summaries generated from the selected dashboard view.")
    return send_file(output, as_attachment=True, download_name=filename, mimetype="application/pdf")


@app.get("/api/export/pdf/progress")
@login_required
def api_export_progress_pdf():
    years = (request.args.get("years") or "").split(",") if request.args.get("years") else None
    level = request.args.get("level", "All")
    analytics = compute_dashboard(storage.list_records(), storage.list_resources(), storage.list_cohort(), years, level)
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=34, rightMargin=34, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ProgressTitle", parent=styles["Title"], textColor=colors.HexColor("#0B3D24"), fontSize=23, leading=28, spaceAfter=8)
    heading = ParagraphStyle("ProgressHeading", parent=styles["Heading2"], textColor=colors.HexColor("#0F633B"), fontSize=14, leading=18, spaceBefore=10, spaceAfter=7)
    body = ParagraphStyle("ProgressBody", parent=styles["BodyText"], textColor=colors.HexColor("#25382F"), fontSize=9.4, leading=13.5)
    sub = ParagraphStyle("ProgressSub", parent=styles["BodyText"], textColor=colors.HexColor("#52665A"), fontSize=10, leading=14)
    story = [Paragraph("SRNHS School Progress and Action Monitoring Report", title), Paragraph(f"View: {analytics['selection_caption']} · School Level: {level} · Generated: {datetime.now().strftime('%B %d, %Y')}", sub), Spacer(1, 10)]
    story.append(Paragraph("Key School Indicators", heading))
    latest = analytics["latest"]
    indicators = [["Indicator", "Latest Value", "Monitoring Meaning"],
      ["Total Enrollment", f"{latest['enrollment']:,}", "Monitor intake and continuation trend."],
      ["Dropout Rate", f"{latest['dropout_rate']:.2f}%", "Monitor annual fluctuation and affected grades."],
      ["Repeater Rate", f"{latest['repeater_rate']:.2f}%", "Track academic support and reduction efforts."],
      ["Students per Teacher", f"{latest['student_teacher_ratio']:.1f}:1", "Review staffing together with enrollment movement."],
      ["Cohort Survival", f"{latest['cohort_survival']:.2f}%" if latest.get('cohort_survival') is not None else "—", "Track student continuity across years."],
      ["Transition Rate", f"{latest['transition_rate']:.2f}%" if latest.get('transition_rate') is not None else "—", "Compare Grade 11 intake with previous Grade 10."],
    ]
    kpi_table = Table(indicators, colWidths=[145,100,450], repeatRows=1)
    kpi_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#168447")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),9),("GRID",(0,0),(-1,-1),.3,colors.HexColor("#DCE8E0")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4FBF6")]),("PADDING",(0,0),(-1,-1),8)]))
    story.append(kpi_table)
    story.append(Paragraph("Dynamic Business Intelligence Findings", heading))
    for area, type_map in analytics["bi_tabs"].items():
        story.append(Paragraph(area.replace("_", " ").title(), heading))
        for kind in ["descriptive", "diagnostic", "predictive", "prescriptive"]:
            selected_items = type_map.get(kind, [])[:2]
            for item in selected_items:
                story.append(Paragraph(f"<b>{kind.title()} · {item['title']}:</b> {item['text']}", body))
                story.append(Spacer(1, 3))
    story.append(PageBreak())
    story.append(Paragraph("Long-Term Action Plan Tracking", title))
    actions = storage.list_actions()
    rows = [["Focus Area", "Suggested Action", "Indicator / Target", "Period", "Status"]]
    for action in actions[:12]:
        target = f"{action.get('target_indicator','')} {action.get('target_value','')}".strip() or "For monitoring"
        rows.append([Paragraph(str(action.get("focus_area", "")), body), Paragraph(str(action.get("suggested_action", "")), body), Paragraph(target, body), Paragraph(str(action.get("monitoring_period", "")), body), Paragraph(str(action.get("status", "Suggested")), body)])
    plan_table = Table(rows, colWidths=[120,295,125,100,85], repeatRows=1)
    plan_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0B3D24")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),9),("GRID",(0,0),(-1,-1),.3,colors.HexColor("#DCE8E0")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F4FBF6")]),("VALIGN",(0,0),(-1,-1),"TOP"),("PADDING",(0,0),(-1,-1),7)]))
    story.append(plan_table)
    story.append(Spacer(1, 13))
    story.append(Paragraph(analytics["formula_notes"]["forecast"], sub))
    doc.build(story)
    output.seek(0)
    filename = f"SRNHS_School_Progress_Action_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
    storage.save_report_export("School Progress and Action Monitoring Report", session["username"], analytics["selected_years"], "PDF")
    log("Downloaded progress report", "Reports", filename, "Generated a PDF for long-term monitoring and action tracking.")
    return send_file(output, as_attachment=True, download_name=filename, mimetype="application/pdf")


@app.errorhandler(413)
def upload_too_large(_error):
    return jsonify({"error": f"File is too large. Maximum upload size is {MAX_UPLOAD_MB} MB."}), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
