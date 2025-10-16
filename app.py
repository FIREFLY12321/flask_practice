from __future__ import annotations

import sqlite3
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config.update(
    SECRET_KEY="0e0524e4bb882c71056583e235b9c1c2",
    DATABASE=str(INSTANCE_DIR / "blog.db"),
)

PASSWORD_HASH_METHOD = "pbkdf2:sha256"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception: Exception | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    with sqlite3.connect(app.config["DATABASE"]) as db:
        with app.open_resource("schema.sql") as schema:
            db.executescript(schema.read().decode("utf-8"))


def seed_data() -> None:
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.row_factory = sqlite3.Row
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()
        if user:
            return

        password_hash = generate_password_hash(
            "luxepass", method=PASSWORD_HASH_METHOD, salt_length=16
        )
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("aurelia", "aurelia@example.com", password_hash),
        )
        user_id = cursor.lastrowid
        posts = [
            (
                "掠影巴黎：月色與香檳",
                "在巴黎的夜色之中，與光之城最私密的藝文場域相遇，從塞納河遊船到小眾畫廊，一場僅獻給知音的冒險。",
            ),
            (
                "京都的天鵝絨黃昏",
                "穿梭嵐山竹林後的靜謐茶席，與職人手中的一針一線，構築出一次只在金色霧光裡發生的旅程。",
            ),
            (
                "聖托里尼金色時分",
                "在懸崖別墅的無邊際泳池前等待夕陽，伴隨愛琴海的鹹味與微風，紀錄最浪漫的一刻。",
            ),
        ]
        db.executemany(
            "INSERT INTO posts (user_id, title, body) VALUES (?, ?, ?)",
            [(user_id, title, body) for title, body in posts],
        )
        db.commit()


with app.app_context():
    init_db()
    seed_data()


@app.before_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db()
            .execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
            .fetchone()
        )


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("請先登入以使用此功能。", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def get_post(post_id: int, check_author: bool = True) -> sqlite3.Row:
    post = (
        get_db()
        .execute(
            """
            SELECT posts.id,
                   posts.title,
                   posts.body,
                   posts.created_at,
                   posts.user_id,
                   users.username
            FROM posts
            JOIN users ON posts.user_id = users.id
            WHERE posts.id = ?
            """,
            (post_id,),
        )
        .fetchone()
    )
    if post is None:
        abort(404, "找不到這篇文章。")
    if check_author and post["user_id"] != g.user["id"]:
        abort(403)
    return post


@app.template_filter("format_date")
def format_date(value: str | None) -> str:
    if not value:
        return ""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y/%m/%d")
        except ValueError:
            continue
    return value


@app.route("/")
def index():
    posts = (
        get_db()
        .execute(
            """
            SELECT posts.id,
                   posts.title,
                   posts.body,
                   posts.created_at,
                   posts.user_id,
                   users.username
            FROM posts
            JOIN users ON posts.user_id = users.id
            ORDER BY posts.created_at DESC
            """
        )
        .fetchall()
    )
    return render_template("home.html", posts=posts)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = None
        if not username:
            error = "請輸入使用者名稱。"
        elif not email:
            error = "請輸入電子郵件。"
        elif not password or len(password) < 6:
            error = "請設定至少六個字元的密碼。"

        if error is None:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (
                        username,
                        email,
                        generate_password_hash(
                            password, method=PASSWORD_HASH_METHOD, salt_length=16
                        ),
                    ),
                )
                db.commit()
                flash("註冊成功，請登入。", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "帳號或電子郵件已被使用，請換一個試試。"

        flash(error, "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT id, username, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash(f"歡迎回來，{user['username']}！", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

        flash("電子郵件或密碼不正確。", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("您已成功登出。", "info")
    return redirect(url_for("index"))


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()

        if not title:
            flash("請為文章設定標題。", "danger")
        elif not body:
            flash("內容不可為空。", "danger")
        else:
            db = get_db()
            cursor = db.execute(
                "INSERT INTO posts (user_id, title, body) VALUES (?, ?, ?)",
                (g.user["id"], title, body),
            )
            db.commit()
            flash("文章已發佈！", "success")
            return redirect(url_for("post_detail", post_id=cursor.lastrowid))

    return render_template("new_post.html")


@app.route("/post/<int:post_id>")
def post_detail(post_id: int):
    post = get_post(post_id, check_author=False)
    return render_template("post_detail.html", post=post)


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id: int):
    post = get_post(post_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()

        if not title:
            flash("請為文章設定標題。", "danger")
        elif not body:
            flash("內容不可為空。", "danger")
        else:
            db = get_db()
            db.execute(
                "UPDATE posts SET title = ?, body = ? WHERE id = ?",
                (title, body, post_id),
            )
            db.commit()
            flash("文章已更新。", "success")
            return redirect(url_for("post_detail", post_id=post_id))

    return render_template("edit_post.html", post=post)


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id: int):
    get_post(post_id)
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    flash("文章已刪除。", "info")
    return redirect(url_for("index"))


@app.context_processor
def inject_globals():
    return {
        "current_year": date.today().year,
        "current_user": getattr(g, "user", None),
    }


if __name__ == "__main__":
    app.run()
