import hashlib

from models import get_db_connection


def hash_password(password):
    """Mã hóa mật khẩu bằng SHA-256 (Giống hệt code web của bạn)."""
    return hashlib.sha256(password.encode()).hexdigest()


def update_all_passwords():
    # Danh sách các tài khoản init ban đầu và mật khẩu gốc của chúng
    users_to_fix = {
        'Putin': 'admin_password',
        'leviethai': 'user1_password',
        'nguyenkhachung': 'user2_password'
    }

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("Đang kết nối Database và cập nhật mật khẩu...")

        for username, plain_password in users_to_fix.items():
            # Băm mật khẩu bằng hàm của Python
            hashed_pw = hash_password(plain_password)

            # Cập nhật vào DB
            cursor.execute("""
                UPDATE Users 
                SET password = ? 
                WHERE username = ?
            """, (hashed_pw, username))

            print(f"[OK] Đã cập nhật Hash chuẩn cho tài khoản: {username}")

        # Lưu thay đổi
        conn.commit()
        print("\nHoàn tất! Tất cả tài khoản đã được đồng bộ chuẩn Python.")
        print("Bây giờ bạn có thể mở Web lên và đăng nhập bình thường!")

    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    update_all_passwords()