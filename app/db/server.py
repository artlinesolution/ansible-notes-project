import os
import hmac
import sqlite3

from pathlib import Path
from contextlib import closing
from datetime import datetime, timezone

from flask import Flask, request, jsonify

app = Flask(__name__)

DB_PATH = Path(
    os.environ.get(
        "NOTES_DB_PATH",
        str(Path(__file__).with_name("notes.sqlite3"))
    )
)

API_KEY = os.environ.get("NOTES_API_KEY")

if not API_KEY:
    raise RuntimeError("NOTES_API_KEY is required")


def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(get_connection()) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.commit()


@app.before_request
def authenticate():
    if request.path == "/health":
        return None

    supplied_key = request.headers.get("X-API-Key", "")

    if not hmac.compare_digest(supplied_key, API_KEY):
        return jsonify({"error": "Unauthorized"}), 401


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/notes")
def create_note():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "JSON object required"}), 400

    content = data.get("content")

    if not isinstance(content, str):
        return jsonify({"error": "Content must be text"}), 400

    content = content.strip()

    if not content or len(content) > 1000:
        return jsonify({
            "error": "Note must contain 1 to 1000 characters"
        }), 400

    created_at = datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )

    with closing(get_connection()) as db:
        cursor = db.execute(
            "INSERT INTO notes (content, created_at) VALUES (?, ?)",
            (content, created_at)
        )
        db.commit()
        note_id = cursor.lastrowid

    return jsonify({
        "id": note_id,
        "content": content,
        "created_at": created_at
    }), 201


@app.get("/notes")
def list_notes():
    with closing(get_connection()) as db:
        rows = db.execute(
            """
            SELECT id, content, created_at
            FROM notes
            ORDER BY id DESC
            LIMIT 100
            """
        ).fetchall()

    return jsonify([dict(row) for row in rows])


initialize_database()

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5051,
        debug=False
    )
