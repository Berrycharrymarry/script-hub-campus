import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from curated_scripts import seed_curated_scripts


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "scripts.db"


def now_text():
    """返回统一格式的本地时间字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def backup_database():
    """在数据库结构升级前创建一次备份。"""
    if not DB_PATH.exists():
        return None

    backup_dir = BASE_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"scripts_{timestamp}.db"
    shutil.copy2(DB_PATH, backup_path)

    return backup_path


def get_db_connection():
    """创建并返回一个 SQLite 数据库连接。"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_configured_admin(username, password_hash):
    """
    Restore the configured administrator after an ephemeral database reset.

    The password hash is supplied through a private environment variable and
    is never stored in the public repository.
    """
    normalized_username = str(username or "").strip()
    normalized_password_hash = str(password_hash or "").strip()

    if not normalized_username or not normalized_password_hash:
        return False

    if not 3 <= len(normalized_username) <= 30:
        raise ValueError(
            "ADMIN_USERNAME must contain between 3 and 30 characters."
        )

    current_time = now_text()
    conn = get_db_connection()

    try:
        existing_user = conn.execute("""
            SELECT id
            FROM users
            WHERE username = ? COLLATE NOCASE
        """, (normalized_username,)).fetchone()

        if existing_user is None:
            conn.execute("""
                INSERT INTO users (
                    username,
                    email,
                    password_hash,
                    role,
                    is_active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 'admin', 1, ?, ?)
            """, (
                normalized_username,
                None,
                normalized_password_hash,
                current_time,
                current_time
            ))

        else:
            conn.execute("""
                UPDATE users
                SET username = ?,
                    password_hash = ?,
                    role = 'admin',
                    is_active = 1,
                    updated_at = ?
                WHERE id = ?
            """, (
                normalized_username,
                normalized_password_hash,
                current_time,
                existing_user["id"]
            ))

        conn.commit()

    finally:
        conn.close()

    return True


def get_table_columns(conn, table_name):
    """返回指定数据表当前拥有的全部字段名。"""
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def add_missing_script_columns(conn):
    """
    给旧版本 scripts 表补充新字段。

    SQLite 支持使用 ALTER TABLE ... ADD COLUMN 增加字段，
    因此旧数据库中的脚本不会被删除。
    """
    existing_columns = get_table_columns(conn, "scripts")

    new_columns = {
        "user_id": "INTEGER REFERENCES users(id) ON DELETE SET NULL",
        "author_name": "TEXT NOT NULL DEFAULT '匿名用户'",
        "review_note": "TEXT",
        "line_count": "INTEGER NOT NULL DEFAULT 0",
        "non_empty_line_count": "INTEGER NOT NULL DEFAULT 0",
        "warnings": "TEXT NOT NULL DEFAULT '[]'",
        "view_count": "INTEGER NOT NULL DEFAULT 0",
        "copy_count": "INTEGER NOT NULL DEFAULT 0",
        "download_count": "INTEGER NOT NULL DEFAULT 0",
        "like_count": "INTEGER NOT NULL DEFAULT 0",
        "updated_at": "TEXT",
        "reviewed_at": "TEXT",
        "tags": "TEXT NOT NULL DEFAULT '[]'",
        "source_name": "TEXT",
        "source_url": "TEXT",
        "install_url": "TEXT",
        "license_name": "TEXT",
        "original_version": "TEXT",
        "source_updated_at": "TEXT",
        "is_curated": "INTEGER NOT NULL DEFAULT 0"
    }

    missing_columns = [
        column_name
        for column_name in new_columns
        if column_name not in existing_columns
    ]

    # 只有确实需要升级旧表时才创建备份
    if missing_columns:
        backup_database()

    for column_name in missing_columns:
        column_definition = new_columns[column_name]
        conn.execute(
            f"ALTER TABLE scripts "
            f"ADD COLUMN {column_name} {column_definition}"
        )

    # 为旧数据补齐合理默认值
    conn.execute("""
        UPDATE scripts
        SET author_name = '匿名用户'
        WHERE author_name IS NULL OR TRIM(author_name) = ''
    """)

    conn.execute("""
        UPDATE scripts
        SET warnings = '[]'
        WHERE warnings IS NULL OR TRIM(warnings) = ''
    """)

    conn.execute("""
        UPDATE scripts
        SET updated_at = created_at
        WHERE updated_at IS NULL OR TRIM(updated_at) = ''
    """)

    conn.execute("""
        UPDATE scripts
        SET tags = '[]'
        WHERE tags IS NULL OR TRIM(tags) = ''
    """)


def init_db():
    """
    创建网站当前阶段需要的全部数据表、字段和索引。

    这个函数可以重复运行：
    已存在的表不会重复创建，旧 scripts 表会自动补字段。
    """
    conn = get_db_connection()

    try:
        # 用户表：为后续注册、登录和管理员权限做准备
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 脚本主表：保存脚本本身以及审核、统计、分析信息
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                author_name TEXT NOT NULL DEFAULT '匿名用户',
                title TEXT NOT NULL,
                description TEXT,
                language TEXT NOT NULL,
                category TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                code TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                review_note TEXT,
                line_count INTEGER NOT NULL DEFAULT 0,
                non_empty_line_count INTEGER NOT NULL DEFAULT 0,
                warnings TEXT NOT NULL DEFAULT '[]',
                view_count INTEGER NOT NULL DEFAULT 0,
                copy_count INTEGER NOT NULL DEFAULT 0,
                download_count INTEGER NOT NULL DEFAULT 0,
                like_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                reviewed_at TEXT,
                source_name TEXT,
                source_url TEXT,
                install_url TEXT,
                license_name TEXT,
                original_version TEXT,
                source_updated_at TEXT,
                is_curated INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)

        # 兼容你已经存在的旧 scripts.db
        add_missing_script_columns(conn)

        # 点赞关系表：限制同一用户不能重复点赞同一个脚本
        conn.execute("""
            CREATE TABLE IF NOT EXISTS script_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (script_id, user_id),
                FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 收藏关系表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS script_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (script_id, user_id),
                FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 评论表：后续可直接实现脚本评论区
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'visible',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (script_id) REFERENCES scripts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # 索引可以加快常用查询
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scripts_status_id
            ON scripts (status, id DESC)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scripts_category_status
            ON scripts (category, status)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scripts_language_status
            ON scripts (language, status)
        """)

        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_scripts_source_url
            ON scripts (source_url)
            WHERE source_url IS NOT NULL
              AND TRIM(source_url) != ''
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_comments_script_id
            ON comments (script_id, id DESC)
        """)

        seed_curated_scripts(conn)

        conn.commit()

    finally:
        conn.close()
