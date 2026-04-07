import os
from datetime import datetime

from bson import ObjectId
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from auth import hash_password, login_required, verify_password
from db import MongoNotAvailable, get_db_checked


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-change-me")

def _col(name: str):
    db = get_db_checked()
    return db[name]


def _now():
    return datetime.utcnow()


def _current_user_id():
    uid = session.get("user_id")
    return ObjectId(uid) if uid else None


@app.errorhandler(MongoNotAvailable)
def mongo_not_available(_e):
    return (
        render_template(
            "mongo_error.html",
            uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        ),
        503,
    )


@app.get("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.get("/signup")
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("signup.html")


@app.post("/signup")
def signup_post():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    confirm = request.form.get("confirm") or ""

    if not name or not email or not password:
        flash("All fields are required.", "danger")
        return redirect(url_for("signup"))
    if password != confirm:
        flash("Passwords do not match.", "danger")
        return redirect(url_for("signup"))
    if _col("users").find_one({"email": email}):
        flash("Email already registered. Please sign in.", "warning")
        return redirect(url_for("signin"))

    doc = {
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "created_at": _now(),
    }
    res = _col("users").insert_one(doc)
    session["user_id"] = str(res.inserted_id)
    session["user_name"] = name
    flash("Welcome! Your account is ready.", "success")
    return redirect(url_for("dashboard"))


@app.get("/signin")
def signin():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("signin.html")


@app.post("/signin")
def signin_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = _col("users").find_one({"email": email})
    if not user or not verify_password(password, user.get("password_hash", "")):
        flash("Invalid email or password.", "danger")
        return redirect(url_for("signin"))

    session["user_id"] = str(user["_id"])
    session["user_name"] = user.get("name") or "Student"
    flash("Signed in successfully.", "success")
    return redirect(url_for("dashboard"))


@app.post("/signout")
def signout():
    session.clear()
    flash("Signed out.", "info")
    return redirect(url_for("index"))


@app.get("/dashboard")
@login_required
def dashboard():
    uid = _current_user_id()
    q = (request.args.get("q") or "").strip()
    query = {"user_id": uid}
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"content": {"$regex": q, "$options": "i"}},
            {"tags": {"$regex": q, "$options": "i"}},
        ]

    user_notes = list(_col("notes").find(query).sort("updated_at", -1).limit(200))
    return render_template("dashboard.html", notes=user_notes, q=q)


@app.get("/notes/new")
@login_required
def note_new():
    return render_template("note_edit.html", note=None)


@app.post("/notes/new")
@login_required
def note_new_post():
    uid = _current_user_id()
    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    tags = (request.form.get("tags") or "").strip()

    if not title or not content:
        flash("Title and content are required.", "danger")
        return redirect(url_for("note_new"))

    doc = {
        "user_id": uid,
        "title": title,
        "content": content,
        "tags": tags,
        "created_at": _now(),
        "updated_at": _now(),
    }
    _col("notes").insert_one(doc)
    flash("Note added.", "success")
    return redirect(url_for("dashboard"))


@app.get("/notes/<note_id>")
@login_required
def note_view(note_id):
    uid = _current_user_id()
    note = _col("notes").find_one({"_id": ObjectId(note_id), "user_id": uid})
    if not note:
        flash("Note not found.", "warning")
        return redirect(url_for("dashboard"))
    return render_template("note_view.html", note=note)


@app.get("/notes/<note_id>/edit")
@login_required
def note_edit(note_id):
    uid = _current_user_id()
    note = _col("notes").find_one({"_id": ObjectId(note_id), "user_id": uid})
    if not note:
        flash("Note not found.", "warning")
        return redirect(url_for("dashboard"))
    return render_template("note_edit.html", note=note)


@app.post("/notes/<note_id>/edit")
@login_required
def note_edit_post(note_id):
    uid = _current_user_id()
    title = (request.form.get("title") or "").strip()
    content = (request.form.get("content") or "").strip()
    tags = (request.form.get("tags") or "").strip()

    if not title or not content:
        flash("Title and content are required.", "danger")
        return redirect(url_for("note_edit", note_id=note_id))

    res = _col("notes").update_one(
        {"_id": ObjectId(note_id), "user_id": uid},
        {"$set": {"title": title, "content": content, "tags": tags, "updated_at": _now()}},
    )
    if res.matched_count == 0:
        flash("Note not found.", "warning")
    else:
        flash("Note updated.", "success")
    return redirect(url_for("note_view", note_id=note_id))


@app.post("/notes/<note_id>/delete")
@login_required
def note_delete(note_id):
    uid = _current_user_id()
    res = _col("notes").delete_one({"_id": ObjectId(note_id), "user_id": uid})
    if res.deleted_count:
        flash("Note deleted.", "info")
    else:
        flash("Note not found.", "warning")
    return redirect(url_for("dashboard"))


@app.get("/notes/<note_id>/pdf")
@login_required
def note_pdf(note_id):
    uid = _current_user_id()
    note = _col("notes").find_one({"_id": ObjectId(note_id), "user_id": uid})
    if not note:
        flash("Note not found.", "warning")
        return redirect(url_for("dashboard"))

    os.makedirs("tmp", exist_ok=True)
    filename = f"tmp/note_{note_id}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    title = note.get("title", "Untitled")
    content = note.get("content", "")
    tags = note.get("tags", "")

    y = height - 72
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, y, title[:90])
    y -= 24

    c.setFont("Helvetica", 10)
    if tags:
        c.drawString(72, y, f"Tags: {tags}"[:120])
        y -= 18

    c.setFont("Helvetica", 11)
    for line in content.splitlines() or [""]:
        while len(line) > 100:
            chunk, line = line[:100], line[100:]
            if y < 72:
                c.showPage()
                y = height - 72
                c.setFont("Helvetica", 11)
            c.drawString(72, y, chunk)
            y -= 14
        if y < 72:
            c.showPage()
            y = height - 72
            c.setFont("Helvetica", 11)
        c.drawString(72, y, line)
        y -= 14

    c.save()
    return send_file(filename, as_attachment=True, download_name=f"{title}.pdf")


@app.get("/calendar")
@login_required
def calendar_page():
    return render_template("calendar.html")


@app.get("/api/events")
@login_required
def api_events_list():
    uid = _current_user_id()
    docs = list(_col("events").find({"user_id": uid}))
    out = []
    for e in docs:
        out.append(
            {
                "id": str(e["_id"]),
                "title": e.get("title", "Event"),
                "start": e.get("start"),
                "end": e.get("end"),
            }
        )
    return jsonify(out)


@app.post("/api/events")
@login_required
def api_events_create():
    uid = _current_user_id()
    data = request.get_json(force=True, silent=True) or {}
    title = (data.get("title") or "").strip()
    start = data.get("start")
    end = data.get("end")
    if not title or not start:
        return jsonify({"error": "title and start are required"}), 400

    doc = {"user_id": uid, "title": title, "start": start, "end": end, "created_at": _now()}
    res = _col("events").insert_one(doc)
    return jsonify({"id": str(res.inserted_id)}), 201


@app.delete("/api/events/<event_id>")
@login_required
def api_events_delete(event_id):
    uid = _current_user_id()
    res = _col("events").delete_one({"_id": ObjectId(event_id), "user_id": uid})
    if not res.deleted_count:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)

