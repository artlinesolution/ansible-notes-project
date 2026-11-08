import os
import requests

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

API_URL = os.environ.get(
    "NOTES_API_URL",
    "http://127.0.0.1:5051"
).rstrip("/")

API_KEY = os.environ.get("NOTES_API_KEY")

if not API_KEY:
    raise RuntimeError("NOTES_API_KEY is required")


def api_headers():
    return {"X-API-Key": API_KEY}


@app.get("/")
def home():
    notes = []
    error = None

    try:
        response = requests.get(
            f"{API_URL}/notes",
            headers=api_headers(),
            timeout=5
        )
        response.raise_for_status()
        notes = response.json()

    except (requests.RequestException, ValueError):
        error = "Unable to connect to the notes database."

    return render_template(
        "index.html",
        notes=notes,
        error=error,
        saved=request.args.get("saved") == "1"
    )


@app.post("/notes")
def create_note():
    content = request.form.get("content", "").strip()

    if not content or len(content) > 1000:
        return "Note must contain 1 to 1000 characters", 400

    try:
        response = requests.post(
            f"{API_URL}/notes",
            headers=api_headers(),
            json={"content": content},
            timeout=5
        )
        response.raise_for_status()

    except requests.RequestException:
        return "Unable to save note. Check database API.", 502

    return redirect(url_for("home", saved="1"), code=303)


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8080,
        debug=False
    )
