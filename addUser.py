import pyodbc
import hashlib

def hash_password(password):
    # Mã hóa mật khẩu bằng SHA-256
    return hashlib.sha256(password.encode()).hexdigest()

try:
    # Kết nối đến cơ sở dữ liệu
    conn = pyodbc.connect('Server=DESKTOP-AMN3OI8;Database=ForumWebsite;UID=sa;PWD=051120;PORT=1433;DRIVER={SQL Server}')
    print("Kết nối thành công!")

    # Tạo cursor để thực hiện truy vấn
    cursor = conn.cursor()

    # Dữ liệu để thêm vào bảng Users (mật khẩu là chuỗi văn bản gốc)
    users_data = [
        ('Putin', 'admin01admin', 'admin@gmail.com', 'admin'),        # Mật khẩu gốc
        ('leviethai', 'user01pass', 'user1@gmail.com', 'user'),       # Mật khẩu gốc
        ('nguyenkhachung', 'user02pass', 'user2@example.com', 'user'), # Mật khẩu gốc
    ]

    # Chuyển đổi mật khẩu sang dạng mã hóa và thêm vào cơ sở dữ liệu
    for username, plain_password, email, role in users_data:
        hashed_password = hash_password(plain_password)  # Mã hóa mật khẩu
        cursor.execute("INSERT INTO Users (username, password, email, role) VALUES (?, ?, ?, ?)",
                       (username, hashed_password, email, role))

    # Lưu các thay đổi
    conn.commit()
    print("Đã thêm 3 bản ghi vào bảng Users.")

except Exception as e:
    print(f"Lỗi kết nối hoặc truy vấn: {e}")

finally:
    # Đóng kết nối
    if 'conn' in locals():
        conn.close()
        print("Đã đóng kết nối.")
