from getpass import getpass

from werkzeug.security import generate_password_hash

from database import get_db_connection, init_db, now_text


def create_admin():
    """
    在终端中创建一个管理员账号。
    """
    init_db()

    print("=== 创建 ScriptHub 管理员 ===")

    username = input("管理员用户名：").strip()

    if len(username) < 3:
        print("创建失败：用户名至少需要 3 个字符。")
        return

    password = getpass("管理员密码：")
    confirm_password = getpass("再次输入密码：")

    if password != confirm_password:
        print("创建失败：两次输入的密码不一致。")
        return

    if len(password) < 8:
        print("创建失败：密码至少需要 8 个字符。")
        return

    password_hash = generate_password_hash(password)
    current_time = now_text()

    conn = get_db_connection()

    try:
        existing_user = conn.execute("""
            SELECT id
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        if existing_user is not None:
            print("创建失败：这个用户名已经存在。")
            return

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
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            username,
            None,
            password_hash,
            "admin",
            1,
            current_time,
            current_time
        ))

        conn.commit()

    finally:
        conn.close()

    print(f"管理员 {username} 创建成功。")


if __name__ == "__main__":
    create_admin()
