from database import get_db_connection, init_db


def show_database_status():
    """初始化数据库，并打印当前数据库结构概况。"""
    init_db()
    conn = get_db_connection()

    try:
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
