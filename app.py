import json
import os
import secrets
from collections import Counter
from functools import wraps
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    redirect,
    send_file,
    send_from_directory,
    url_for,
    session
)
from dotenv import load_dotenv
from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from code_analyzer import analyze_code
from database import (
    ensure_configured_admin,
    get_db_connection,
    init_db,
    now_text
)
from deepseek_api import handle_question
from pet_generator.build_petpack import (
    MAX_FILES,
    PetpackInputError,
    PetpackServiceError,
    SUPPORTED_ROLES,
    SUPPORTED_SUFFIXES,
    build_petpack
)


load_dotenv()

app = Flask(__name__)

NEON_RAIL_RUNNER_BUILD = (
    Path(app.root_path)
    / "static"
    / "games"
    / "neon-rail-runner"
)
NEON_RAIL_RUNNER_KEY = "neon-rail-runner"
NEON_RAIL_LEADERBOARD_LIMIT = 20
NEON_RAIL_MAX_SCORE = 100_000_000

DESKTOP_PET_PLAYER_VERSION = "1.1.0"

# Flask 使用 SECRET_KEY 对 Session 登录信息进行签名
app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY",
    "dev-only-change-this-secret-key"
)

# 阻止网页中的 JavaScript 直接读取 Session Cookie
app.config["SESSION_COOKIE_HTTPONLY"] = True

# 降低部分跨站请求携带 Cookie 的风险
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# 公网部署时只通过 HTTPS 发送登录 Cookie
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("APP_ENV", "development")
    == "production"
)

# 桌宠资源包支持多张动画素材，单次请求最多约 36 MB。
# 生成器内部还会分别检查单文件、总上传量和解码后像素数。
app.config["MAX_CONTENT_LENGTH"] = (
    36 * 1024 * 1024
)

# 网站启动时检查并初始化数据库
init_db()

admin_username = os.getenv(
    "ADMIN_USERNAME",
    ""
).strip()
admin_password_hash = os.getenv(
    "ADMIN_PASSWORD_HASH",
    ""
).strip()

if bool(admin_username) != bool(admin_password_hash):
    raise RuntimeError(
        "ADMIN_USERNAME and ADMIN_PASSWORD_HASH must be configured together."
    )

ensure_configured_admin(
    admin_username,
    admin_password_hash
)


def normalize_script_tags(raw_tags):
    """把用户输入的标签整理为短小、去重的列表。"""
    if isinstance(raw_tags, str):
        normalized_text = raw_tags

        for separator in ("，", "\n", "#"):
            normalized_text = normalized_text.replace(
                separator,
                ","
            )

        candidates = normalized_text.split(",")

    elif isinstance(raw_tags, list):
        candidates = raw_tags

    else:
        candidates = []

    tags = []
    seen = set()

    for candidate in candidates:
        tag = str(candidate).strip()

        if (
            not tag
            or len(tag) > 20
            or tag.casefold() in seen
        ):
            continue

        tags.append(tag)
        seen.add(tag.casefold())

        if len(tags) >= 6:
            break

    return tags


def parse_script_tags(value):
    """安全解析数据库中保存的 JSON 标签。"""
    if not value:
        return []

    try:
        parsed = json.loads(value)

    except (
        json.JSONDecodeError,
        TypeError
    ):
        return []

    return normalize_script_tags(parsed)


def is_trusted_curated_install_url(url):
    """只允许精选条目跳转到已审核来源站的用户脚本文件。"""
    if not isinstance(url, str):
        return False

    parsed_url = urlsplit(url)

    if (
        parsed_url.scheme != "https"
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.query
        or parsed_url.fragment
    ):
        return False

    trusted_paths = {
        "update.greasyfork.org": "/scripts/",
        "scriptcat.org": "/scripts/code/"
    }
    required_prefix = trusted_paths.get(
        parsed_url.hostname
    )

    return (
        required_prefix is not None
        and parsed_url.path.startswith(
            required_prefix
        )
        and parsed_url.path.endswith(
            ".user.js"
        )
    )


# =========================
# 普通用户登录保护
# =========================
def login_required(view_function):
    """
    只有已登录用户才能访问被保护的路由。
    """

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view


# =========================
# 管理员登录保护
# =========================
def admin_required(view_function):
    """
    只有管理员才能访问被保护的路由。
    """

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if session.get("user_role") != "admin":
            return redirect(url_for("login"))

        return view_function(*args, **kwargs)

    return wrapped_view


# =========================
# 普通用户注册
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    # 已经登录时，不再显示注册页面
    if session.get("user_id") is not None:
        return redirect(url_for("index"))

    error = ""
    username = ""

    if request.method == "POST":
        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if len(username) < 3:
            error = "用户名至少需要 3 个字符。"

        elif len(username) > 30:
            error = "用户名最多只能有 30 个字符。"

        elif len(password) < 8:
            error = "密码至少需要 8 个字符。"

        elif password != confirm_password:
            error = "两次输入的密码不一致。"

        else:
            conn = get_db_connection()

            try:
                existing_user = conn.execute("""
                    SELECT id
                    FROM users
                    WHERE username = ?
                """, (username,)).fetchone()

                if existing_user is not None:
                    error = "这个用户名已经被使用。"

                else:
                    current_time = now_text()

                    password_hash = generate_password_hash(
                        password
                    )

                    cursor = conn.execute("""
                        INSERT INTO users (
                            username,
                            email,
                            password_hash,
                            role,
                            is_active,
                            created_at,
                            updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        RETURNING id
                    """, (
                        username,
                        None,
                        password_hash,
                        "user",
                        1,
                        current_time,
                        current_time
                    ))

                    # 获取刚刚创建的用户编号
                    user_id = cursor.fetchone()["id"]

                    conn.commit()

            finally:
                conn.close()

            # 注册成功后自动登录
            if not error:
                session.clear()

                session["user_id"] = user_id
                session["username"] = username
                session["user_role"] = "user"

                return redirect(url_for("index"))

    return render_template(
        "register.html",
        error=error,
        username=username
    )


# =========================
# 普通用户登录
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id") is not None:
        return redirect(url_for("index"))

    error = ""
    username = ""

    if request.method == "POST":
        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db_connection()

        try:
            user = conn.execute("""
                SELECT
                    id,
                    username,
                    password_hash,
                    role,
                    is_active
                FROM users
                WHERE username = ?
            """, (username,)).fetchone()

        finally:
            conn.close()

        login_is_valid = (
            user is not None
            and user["is_active"] == 1
            and check_password_hash(
                user["password_hash"],
                password
            )
        )

        if login_is_valid:
            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["user_role"] = user["role"]

            if user["role"] == "admin":
                return redirect(
                    url_for("admin_scripts")
                )

            return redirect(url_for("index"))

        error = "用户名或密码错误，或者账号已停用。"

    return render_template(
        "login.html",
        error=error,
        username=username
    )


# =========================
# 普通用户退出登录
# =========================
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()

    return redirect(url_for("index"))


# =========================
# 我的投稿
# =========================
@app.route("/my/scripts")
@login_required
def my_scripts():
    conn = get_db_connection()

    try:
        script_list = conn.execute("""
            SELECT *
            FROM scripts
            WHERE user_id = ?
            ORDER BY id DESC
        """, (
            session["user_id"],
        )).fetchall()

    finally:
        conn.close()

    return render_template(
        "my_scripts.html",
        scripts=script_list
    )


# 兼容旧书签：管理员与普通用户统一使用 /login。
@app.route("/admin/login")
def legacy_admin_login():
    return redirect(url_for("login"))


# =========================
# 网站首页
# =========================
@app.route("/")
def index():
    conn = get_db_connection()

    try:
        approved_count = conn.execute("""
            SELECT COUNT(*) AS total
            FROM scripts
            WHERE status = ?
        """, (
            "approved",
        )).fetchone()["total"]

        pending_count = conn.execute("""
            SELECT COUNT(*) AS total
            FROM scripts
            WHERE status = ?
        """, (
            "pending",
        )).fetchone()["total"]

        category_count = conn.execute("""
            SELECT COUNT(
                DISTINCT category
            ) AS total
            FROM scripts
            WHERE status = ?
              AND category IS NOT NULL
              AND TRIM(category) != ''
        """, (
            "approved",
        )).fetchone()["total"]

        latest_scripts = conn.execute("""
            SELECT
                id,
                title,
                description,
                language,
                category,
                created_at
            FROM scripts
            WHERE status = ?
            ORDER BY id DESC
            LIMIT 3
        """, (
            "approved",
        )).fetchall()

    finally:
        conn.close()

    stats = {
        "approved_count": approved_count,
        "pending_count": pending_count,
        "category_count": category_count
    }

    return render_template(
        "index.html",
        stats=stats,
        latest_scripts=latest_scripts
    )


# =========================
# 托管平台健康检查
# =========================
@app.route("/health")
def health():
    conn = get_db_connection()

    try:
        conn.execute(
            "SELECT 1"
        ).fetchone()

    finally:
        conn.close()

    return {
        "status": "ok"
    }


# =========================
# 用户脚本启动器安装指南
# =========================
@app.route("/script-managers")
def script_managers():
    return render_template(
        "script_managers.html"
    )


# =========================
# Neon Rail Runner WebGL 游戏
# =========================
def get_neon_rail_leaderboard(conn, current_user_id=None):
    """读取最高分排名，并在登录时附带当前用户的名次。"""
    ranking_query = """
        WITH ranked_scores AS (
            SELECT
                game_scores.user_id,
                users.username,
                game_scores.best_score,
                game_scores.achieved_at,
                DENSE_RANK() OVER (
                    ORDER BY game_scores.best_score DESC
                ) AS rank
            FROM game_scores
            INNER JOIN users
                ON users.id = game_scores.user_id
            WHERE game_scores.game_key = ?
              AND users.is_active = 1
        )
    """

    top_rows = conn.execute(
        ranking_query
        + """
            SELECT *
            FROM ranked_scores
            ORDER BY rank ASC, achieved_at ASC, username ASC
            LIMIT ?
        """,
        (
            NEON_RAIL_RUNNER_KEY,
            NEON_RAIL_LEADERBOARD_LIMIT
        )
    ).fetchall()

    leaderboard = [
        {
            "rank": int(row["rank"]),
            "username": row["username"],
            "best_score": int(row["best_score"])
        }
        for row in top_rows
    ]

    current_user = None

    if current_user_id is not None:
        current_row = conn.execute(
            ranking_query
            + """
                SELECT *
                FROM ranked_scores
                WHERE user_id = ?
            """,
            (
                NEON_RAIL_RUNNER_KEY,
                current_user_id
            )
        ).fetchone()

        if current_row is not None:
            current_user = {
                "rank": int(current_row["rank"]),
                "username": current_row["username"],
                "best_score": int(current_row["best_score"])
            }

    return {
        "leaderboard": leaderboard,
        "current_user": current_user
    }


@app.route("/games/neon-rail-runner")
def neon_rail_runner():
    score_submission_token = ""

    if session.get("user_id") is not None:
        score_submission_token = session.get(
            "neon_rail_score_token",
            ""
        )

        if not score_submission_token:
            score_submission_token = secrets.token_urlsafe(32)
            session["neon_rail_score_token"] = score_submission_token

    return render_template(
        "neon_rail_runner.html",
        score_submission_token=score_submission_token
    )


@app.route("/api/games/neon-rail-runner/leaderboard")
def neon_rail_runner_leaderboard():
    conn = get_db_connection()

    try:
        ranking = get_neon_rail_leaderboard(
            conn,
            session.get("user_id")
        )

    finally:
        conn.close()

    return jsonify({
        "success": True,
        **ranking
    })


@app.route(
    "/api/games/neon-rail-runner/scores",
    methods=["POST"]
)
def submit_neon_rail_runner_score():
    user_id = session.get("user_id")

    if user_id is None:
        return jsonify({
            "success": False,
            "message": "请先登录，再参与排行榜。"
        }), 401

    expected_token = session.get(
        "neon_rail_score_token",
        ""
    )
    supplied_token = request.headers.get(
        "X-Game-Token",
        ""
    )

    if (
        not expected_token
        or not supplied_token
        or not secrets.compare_digest(
            expected_token,
            supplied_token
        )
    ):
        return jsonify({
            "success": False,
            "message": "成绩提交凭证已失效，请刷新游戏页面后重试。"
        }), 403

    payload = request.get_json(silent=True)
    score = (
        payload.get("score")
        if isinstance(payload, dict)
        else None
    )

    if (
        isinstance(score, bool)
        or not isinstance(score, int)
        or score < 0
        or score > NEON_RAIL_MAX_SCORE
    ):
        return jsonify({
            "success": False,
            "message": "成绩格式不正确。"
        }), 400

    current_time = now_text()
    conn = get_db_connection()

    try:
        previous_row = conn.execute("""
            SELECT best_score
            FROM game_scores
            WHERE game_key = ?
              AND user_id = ?
        """, (
            NEON_RAIL_RUNNER_KEY,
            user_id
        )).fetchone()

        previous_best = (
            int(previous_row["best_score"])
            if previous_row is not None
            else None
        )

        conn.execute("""
            INSERT INTO game_scores (
                game_key,
                user_id,
                best_score,
                achieved_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (game_key, user_id)
            DO UPDATE SET
                best_score = excluded.best_score,
                achieved_at = excluded.achieved_at,
                updated_at = excluded.updated_at
            WHERE excluded.best_score > game_scores.best_score
        """, (
            NEON_RAIL_RUNNER_KEY,
            user_id,
            score,
            current_time,
            current_time
        ))

        conn.commit()

        saved_row = conn.execute("""
            SELECT best_score
            FROM game_scores
            WHERE game_key = ?
              AND user_id = ?
        """, (
            NEON_RAIL_RUNNER_KEY,
            user_id
        )).fetchone()

        saved_best = int(saved_row["best_score"])
        ranking = get_neon_rail_leaderboard(
            conn,
            user_id
        )

    finally:
        conn.close()

    return jsonify({
        "success": True,
        "submitted_score": score,
        "best_score": saved_best,
        "is_new_best": (
            previous_best is None
            or score > previous_best
        ),
        **ranking
    })


@app.route(
    "/games/neon-rail-runner/play/",
    defaults={"filename": "index.html"}
)
@app.route(
    "/games/neon-rail-runner/play/<path:filename>"
)
def neon_rail_runner_file(filename):
    """提供 Unity WebGL 文件，并为压缩资源设置正确响应头。"""
    response = send_from_directory(
        NEON_RAIL_RUNNER_BUILD,
        filename
    )

    if filename.endswith(".gz"):
        uncompressed_name = filename[:-3]
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Vary"] = "Accept-Encoding"

        if uncompressed_name.endswith(".wasm"):
            response.headers["Content-Type"] = (
                "application/wasm"
            )
        elif uncompressed_name.endswith(".js"):
            response.headers["Content-Type"] = (
                "application/javascript; charset=utf-8"
            )
        elif uncompressed_name.endswith(".data"):
            response.headers["Content-Type"] = (
                "application/octet-stream"
            )

    if filename == "index.html":
        response.headers["Cache-Control"] = (
            "no-cache"
        )
    else:
        response.headers["Cache-Control"] = (
            "public, max-age=604800"
        )

    return response


# =========================
# 上传脚本
# =========================
@app.route(
    "/upload",
    methods=["GET", "POST"]
)
@login_required
def upload():
    if request.method == "GET":
        return render_template(
            "upload.html",
            current_username=session.get(
                "username"
            )
        )

    title = request.form.get(
        "title",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    language = request.form.get(
        "language",
        ""
    ).strip()

    category = request.form.get(
        "category",
        ""
    ).strip()

    tags = normalize_script_tags(
        request.form.get(
            "tags",
            ""
        )
    )

    code = request.form.get(
        "code",
        ""
    ).strip()

    if not title or not language or not code:
        return (
            "标题、脚本语言和代码不能为空。",
            400
        )

    analysis = analyze_code(code)

    if not analysis["success"]:
        return analysis["error"], 400

    created_at = now_text()

    warnings_json = json.dumps(
        analysis["warnings"],
        ensure_ascii=False
    )

    conn = get_db_connection()

    try:
        conn.execute("""
            INSERT INTO scripts (
                user_id,
                author_name,
                title,
                description,
                language,
                category,
                tags,
                code,
                status,
                line_count,
                non_empty_line_count,
                warnings,
                created_at,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
        """, (
            session["user_id"],
            session["username"],
            title,
            description,
            language,
            category,
            json.dumps(
                tags,
                ensure_ascii=False
            ),
            code,
            "pending",
            analysis["line_count"],
            analysis[
                "non_empty_line_count"
            ],
            warnings_json,
            created_at,
            created_at
        ))

        conn.commit()

    finally:
        conn.close()

    return redirect(url_for("my_scripts"))


# =========================
# 公开脚本列表
# =========================
@app.route("/scripts")
def scripts():
    search = request.args.get(
        "q",
        ""
    ).strip()

    category = request.args.get(
        "category",
        ""
    ).strip()

    language = request.args.get(
        "language",
        ""
    ).strip()

    tag = request.args.get(
        "tag",
        ""
    ).strip()[:20]

    page = request.args.get(
        "page",
        1,
        type=int
    )

    if page < 1:
        page = 1

    per_page = 10
    offset = (page - 1) * per_page

    where_clauses = [
        "status = 'approved'"
    ]

    params = []

    if search:
        where_clauses.append(
            "("
            "title LIKE ? "
            "OR description LIKE ? "
            "OR code LIKE ? "
            "OR tags LIKE ? "
            "OR author_name LIKE ?"
            ")"
        )

        keyword = f"%{search}%"

        params.extend([
            keyword,
            keyword,
            keyword,
            keyword,
            keyword
        ])

    if category:
        where_clauses.append(
            "category = ?"
        )

        params.append(category)

    if language:
        where_clauses.append(
            "language = ?"
        )

        params.append(language)

    if tag:
        tag_json = json.dumps(
            tag,
            ensure_ascii=False
        )

        where_clauses.append(
            "tags LIKE ?"
        )

        params.append(
            f"%{tag_json}%"
        )

    where_sql = " AND ".join(
        where_clauses
    )

    conn = get_db_connection()

    try:
        count_sql = (
            "SELECT COUNT(*) AS total "
            "FROM scripts "
            f"WHERE {where_sql}"
        )

        total = conn.execute(
            count_sql,
            params
        ).fetchone()["total"]

        total_pages = (
            total + per_page - 1
        ) // per_page

        if (
            page > total_pages
            and total_pages > 0
        ):
            page = total_pages
            offset = (
                page - 1
            ) * per_page

        sql = f"""
            SELECT *
            FROM scripts
            WHERE {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """

        script_rows = conn.execute(
            sql,
            params + [
                per_page,
                offset
            ]
        ).fetchall()

        script_list = []

        for row in script_rows:
            script = dict(row)
            script["tags_list"] = parse_script_tags(
                script.get("tags")
            )
            script_list.append(script)

        category_list = conn.execute("""
            SELECT DISTINCT category
            FROM scripts
            WHERE status = 'approved'
              AND category IS NOT NULL
              AND category != ''
            ORDER BY category
        """).fetchall()

        language_list = conn.execute("""
            SELECT DISTINCT language
            FROM scripts
            WHERE status = 'approved'
              AND language IS NOT NULL
              AND language != ''
            ORDER BY language
        """).fetchall()

        tag_rows = conn.execute("""
            SELECT tags
            FROM scripts
            WHERE status = 'approved'
              AND tags IS NOT NULL
              AND tags != '[]'
        """).fetchall()

    finally:
        conn.close()

    tag_counts = Counter()

    for row in tag_rows:
        tag_counts.update(
            parse_script_tags(row["tags"])
        )

    tag_list = [
        {
            "name": name,
            "count": count
        }
        for name, count in sorted(
            tag_counts.items(),
            key=lambda item: (
                -item[1],
                item[0]
            )
        )
    ]

    return render_template(
        "scripts.html",
        scripts=script_list,
        search=search,
        selected_category=category,
        selected_language=language,
        selected_tag=tag,
        categories=category_list,
        languages=language_list,
        tags=tag_list,
        current_page=page,
        total_pages=total_pages
    )


# =========================
# 单个脚本详情页
# =========================
@app.route(
    "/scripts/<int:script_id>"
)
def script_detail(script_id):
    conn = get_db_connection()

    try:
        script = conn.execute("""
            SELECT *
            FROM scripts
            WHERE id = ?
              AND status = 'approved'
        """, (
            script_id,
        )).fetchone()

        if script is None:
            return (
                "这个脚本不存在，或者尚未审核通过。",
                404
            )

        # 每次打开详情页，浏览次数增加 1
        conn.execute("""
            UPDATE scripts
            SET view_count = view_count + 1
            WHERE id = ?
        """, (
            script_id,
        ))

        conn.commit()

        # 读取更新后的脚本数据
        script = conn.execute("""
            SELECT *
            FROM scripts
            WHERE id = ?
              AND status = 'approved'
        """, (
            script_id,
        )).fetchone()

        user_has_liked = False
        user_has_favorited = False

        # 登录用户才需要检查点赞和收藏状态
        if session.get("user_id") is not None:
            user_id = session["user_id"]

            like_record = conn.execute("""
                SELECT id
                FROM script_likes
                WHERE script_id = ?
                  AND user_id = ?
            """, (
                script_id,
                user_id
            )).fetchone()

            favorite_record = conn.execute("""
                SELECT id
                FROM script_favorites
                WHERE script_id = ?
                  AND user_id = ?
            """, (
                script_id,
                user_id
            )).fetchone()

            user_has_liked = (
                like_record is not None
            )

            user_has_favorited = (
                favorite_record is not None
            )

    finally:
        conn.close()

    script = dict(script)
    script["tags_list"] = parse_script_tags(
        script.get("tags")
    )

    try:
        warnings = json.loads(
            script["warnings"] or "[]"
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):
        warnings = []

    return render_template(
        "script_detail.html",
        script=script,
        warnings=warnings,
        user_has_liked=user_has_liked,
        user_has_favorited=user_has_favorited
    )


# =========================
# 下载脚本文件
# =========================
SCRIPT_DOWNLOAD_FORMATS = {
    "python": (
        ".py",
        "text/x-python"
    ),
    "powershell": (
        ".ps1",
        "text/plain"
    ),
    "javascript": (
        ".js",
        "text/javascript"
    ),
    "bash": (
        ".sh",
        "text/x-shellscript"
    ),
    "html": (
        ".html",
        "text/html"
    ),
    "css": (
        ".css",
        "text/css"
    ),
    "sql": (
        ".sql",
        "application/sql"
    ),
    "java": (
        ".java",
        "text/x-java-source"
    ),
    "c": (
        ".c",
        "text/x-c"
    ),
    "c++": (
        ".cpp",
        "text/x-c++src"
    ),
    "cpp": (
        ".cpp",
        "text/x-c++src"
    )
}


def safe_script_download_name(
    title,
    extension
):
    cleaned_title = "".join(
        character
        if (
            character not in '<>:"/\\|?*'
            and ord(character) >= 32
        )
        else "_"
        for character in (title or "")
    ).strip(" .")

    if not cleaned_title:
        cleaned_title = "script"

    return (
        cleaned_title[:80]
        + extension
    )


@app.route(
    "/scripts/<int:script_id>/download"
)
def download_script(script_id):
    conn = get_db_connection()

    try:
        script = conn.execute("""
            SELECT
                id,
                title,
                language,
                code,
                install_url
            FROM scripts
            WHERE id = ?
              AND status = 'approved'
        """, (
            script_id,
        )).fetchone()

        if script is None:
            return (
                "这个脚本不存在，或者尚未审核通过。",
                404
            )

        conn.execute("""
            UPDATE scripts
            SET download_count = download_count + 1
            WHERE id = ?
        """, (
            script_id,
        ))

        conn.commit()

    finally:
        conn.close()

    if is_trusted_curated_install_url(
        script["install_url"]
    ):
        return redirect(
            script["install_url"],
            code=302
        )

    language_key = (
        script["language"]
        or ""
    ).strip().lower()

    extension, mimetype = (
        SCRIPT_DOWNLOAD_FORMATS.get(
            language_key,
            (
                ".txt",
                "text/plain"
            )
        )
    )

    download_name = (
        safe_script_download_name(
            script["title"],
            extension
        )
    )

    # Windows PowerShell 5.1 使用 BOM 时能更稳定地
    # 识别中文；其他脚本保持标准 UTF-8，避免影响
    # Bash 文件首行的 shebang。
    output_encoding = (
        "utf-8-sig"
        if language_key == "powershell"
        else "utf-8"
    )

    script_bytes = (
        script["code"]
        or ""
    ).encode(output_encoding)

    return send_file(
        BytesIO(script_bytes),
        mimetype=mimetype,
        as_attachment=True,
        download_name=download_name
    )


# =========================
# 记录复制代码次数
# =========================
@app.route(
    "/scripts/<int:script_id>/copy",
    methods=["POST"]
)
def record_script_copy(script_id):
    conn = get_db_connection()

    try:
        script = conn.execute("""
            SELECT id
            FROM scripts
            WHERE id = ?
              AND status = 'approved'
        """, (
            script_id,
        )).fetchone()

        if script is None:
            return {
                "success": False,
                "message": "这个脚本不存在。"
            }, 404

        conn.execute("""
            UPDATE scripts
            SET copy_count = copy_count + 1
            WHERE id = ?
        """, (
            script_id,
        ))

        conn.commit()

        updated_script = conn.execute("""
            SELECT copy_count
            FROM scripts
            WHERE id = ?
        """, (
            script_id,
        )).fetchone()

        updated_copy_count = updated_script[
            "copy_count"
        ]

    finally:
        conn.close()

    return {
        "success": True,
        "copy_count": updated_copy_count
    }


# =========================
# 点赞或取消点赞
# =========================
@app.route(
    "/scripts/<int:script_id>/like",
    methods=["POST"]
)
@login_required
def toggle_script_like(script_id):
    user_id = session["user_id"]

    conn = get_db_connection()

    try:
        # 只允许给已经审核通过的脚本点赞
        script = conn.execute("""
            SELECT id
            FROM scripts
            WHERE id = ?
              AND status = 'approved'
        """, (
            script_id,
        )).fetchone()

        if script is None:
            return {
                "success": False,
                "message": "这个脚本不存在。"
            }, 404

        # 检查当前用户是否已经点过赞
        existing_like = conn.execute("""
            SELECT id
            FROM script_likes
            WHERE script_id = ?
              AND user_id = ?
        """, (
            script_id,
            user_id
        )).fetchone()

        if existing_like is None:
            # 没有点赞记录，就新增一条
            conn.execute("""
                INSERT INTO script_likes (
                    script_id,
                    user_id,
                    created_at
                )
                VALUES (?, ?, ?)
            """, (
                script_id,
                user_id,
                now_text()
            ))

            liked = True

        else:
            # 已经点过赞，就删除点赞记录
            conn.execute("""
                DELETE FROM script_likes
                WHERE script_id = ?
                  AND user_id = ?
            """, (
                script_id,
                user_id
            ))

            liked = False

        # 重新统计这个脚本的真实点赞数量
        like_count = conn.execute("""
            SELECT COUNT(*) AS total
            FROM script_likes
            WHERE script_id = ?
        """, (
            script_id,
        )).fetchone()["total"]

        # 把统计结果同步到 scripts 表
        conn.execute("""
            UPDATE scripts
            SET like_count = ?
            WHERE id = ?
        """, (
            like_count,
            script_id
        ))

        conn.commit()

    finally:
        conn.close()

    return {
        "success": True,
        "liked": liked,
        "like_count": like_count
    }

# =========================
# 收藏或取消收藏
# =========================
@app.route(
    "/scripts/<int:script_id>/favorite",
    methods=["POST"]
)
@login_required
def toggle_script_favorite(script_id):
    user_id = session["user_id"]

    conn = get_db_connection()

    try:
        # 只能收藏已经审核通过的脚本
        script = conn.execute("""
            SELECT id
            FROM scripts
            WHERE id = ?
              AND status = 'approved'
        """, (
            script_id,
        )).fetchone()

        if script is None:
            return {
                "success": False,
                "message": "这个脚本不存在。"
            }, 404

        existing_favorite = conn.execute("""
            SELECT id
            FROM script_favorites
            WHERE script_id = ?
              AND user_id = ?
        """, (
            script_id,
            user_id
        )).fetchone()

        if existing_favorite is None:
            conn.execute("""
                INSERT INTO script_favorites (
                    script_id,
                    user_id,
                    created_at
                )
                VALUES (?, ?, ?)
            """, (
                script_id,
                user_id,
                now_text()
            ))

            favorited = True

        else:
            conn.execute("""
                DELETE FROM script_favorites
                WHERE script_id = ?
                  AND user_id = ?
            """, (
                script_id,
                user_id
            ))

            favorited = False

        conn.commit()

    finally:
        conn.close()

    return {
        "success": True,
        "favorited": favorited
    }


# =========================
# 我的收藏
# =========================
@app.route("/my/favorites")
@login_required
def my_favorites():
    user_id = session["user_id"]

    conn = get_db_connection()

    try:
        favorite_scripts = conn.execute("""
            SELECT
                scripts.*,
                script_favorites.created_at
                    AS favorited_at
            FROM script_favorites
            INNER JOIN scripts
                ON scripts.id =
                   script_favorites.script_id
            WHERE script_favorites.user_id = ?
              AND scripts.status = 'approved'
            ORDER BY script_favorites.id DESC
        """, (
            user_id,
        )).fetchall()

    finally:
        conn.close()

    return render_template(
        "my_favorites.html",
        scripts=favorite_scripts
    )


# =========================
# 桌宠工坊
# =========================
@app.route("/pet-generator")
def pet_generator():
    return render_template(
        "pet_generator.html",
        max_files=MAX_FILES,
        player_version=(
            DESKTOP_PET_PLAYER_VERSION
        )
    )


@app.route("/downloads/desktop-pet-player")
def download_desktop_pet_player():
    player_path = (
        Path(app.root_path)
        / "static"
        / "downloads"
        / "桌宠播放器.exe"
    )

    if not player_path.is_file():
        return "桌宠播放器暂时不可用。", 404

    response = send_file(
        player_path,
        as_attachment=True,
        download_name=(
            "桌宠播放器-v"
            + DESKTOP_PET_PLAYER_VERSION
            + ".exe"
        ),
        max_age=0
    )

    response.headers["Cache-Control"] = (
        "no-store, max-age=0"
    )
    response.headers[
        "X-Desktop-Pet-Player-Version"
    ] = DESKTOP_PET_PLAYER_VERSION

    return response


def parse_pet_string_list(
    raw_value,
    field_name
):
    try:
        parsed_value = json.loads(
            raw_value or "[]"
        )

    except json.JSONDecodeError as error:
        raise PetpackInputError(
            f"{field_name} 格式不正确。"
        ) from error

    if (
        not isinstance(parsed_value, list)
        or not all(
            isinstance(item, str)
            for item in parsed_value
        )
    ):
        raise PetpackInputError(
            f"{field_name} 格式不正确。"
        )

    return parsed_value


@app.route(
    "/api/desktop-packs",
    methods=["POST"]
)
def create_desktop_pack():
    uploads = [
        upload
        for upload in request.files.getlist(
            "files"
        )
        if upload and upload.filename
    ]

    try:
        if not 1 <= len(uploads) <= MAX_FILES:
            raise PetpackInputError(
                f"请上传 1～{MAX_FILES} 个图片或动画文件。"
            )

        try:
            default_size = int(
                request.form.get(
                    "size",
                    "120"
                )
            )

            background_threshold = int(
                request.form.get(
                    "background_threshold",
                    "32"
                )
            )

        except ValueError as error:
            raise PetpackInputError(
                "桌宠大小或背景容差不是有效数字。"
            ) from error

        labels = parse_pet_string_list(
            request.form.get(
                "labels",
                "[]"
            ),
            "动作名称"
        )

        roles = [
            role.lower().strip()
            for role in parse_pet_string_list(
                request.form.get(
                    "roles",
                    "[]"
                ),
                "动作角色"
            )
        ]

        if any(
            role not in SUPPORTED_ROLES
            for role in roles
        ):
            raise PetpackInputError(
                "动作角色中包含不支持的选项。"
            )

        remove_background = (
            request.form.get(
                "remove_background",
                "false"
            ).lower()
            in {
                "1",
                "true",
                "yes",
                "on"
            }
        )

        pet_name = request.form.get(
            "name",
            "我的桌宠"
        ).strip()

        with TemporaryDirectory(
            prefix="scripthub-pet-"
        ) as temporary_directory:
            workspace = Path(
                temporary_directory
            )
            image_paths = []

            for index, upload in enumerate(
                uploads
            ):
                suffix = Path(
                    upload.filename
                ).suffix.lower()

                if suffix not in SUPPORTED_SUFFIXES:
                    raise PetpackInputError(
                        "不支持的文件格式："
                        f"{upload.filename}"
                    )

                destination = (
                    workspace
                    / f"action{index:03d}{suffix}"
                )

                upload.save(destination)
                image_paths.append(destination)

            output_path = (
                workspace
                / "generated.petpack"
            )

            build_petpack(
                image_paths,
                output_path,
                labels=labels,
                roles=roles,
                pet_name=pet_name,
                default_size=default_size,
                remove_background=remove_background,
                background_threshold=(
                    background_threshold
                )
            )

            package_bytes = (
                output_path.read_bytes()
            )

        safe_name = "".join(
            character
            if character not in '<>:"/\\|?*'
            else "_"
            for character in pet_name
        ).strip(" .")

        if not safe_name:
            safe_name = "我的桌宠"

        return send_file(
            BytesIO(package_bytes),
            mimetype=(
                "application/"
                "vnd.desktop-pet-pack"
            ),
            as_attachment=True,
            download_name=(
                safe_name[:64]
                + ".petpack"
            )
        )

    except PetpackInputError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except PetpackServiceError:
        app.logger.exception(
            "桌宠资源包生成失败"
        )

        return jsonify({
            "success": False,
            "message": (
                "生成服务暂时不可用，"
                "请稍后再试。"
            )
        }), 503

    except Exception:
        app.logger.exception(
            "桌宠资源包请求处理失败"
        )

        return jsonify({
            "success": False,
            "message": (
                "处理图片时发生错误，"
                "请检查文件后重试。"
            )
        }), 500


# =========================
# 管理员审核页面
# =========================
@app.route("/admin/scripts")
@admin_required
def admin_scripts():
    selected_status = request.args.get(
        "status",
        "pending"
    ).strip()

    allowed_statuses = {
        "pending",
        "approved",
        "rejected",
        "all"
    }

    if (
        selected_status
        not in allowed_statuses
    ):
        selected_status = "pending"

    conn = get_db_connection()

    try:
        if selected_status == "all":
            script_list = conn.execute("""
                SELECT *
                FROM scripts
                ORDER BY id DESC
            """).fetchall()

        else:
            script_list = conn.execute("""
                SELECT *
                FROM scripts
                WHERE status = ?
                ORDER BY id DESC
            """, (
                selected_status,
            )).fetchall()

    finally:
        conn.close()

    return render_template(
        "admin_scripts.html",
        scripts=script_list,
        selected_status=selected_status,
        current_admin=session.get(
            "username"
        )
    )


# =========================
# 审核通过
# =========================
@app.route(
    "/admin/scripts/"
    "<int:script_id>/approve",
    methods=["POST"]
)
@admin_required
def approve_script(script_id):
    current_time = now_text()

    conn = get_db_connection()

    try:
        conn.execute("""
            UPDATE scripts
            SET status = 'approved',
                updated_at = ?,
                reviewed_at = ?
            WHERE id = ?
        """, (
            current_time,
            current_time,
            script_id
        ))

        conn.commit()

    finally:
        conn.close()

    return redirect(
        url_for("admin_scripts")
    )


# =========================
# 审核拒绝
# =========================
@app.route(
    "/admin/scripts/"
    "<int:script_id>/reject",
    methods=["POST"]
)
@admin_required
def reject_script(script_id):
    current_time = now_text()

    conn = get_db_connection()

    try:
        conn.execute("""
            UPDATE scripts
            SET status = 'rejected',
                updated_at = ?,
                reviewed_at = ?
            WHERE id = ?
        """, (
            current_time,
            current_time,
            script_id
        ))

        conn.commit()

    finally:
        conn.close()

    return redirect(
        url_for("admin_scripts")
    )


# =========================
# 管理员删除脚本
# =========================
@app.route(
    "/admin/scripts/"
    "<int:script_id>/delete",
    methods=["POST"]
)
@admin_required
def delete_script(script_id):
    selected_status = request.form.get(
        "status",
        "pending"
    ).strip()

    allowed_statuses = {
        "pending",
        "approved",
        "rejected",
        "all"
    }

    if (
        selected_status
        not in allowed_statuses
    ):
        selected_status = "pending"

    conn = get_db_connection()

    try:
        conn.execute("""
            DELETE FROM scripts
            WHERE id = ?
        """, (
            script_id,
        ))

        conn.commit()

    finally:
        conn.close()

    return redirect(
        url_for(
            "admin_scripts",
            status=selected_status
        )
    )


# =========================
# AI 测试页面
# =========================
@app.route(
    "/ai-test",
    methods=["GET", "POST"]
)
def ai_test():
    question = ""
    answer = ""

    if request.method == "POST":
        question = request.form.get(
            "question",
            ""
        )

        answer = handle_question(
            question
        )

    return render_template(
        "ai_test.html",
        question=question,
        answer=answer
    )


# =========================
# 启动程序
# =========================
if __name__ == "__main__":
    app.run(debug=True)
