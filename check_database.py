from database import get_db_connection, init_db


def show_database_status():
    """初始化数据库，并打印当前数据库结构概况。"""
    init_db()
    conn = get_db_connection()

    try:
        if getattr(conn, "is_postgresql", False):
            tables = conn.execute("""
                SELECT table_name AS name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """).fetchall()

        else:
            tables = conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """).fetchall()

        print("数据库中的数据表：")

        for table in tables:
            table_name = table["name"]

            total = conn.execute(
                f"SELECT COUNT(*) AS total FROM {table_name}"
            ).fetchone()["total"]

            print(f"- {table_name}：{total} 条记录")

        print("\nscripts 表字段：")

        if getattr(conn, "is_postgresql", False):
            columns = conn.execute("""
                SELECT
                    column_name AS name,
                    data_type AS type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'scripts'
                ORDER BY ordinal_position
            """).fetchall()

        else:
            columns = conn.execute(
                "PRAGMA table_info(scripts)"
            ).fetchall()

        for column in columns:
            print(
                f"- {column['name']} "
                f"({column['type'] or '未指定类型'})"
            )

    finally:
        conn.close()


if __name__ == "__main__":
    show_database_status()
