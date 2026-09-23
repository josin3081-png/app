import os
import sqlite3
import time
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "spark.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

DEMO_USERS = [
    {
        "email": "maya@spark.test",
        "password": "demo123",
        "name": "Maya Singh",
        "age": 27,
        "gender": "Woman",
        "looking_for": "Men",
        "city": "Chicago",
        "bio": "Coffee, museums, and spontaneous road trips.",
        "interests": "Coffee, Art, Travel, Music",
        "photo": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=800&q=80",
    },
    {
        "email": "jordan@spark.test",
        "password": "demo123",
        "name": "Jordan Lee",
        "age": 30,
        "gender": "Man",
        "looking_for": "Women",
        "city": "New York",
        "bio": "Weekend climber and ramen enthusiast.",
        "interests": "Hiking, Food, Fitness, Games",
        "photo": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=800&q=80",
    },
    {
        "email": "alex@spark.test",
        "password": "demo123",
        "name": "Alex Chen",
        "age": 29,
        "gender": "Man",
        "looking_for": "Women",
        "city": "Seattle",
        "bio": "Design nerd with a soft spot for indie films.",
        "interests": "Design, Movies, Coffee, Bikes",
        "photo": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=800&q=80",
    },
    {
        "email": "luna@spark.test",
        "password": "demo123",
        "name": "Luna Ortiz",
        "age": 24,
        "gender": "Woman",
        "looking_for": "Everyone",
        "city": "Austin",
        "bio": "Florist who paints on Sundays. Send me your favorite flower.",
        "interests": "Flowers, Painting, Plants, Markets",
        "photo": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?auto=format&fit=crop&w=800&q=80",
    },
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def photo_url(person):
    if not person:
        return url_for("static", filename="placeholder.svg")
    photo = person.get("photo") if isinstance(person, dict) else getattr(person, "photo", None)
    if photo:
        return photo
    return url_for("static", filename="placeholder.svg")


def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            looking_for TEXT,
            city TEXT,
            bio TEXT,
            interests TEXT,
            photo TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS swipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            swiper_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            liked INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(swiper_id, target_id),
            FOREIGN KEY (swiper_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )

    existing = db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    if existing == 0:
        now = datetime.utcnow().isoformat()
        for user in DEMO_USERS:
            db.execute(
                """
                INSERT INTO users (
                    email, password_hash, name, age, gender, looking_for, city, bio, interests, photo, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["email"],
                    generate_password_hash(user["password"]),
                    user["name"],
                    user["age"],
                    user["gender"],
                    user["looking_for"],
                    user["city"],
                    user["bio"],
                    user["interests"],
                    user["photo"],
                    now,
                ),
            )
        db.commit()

        ids = {row["email"]: row["id"] for row in db.execute("SELECT id, email FROM users")}
        match_now = datetime.utcnow().isoformat()
        pairs = [
            (ids["maya@spark.test"], ids["jordan@spark.test"]),
            (ids["maya@spark.test"], ids["alex@spark.test"]),
        ]
        for a, b in pairs:
            db.execute(
                "INSERT OR IGNORE INTO swipes (swiper_id, target_id, liked, created_at) VALUES (?, ?, 1, ?)",
                (a, b, match_now),
            )
            db.execute(
                "INSERT OR IGNORE INTO swipes (swiper_id, target_id, liked, created_at) VALUES (?, ?, 1, ?)",
                (b, a, match_now),
            )
        db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Please sign in"}), 401
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.context_processor
def inject_user():
    return {"current_user": current_user(), "photo_url": photo_url}


TYPING_STATE = {}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def gender_matches(target_gender, looking_for):
    looking = (looking_for or "Everyone").strip().lower()
    gender = (target_gender or "").strip().lower()
    if looking in ("", "everyone"):
        return True
    if looking == "women":
        return gender == "woman"
    if looking == "men":
        return gender == "man"
    return True


def are_matched(db, a, b):
    like_ab = db.execute(
        "SELECT 1 FROM swipes WHERE swiper_id = ? AND target_id = ? AND liked = 1",
        (a, b),
    ).fetchone()
    like_ba = db.execute(
        "SELECT 1 FROM swipes WHERE swiper_id = ? AND target_id = ? AND liked = 1",
        (b, a),
    ).fetchone()
    return bool(like_ab and like_ba)


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        row = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            session["user_id"] = row["id"]
            return redirect(url_for("discover"))
        flash("Invalid email or password.")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        name = (request.form.get("name") or "").strip()
        if not email or not password or not name:
            flash("Please fill in all fields.")
            return render_template("signup.html")
        if get_db().execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            flash("That email is already in use.")
            return render_template("signup.html")
        db = get_db()
        db.execute(
            """
            INSERT INTO users (email, password_hash, name, age, gender, looking_for, city, bio, interests, photo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                generate_password_hash(password),
                name,
                request.form.get("age") or None,
                request.form.get("gender") or "",
                request.form.get("looking_for") or "Everyone",
                request.form.get("city") or "",
                request.form.get("bio") or "",
                request.form.get("interests") or "",
                request.form.get("photo") or "",
                datetime.utcnow().isoformat(),
            ),
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        session["user_id"] = user["id"]
        return redirect(url_for("discover"))
    return render_template("signup.html")


@app.route("/register")
def register():
    return redirect(url_for("signup"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/discover")
@login_required
def discover():
    me = current_user()
    db = get_db()
    candidates = db.execute(
        """
        SELECT * FROM users
        WHERE id != ?
          AND id NOT IN (SELECT target_id FROM swipes WHERE swiper_id = ?)
        ORDER BY id
        """,
        (me["id"], me["id"]),
    ).fetchall()
    visible = []
    for person in candidates:
        if not gender_matches(person["gender"], me["looking_for"]):
            continue
        if not gender_matches(me["gender"], person["looking_for"]):
            continue
        visible.append(
            {
                "id": person["id"],
                "name": person["name"],
                "age": person["age"],
                "city": person["city"] or "",
                "bio": person["bio"] or "",
                "interests": [i.strip() for i in (person["interests"] or "").split(",") if i.strip()],
                "photo": photo_url(person),
            }
        )
    return render_template("discover.html", cards=visible)


@app.route("/matches")
@login_required
def matches():
    me = current_user()
    db = get_db()
    rows = db.execute(
        """
        SELECT u.*
        FROM users u
        WHERE u.id != ?
          AND EXISTS (
              SELECT 1 FROM swipes s1
              WHERE s1.swiper_id = ? AND s1.target_id = u.id AND s1.liked = 1
          )
          AND EXISTS (
              SELECT 1 FROM swipes s2
              WHERE s2.swiper_id = u.id AND s2.target_id = ? AND s2.liked = 1
          )
        ORDER BY u.id
        """,
        (me["id"], me["id"], me["id"]),
    ).fetchall()
    matches = [
        {
            "id": row["id"],
            "name": row["name"],
            "city": row["city"] or "",
            "photo": photo_url(row),
        }
        for row in rows
    ]
    return render_template("matches.html", matches=matches)


@app.route("/profile")
@login_required
def profile():
    me = current_user()
    return render_template("profile.html", user=me, photo_url=photo_url)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    me = current_user()
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        age = request.form.get("age")
        age = int(age) if age not in (None, "") else None
        gender = request.form.get("gender") or ""
        looking_for = request.form.get("looking_for") or "Everyone"
        city = (request.form.get("city") or "").strip()
        bio = (request.form.get("bio") or "").strip()
        interests = (request.form.get("interests") or "").strip()
        photo_name = me["photo"]

        if not name:
            flash("Name is required.")
            return render_template("edit_profile.html", user=me)
        if age is not None and (age < 18 or age > 120):
            flash("You must be 18 or older.")
            return render_template("edit_profile.html", user=me)

        file = request.files.get("photo")
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Please upload a PNG, JPG, GIF, or WEBP photo.")
                return render_template("edit_profile.html", user=me)
            filename = secure_filename(f"{me['id']}_{file.filename}")
            file.save(UPLOAD_DIR / filename)
            photo_name = filename

        db = get_db()
        db.execute(
            """
            UPDATE users
            SET name = ?, age = ?, gender = ?, looking_for = ?, city = ?, bio = ?, interests = ?, photo = ?
            WHERE id = ?
            """,
            (name, age, gender, looking_for, city, bio, interests, photo_name, me["id"]),
        )
        db.commit()
        flash("Profile saved.")
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", user=me, photo_url=photo_url)


@app.route("/chat/<int:user_id>")
@login_required
def chat(user_id):
    me = current_user()
    db = get_db()
    other = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not other:
        flash("User not found.")
        return redirect(url_for("matches"))
    if not are_matched(db, me["id"], user_id):
        flash("You are not matched with that person.")
        return redirect(url_for("matches"))
    return render_template("chat.html", other=other, photo_url=photo_url)


@app.route("/api/discover")
@login_required
def api_discover():
    me = current_user()
    db = get_db()
    candidates = db.execute(
        """
        SELECT * FROM users
        WHERE id != ?
          AND id NOT IN (SELECT target_id FROM swipes WHERE swiper_id = ?)
        ORDER BY id
        """,
        (me["id"], me["id"]),
    ).fetchall()
    cards = []
    for person in candidates:
        if not gender_matches(person["gender"], me["looking_for"]):
            continue
        if not gender_matches(me["gender"], person["looking_for"]):
            continue
        cards.append(
            {
                "id": person["id"],
                "name": person["name"],
                "age": person["age"],
                "city": person["city"] or "",
                "bio": person["bio"] or "",
                "interests": [i.strip() for i in (person["interests"] or "").split(",") if i.strip()],
                "photo": photo_url(person),
            }
        )
    return jsonify({"cards": cards})


@app.route("/api/swipe", methods=["POST"])
@login_required
def api_swipe():
    me = current_user()
    data = request.get_json(silent=True) or {}
    target_id = data.get("target_id")
    liked = 1 if data.get("liked") else 0
    if not isinstance(target_id, int) or target_id == me["id"]:
        return jsonify({"error": "Invalid person"}), 400
    db = get_db()
    target = db.execute("SELECT * FROM users WHERE id = ?", (target_id,)).fetchone()
    if not target:
        return jsonify({"error": "Person not found"}), 404
    db.execute(
        """
        INSERT INTO swipes (swiper_id, target_id, liked, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(swiper_id, target_id) DO UPDATE SET liked = excluded.liked
        """,
        (me["id"], target_id, liked, datetime.utcnow().isoformat()),
    )
    db.commit()
    matched = bool(liked) and are_matched(db, me["id"], target_id)
    return jsonify(
        {
            "ok": True,
            "matched": matched,
            "match": {"id": target["id"], "name": target["name"], "photo": photo_url(target)} if matched else None,
        }
    )


@app.route("/api/messages/<int:user_id>")
@login_required
def api_messages(user_id):
    me = current_user()
    db = get_db()
    if not are_matched(db, me["id"], user_id):
        return jsonify({"error": "Not matched"}), 403
    after_id = request.args.get("after", type=int) or 0
    rows = db.execute(
        """
        SELECT id, sender_id, receiver_id, body, created_at
        FROM messages
        WHERE id > ?
          AND ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
        ORDER BY id
        """,
        (after_id, me["id"], user_id, user_id, me["id"]),
    ).fetchall()
    typing_state = TYPING_STATE.get((user_id, me["id"]))
    typing_active = bool(typing_state and typing_state.get("typing") and (time.time() - typing_state.get("updated_at", 0) <= 5))
    payload = {
        "messages": [
            {
                "id": row["id"],
                "mine": row["sender_id"] == me["id"],
                "body": row["body"],
                "created_at": row["created_at"],
            }
            for row in rows
        ],
        "typing": typing_active,
    }
    return jsonify(payload)


@app.route("/api/messages/<int:user_id>/typing", methods=["POST"])
@login_required
def api_set_typing(user_id):
    me = current_user()
    db = get_db()
    if not are_matched(db, me["id"], user_id):
        return jsonify({"error": "Not matched"}), 403

    data = request.get_json(silent=True) or {}
    typing = bool(data.get("typing"))
    if typing:
        TYPING_STATE[(me["id"], user_id)] = {"typing": True, "updated_at": time.time()}
    else:
        TYPING_STATE.pop((me["id"], user_id), None)
    return jsonify({"ok": True, "typing": typing})


@app.route("/api/messages/<int:user_id>", methods=["POST"])
@login_required
def api_send_message(user_id):
    me = current_user()
    db = get_db()
    if not are_matched(db, me["id"], user_id):
        return jsonify({"error": "Not matched"}), 403

    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()
    if not body:
        return jsonify({"error": "Message cannot be empty"}), 400
    if len(body) > 1000:
        return jsonify({"error": "Message is too long"}), 400

    cursor = db.execute(
        "INSERT INTO messages (sender_id, receiver_id, body, created_at) VALUES (?, ?, ?, ?)",
        (me["id"], user_id, body, datetime.utcnow().isoformat()),
    )
    db.commit()
    return jsonify({"ok": True, "id": cursor.lastrowid})


init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
