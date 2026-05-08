import pyodbc


def fetch_users():
    # Kết nối đến SQL Server bằng xác thực Windows
    conn = pyodbc.connect('Server=DESKTOP-AMN3OI8;Database=ForumWebsite;Trusted_Connection=yes;DRIVER={SQL Server}')

    # Tạo một cursor để thực hiện các câu lệnh SQL
    cursor = conn.cursor()

    try:
        # Thực hiện câu lệnh SELECT
        cursor.execute("SELECT * FROM users")

        # Lấy tất cả kết quả
        rows = cursor.fetchall()

        # In kết quả ra màn hình
        for row in rows:
            print(row)

    except Exception as e:
        print("Đã xảy ra lỗi:", e)

    finally:
        # Đóng cursor và kết nối
        cursor.close()
        conn.close()


if __name__ == "__main__":
    fetch_users()
