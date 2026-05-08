import pyodbc
from model import Users  # Giả sử bạn đã định nghĩa lớp Users trong model.py

try:
    # Kết nối đến cơ sở dữ liệu
    conn = pyodbc.connect('Server=DESKTOP-AMN3OI8;Database=ForumWebsite;UID=sa;PWD=051120;PORT=1433;DRIVER={SQL Server}')
    print("Kết nối thành công!")

    # Tạo cursor để thực hiện truy vấn
    cursor = conn.cursor()

    # Thực hiện truy vấn để lấy tất cả các bản ghi từ bảng Users
    cursor.execute("SELECT user_id, username, password, email, role FROM Users")

    # Lấy tất cả các bản ghi
    rows = cursor.fetchall()

    # In thông tin của từng bản ghi ra màn hình
    for row in rows:
        user = Users(row.user_id, row.username, row.password, row.email, row.role)
        print(f'Mã người dùng: {user.user_id}, '
              f'Tên người dùng: {user.username}, '
              f'Mật khẩu: {user.password}, '
              f'Email: {user.email}, '
              f'Vai trò: {user.role}')

except Exception as e:
    print(f"Lỗi kết nối hoặc truy vấn: {e}")

finally:
    # Đóng kết nối
    if 'conn' in locals():
        conn.close()
        print("Đã đóng kết nối.")
