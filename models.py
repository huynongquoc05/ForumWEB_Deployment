import os

import pyodbc
import hashlib

import redis
import os

cache = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=6379,
    db=0
)

# def get_db_connection():
#     return pyodbc.connect('Server=DESKTOP-AMN3OI8;Database=ForumWebsite;Trusted_Connection=yes;DRIVER={SQL Server}')

def get_db_connection():
    # 1. Lấy thông tin từ bên ngoài truyền vào.
    # Nếu không có ai truyền vào, dùng giá trị mặc định ở vế sau.
    db_server = os.environ.get('DB_SERVER', 'host.docker.internal')
    db_user = os.environ.get('DB_USER', 'sa')
    db_password = os.environ.get('DB_PASSWORD', '')

    # 2. Sử dụng f-string để chèn các biến này vào chuỗi kết nối
    return pyodbc.connect(
        'DRIVER={ODBC Driver 18 for SQL Server};'
        f'SERVER={db_server};'
        'DATABASE=ForumWebsite;'
        f'UID={db_user};'
        f'PWD={db_password};'
        'TrustServerCertificate=yes;'
    )

def hash_password(password):
    """Mã hóa mật khẩu bằng SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def check_exists(username, password):
    """Kiểm tra nếu tên người dùng và mật khẩu hợp lệ, trả về thông tin người dùng nếu tồn tại."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Hash mật khẩu trước khi so sánh
    hashed_password = hash_password(password)
    # print(hashed_password)

    # Thực hiện truy vấn tìm người dùng với username và hashed password
    sqlcommand = "SELECT user_id, username ,role  FROM Users WHERE username = ? AND password = ?"
    cursor.execute(sqlcommand, (username, hashed_password))
    user = cursor.fetchone()  # Lấy một dòng dữ liệu nếu có

    conn.close()

    # Trả về thông tin người dùng nếu tìm thấy, nếu không trả về None
    return user  # Trả về (user_id, username) nếu tìm thấy, None nếu không tìm thấy


def SaveToDB(name, password, email):
    """Lưu người dùng mới vào cơ sở dữ liệu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    role = 'user'
    hashed_password = hash_password(password)
    cursor.execute("INSERT INTO Users (username, password, email, role) VALUES (?, ?, ?, ?)",
                   (name, hashed_password, email, role))
    conn.commit()
    conn.close()

import pyodbc

# Hàm lấy danh sách chuyên mục từ database
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category_id, name FROM Categories")
    categories = cursor.fetchall()
    conn.close()
    return categories


def parse_custom_syntax(content):
    # Thay thế cú pháp -uplimg(link ảnh) bằng thẻ <img src="link ảnh">
    while '-uplimg(' in content:
        start = content.index('-uplimg(')
        end = content.index(')', start)
        image_link = content[start + 8:end]  # Lấy link ảnh
        img_tag = f'<img src="{image_link}" alt="Image">'
        content = content[:start] + img_tag + content[end + 1:]
    return content

def add_paragraph_tags(content):
    # Chia đoạn văn bản theo dòng trống và gắn thẻ <p> cho từng đoạn
    paragraphs = content.split("\n\n")  # Mỗi đoạn văn cách nhau 2 dấu xuống dòng
    wrapped_content = ''.join(
        f'<p>{p.replace("\n", "<br>").strip()}</p>' for p in paragraphs if p.strip()
    )
    return wrapped_content

import re


def parse_custom_syntax_reverse(content):
    # Chuyển đổi <img src="link"> thành -uplimg(link)
    while '<img src="' in content:
        start = content.index('<img src="') + len('<img src="')
        end = content.index('"', start)
        image_link = content[start:end]
        content = content.replace(f'<img src="{image_link}" alt="">', f'-uplimg({image_link})')

    # Xóa các thẻ <p> và <br> để trả về đoạn văn ban đầu
    content = content.replace('<p>', '').replace('</p>', '\n\n').replace('<br>', '\n')

    # Loại bỏ thẻ alt="Image" nếu không có
    content = content.replace('alt="">', 'alt="Image">')

    return content


# Hàm lấy bài viết theo post_id


# Hàm cập nhật bài viết
def save_updated_post(post_id, title, content, category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Posts SET title = ?, content = ?, category_id = ?, updated_at = GETDATE() 
        WHERE post_id = ?
    """, (title, content, category_id, post_id))
    conn.commit()
    conn.close()




# Hàm lưu bài viết mới vào database

def save_post(title, content, category_id, user_id,is_admin):
    conn = get_db_connection()
    cursor = conn.cursor()

    if is_admin == 'admin':
        status = 'approved'
    else:
        status = 'pending'  # Trạng thái mặc định là 'pending' nếu là user
    cursor.execute("""
        INSERT INTO Posts (title, content, category_id, user_id, status) 
        VALUES (?, ?, ?, ?, ?)
    """, (title, content, category_id, user_id, status))
    conn.commit()
    conn.close()
    return status


def get_post_by_id0(post_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Posts WHERE post_id = ?", (post_id,))
    post = cursor.fetchone()
    conn.close()
    return post

def get_post_by_id(post_id):
    """Lấy thông tin bài viết theo ID, chỉ lấy bài viết đã được phê duyệt."""
    conn = get_db_connection()
    cursor = conn.cursor()

    sql_command = """
    SELECT 
        p.post_id,
        p.title AS post_title,
        p.content AS post_content,
        p.created_at AS post_created_at,
        p.updated_at AS post_updated_at,
        c.name AS category_name,
        u.user_id AS author_id,  -- Thêm thuộc tính id của tác giả
        u.username AS author_username  -- Thêm thuộc tính username của tác giả
    FROM 
        Posts p
    JOIN 
        Categories c ON p.category_id = c.category_id
    JOIN 
        Users u ON p.user_id = u.user_id
    WHERE 
        p.post_id = ? AND p.status = 'approved'
    """

    cursor.execute(sql_command, (post_id,))
    post = cursor.fetchone()

    conn.close()

    if post:
        return {
            'post_id': post.post_id,  # Thêm post_id vào dictionary
            'title': post.post_title,
            'content': post.post_content,
            'created_at': post.post_created_at,
            'updated_at': post.post_updated_at,
            'category': post.category_name,
            'author_id': post.author_id,  # Trả về thuộc tính id của tác giả
            'author': post.author_username  # Trả về thuộc tính username
        }
    else:
        return None



import re

def extract_thumbnail(content):
    """
    Hàm tìm ảnh đại diện từ nội dung bài viết.
    Nếu có thẻ <img>, lấy URL ảnh đầu tiên làm ảnh đại diện.
    Nếu không có, trả về None.
    """
    # Tìm thẻ img đầu tiên và lấy URL từ thuộc tính src
    match = re.search(r'<img[^>]+src="([^">]+)"', content)
    return match.group(1) if match else None

def get_recent_posts(limit=None, category_id=None):
    """Lấy ra tất cả các bài viết hoặc số lượng bài viết được chỉ định và tùy chọn lọc theo chuyên mục."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Điều chỉnh câu lệnh SQL, nếu có category_id thì thêm điều kiện lọc
    sql_command = """
    SELECT 
        p.post_id,
        p.title,
        p.content,
        p.created_at,
        c.name AS category_name,
        u.username AS author_username
    FROM 
        Posts p
    JOIN 
        Categories c ON p.category_id = c.category_id
    JOIN 
        Users u ON p.user_id = u.user_id
    WHERE 
        p.status = 'approved'
    """

    # Nếu có category_id, thêm điều kiện lọc theo category_id
    if category_id is not None:
        sql_command += " AND p.category_id = ?"

    # Thêm điều kiện sắp xếp, và chỉ giới hạn số lượng khi `limit` không phải là `None`
    sql_command += " ORDER BY p.created_at DESC"
    if limit is not None:
        sql_command += " OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY"

    # Thực thi câu lệnh SQL với các tham số tương ứng
    if category_id is not None and limit is not None:
        cursor.execute(sql_command, (category_id, limit))
    elif category_id is not None:
        cursor.execute(sql_command, (category_id,))
    elif limit is not None:
        cursor.execute(sql_command, (limit,))
    else:
        cursor.execute(sql_command)

    posts = cursor.fetchall()
    conn.close()

    return [
        {
            'post_id': post.post_id,
            'title': post.title,
            'content': post.content[:100],  # Lấy 100 ký tự đầu tiên của nội dung
            'created_at': post.created_at,
            'category': post.category_name,
            'author': post.author_username,
            'thumbnail': extract_thumbnail(post.content)  # Thêm ảnh đại diện
        }
        for post in posts
    ]



# Lấy bài viết theo tài khoản
def get_postByUserId(user_id):
    """Lấy thông tin bài viết theo tài khoản, chỉ lấy bài viết đã được phê duyệt."""

    # Kết nối đến cơ sở dữ liệu
    conn = get_db_connection()

    # Tạo một con trỏ để thực hiện truy vấn
    cursor = conn.cursor()

    # Truy vấn để lấy thông tin bài viết của người dùng
    query = """
    SELECT 
        p.post_id, 
        p.title, 
        p.content, 
        p.created_at, 
        c.name AS category_name, 
        u.username AS author_username 
    FROM 
        Posts p
    JOIN 
        Categories c ON p.category_id = c.category_id
    JOIN 
        Users u ON p.user_id = u.user_id
    WHERE 
        p.user_id = ? AND p.status = 'approved'
    """

    # Thực hiện truy vấn với user_id
    cursor.execute(query, (user_id,))

    # Lấy tất cả kết quả
    posts = cursor.fetchall()

    # Đóng con trỏ và kết nối
    cursor.close()
    conn.close()

    # Trả về kết quả dưới dạng danh sách dictionary
    return [
        {
            'post_id': post.post_id,
            'title': post.title,
            'content': post.content[:100],  # Lấy 100 ký tự đầu tiên của nội dung
            'created_at': post.created_at,
            'category': post.category_name,
            'author': post.author_username
        }
        for post in posts
    ]


def add_comment_to_db(post_id, parent_comment_id, user_id, content):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Thêm bình luận vào CSDL
    cursor.execute("""
        INSERT INTO Comments (post_id, parent_comment_id, user_id, content, created_at)
        VALUES (?, ?, ?, ?, GETDATE())
    """, (post_id, parent_comment_id, user_id, content))

    conn.commit()
    conn.close()

def can_user_edit_comment(comment_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM Comments WHERE comment_id = ?", (comment_id,))
    comment = cursor.fetchone()
    conn.close()

    # Kiểm tra nếu bình luận tồn tại và người dùng hiện tại là tác giả
    return comment and comment[0] == user_id  # Sử dụng comment[0] thay vì comment['user_id']

def update_comment_in_db(comment_id, content):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Cập nhật nội dung bình luận
    cursor.execute("""
        UPDATE Comments
        SET content = ?, created_at = GETDATE()
        WHERE comment_id = ?
    """, (content, comment_id))

    conn.commit()
    conn.close()


def delete_comment_from_db(comment_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Kiểm tra xem bình luận có bình luận con nào không
    cursor.execute("SELECT comment_id FROM Comments WHERE parent_comment_id = ?", (comment_id,))
    child_comments = cursor.fetchall()

    # Nếu có bình luận con, thay đổi parent_comment_id thành NULL
    if child_comments:
        for child in child_comments:
            cursor.execute("UPDATE Comments SET parent_comment_id = NULL WHERE comment_id = ?", (child[0],))

    # Xóa bình luận cha
    cursor.execute("DELETE FROM Comments WHERE comment_id = ?", (comment_id,))

    conn.commit()
    conn.close()



def get_pending_posts():
    conn = get_db_connection()
    query = """
        SELECT post_id, title, content, created_at
        FROM Posts
        WHERE status = 'pending'
    """
    cursor = conn.cursor()
    cursor.execute(query)
    pending_posts = cursor.fetchall()
    return pending_posts


def get_pending_posts_byId(post_id):
    """Lấy thông tin của một bài viết đang chờ duyệt dựa trên post_id."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Truy vấn lấy bài viết với trạng thái pending
    query = """
        SELECT P.post_id, P.title, P.content, P.created_at, P.status, U.user_id, U.username
        FROM Posts P
        JOIN Users U ON P.user_id = U.user_id
        WHERE P.post_id = ? AND P.status = 'pending'
    """
    cursor.execute(query, (post_id,))
    post = cursor.fetchone()

    # Đóng kết nối
    cursor.close()
    conn.close()

    return post


def get_comments_by_post_id(post_id):
    """Lấy các bình luận của bài viết và nhóm theo bình luận cha, bao gồm số cảm xúc của mỗi bình luận."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(""" 
        SELECT 
            c.comment_id,
            c.content,
            c.created_at,
            c.parent_comment_id,
            u.username AS author,
            c.user_id
        FROM 
            Comments c
        JOIN 
            Users u ON c.user_id = u.user_id
        WHERE 
            c.post_id = ?
        ORDER BY 
            c.created_at ASC
    """, (post_id,))

    comments = cursor.fetchall()
    conn.close()

    # Dictionary to group comments
    comment_dict = {}

    def find_comment_group(comment_id, comment_dict):
        for parent_id, group in comment_dict.items():
            for c in group:
                # Sử dụng cú pháp truy cập từ điển
                if c['comment_id'] == comment_id:  # Thay đổi ở đây
                    return group
        return None

    for comment in comments:
        # Thêm số lượng cảm xúc cho từng bình luận
        reaction_count = get_comment_reaction_count(comment.comment_id)
        comment_dict_entry = {
            'comment_id': comment.comment_id,
            'content': comment.content,
            'created_at': comment.created_at,
            'parent_comment_id': comment.parent_comment_id,
            'author': comment.author,
            'reaction_count': reaction_count,
            'user_id':comment.user_id
        }

        if comment_dict_entry['parent_comment_id'] is None:
            if comment_dict_entry['comment_id'] not in comment_dict:
                comment_dict[comment_dict_entry['comment_id']] = [comment_dict_entry]
        else:
            parent_group = find_comment_group(comment_dict_entry['parent_comment_id'], comment_dict)
            if parent_group is not None:
                parent_group.append(comment_dict_entry)
            else:
                comment_dict[comment_dict_entry['parent_comment_id']] = [comment_dict_entry]

    return list(comment_dict.values())


def get_comment_by_id(comment_id):
    # Kết nối đến cơ sở dữ liệu
    conn = get_db_connection()

    cursor = conn.cursor()

    # Truy vấn dữ liệu từ bảng Comments
    query = """
        SELECT 
            c.comment_id,
            c.content,
            c.created_at,
            c.parent_comment_id,
            u.username AS author
        FROM 
            Comments c
        LEFT JOIN 
            Users u ON c.user_id = u.user_id
        WHERE 
            c.comment_id = ?
    """

    # Thực thi truy vấn
    cursor.execute(query, (comment_id,))

    # Lấy kết quả
    result = cursor.fetchone()

    # Đóng kết nối
    cursor.close()
    conn.close()

    # Kiểm tra xem có kết quả không
    if result:
        # Lấy số lượng cảm xúc bằng hàm get_comment_reaction_count
        reaction_count = get_comment_reaction_count(result.comment_id)

        # Trả về dữ liệu dưới dạng dictionary
        return {
            'comment_id': result.comment_id,
            'content': result.content,
            'created_at': result.created_at,
            'parent_comment_id': result.parent_comment_id,
            'author': result.author,
            'reaction_count': reaction_count
        }
    else:
        return None


# models.py
import pyodbc


def handle_reaction(post_id, user_id, reaction_type):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Kiểm tra cảm xúc hiện tại của người dùng đối với bài viết
    cursor.execute("""
        SELECT reaction_id, reaction_type FROM Reactions WHERE post_id = ? AND user_id = ?
    """, (post_id, user_id))
    existing_reaction = cursor.fetchone()

    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            # Nếu cảm xúc đã tồn tại và giống nhau, xóa cảm xúc
            cursor.execute("DELETE FROM Reactions WHERE reaction_id = ?", (existing_reaction.reaction_id,))
        else:
            # Nếu cảm xúc khác nhau, cập nhật cảm xúc
            cursor.execute("UPDATE Reactions SET reaction_type = ? WHERE reaction_id = ?", (reaction_type, existing_reaction.reaction_id))
    else:
        # Thêm cảm xúc mới nếu chưa tồn tại
        cursor.execute("""
            INSERT INTO Reactions (user_id, post_id, reaction_type, created_at)
            VALUES (?, ?, ?, GETDATE())
        """, (user_id, post_id, reaction_type))

    conn.commit()

    # Lấy lại số lượng cảm xúc
    cursor.execute("SELECT COUNT(*) FROM Reactions WHERE post_id = ?", (post_id,))
    reaction_count = cursor.fetchone()[0]
    conn.close()

    return reaction_count






def get_post_reaction_count(post_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT reaction_type, COUNT(*) FROM Reactions WHERE post_id = ? GROUP BY reaction_type
    """, post_id)
    reaction_data = cursor.fetchall()
    conn.close()
    return len(reaction_data)

def get_user_reaction(user_id, post_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT reaction_type FROM Reactions WHERE post_id = ? AND user_id = ?", (post_id, user_id))
    user_reaction = cursor.fetchone()
    conn.close()
    return user_reaction


import pyodbc


def get_comment_reaction_count(comment_id):
    """Lấy số lượng cảm xúc của bình luận theo comment_id."""
    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) 
        FROM Reactions 
        WHERE comment_id = ?
    """, (comment_id,))
    reaction_count = cursor.fetchone()[0] or 0
    conn.close()

    return reaction_count

def update_comment_reaction(comment_id, user_id, reaction_type):
    # Kiểm tra xem user_id có hợp lệ không
    if user_id is None:
        raise ValueError("user_id cannot be None")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Kiểm tra cảm xúc hiện tại của người dùng đối với bình luận
    cursor.execute("""
        SELECT reaction_id, reaction_type FROM Reactions WHERE comment_id = ? AND user_id = ?
    """, (comment_id, user_id))
    existing_reaction = cursor.fetchone()

    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            # Nếu cảm xúc đã tồn tại và giống nhau, xóa cảm xúc
            cursor.execute("DELETE FROM Reactions WHERE reaction_id = ?", (existing_reaction.reaction_id,))
        else:
            # Nếu cảm xúc khác nhau, cập nhật cảm xúc
            cursor.execute("UPDATE Reactions SET reaction_type = ? WHERE reaction_id = ?", (reaction_type, existing_reaction.reaction_id))
    else:
        # Thêm cảm xúc mới nếu chưa tồn tại
        cursor.execute("""
            INSERT INTO Reactions (user_id, post_id, comment_id, reaction_type, created_at)
            VALUES (?, ?, ?, ?, GETDATE())
        """, (user_id, None, comment_id, reaction_type))  # post_id có thể là None nếu không sử dụng

    conn.commit()

    # Lấy lại số lượng cảm xúc cho bình luận
    cursor.execute("SELECT COUNT(*) FROM Reactions WHERE comment_id = ?", (comment_id,))
    reaction_count = cursor.fetchone()[0]
    conn.close()

    return reaction_count


def get_user_comment_reaction(post_id,user_id):

    # Tiếp tục xử lý với post_id và user_id
    if user_id is None:
        return None  # Nếu người dùng chưa đăng nhập, trả về None

    # Kết nối đến cơ sở dữ liệu
    conn = get_db_connection()
    cursor = conn.cursor()

    # Truy vấn lấy phản ứng của người dùng cho bài viết cụ thể này
    cursor.execute("""
        SELECT reaction_type FROM Reactions
        WHERE post_id = ? AND user_id = ?
    """, (post_id, user_id))
    reaction = cursor.fetchone()

    conn.close()

    # Trả về phản ứng nếu có, nếu không trả về None
    return reaction[0] if reaction else None


def get_user_info_and_posts(user_id, is_admin):
    """Lấy thông tin người dùng và danh sách bài viết công khai hoặc tất cả bài viết nếu là admin."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Lấy thông tin người dùng
    query_user = "SELECT username, role, created_at, user_id FROM Users WHERE user_id = ?"
    cursor.execute(query_user, (user_id,))
    user_info = cursor.fetchone()

    if user_info is None:
        return None, None  # Trả về None nếu người dùng không tồn tại

    username, role, created_at, user_id = user_info

    # Kiểm tra xem người dùng là admin hay không
    if is_admin == 'admin':
        # Lấy tất cả bài viết nếu là admin (bao gồm cả bài viết "pending" và "approved")
        query_posts = "SELECT post_id, title, content, created_at, user_id, status FROM Posts"
        cursor.execute(query_posts)
        posts = cursor.fetchall()


        query_user_posts_count = """
            SELECT U.user_id, U.username, U.role, U.created_at, COUNT(P.post_id) AS post_count
            FROM Users U 
            LEFT JOIN Posts P ON U.user_id = P.user_id AND P.status = 'approved'  -- Chỉ tính bài viết đã duyệt
            GROUP BY U.user_id, U.username, U.role, U.created_at
            ORDER BY post_count DESC
        """

        cursor.execute(query_user_posts_count)
        users_post_counts = cursor.fetchall()

    else:
        # Nếu không phải admin, chỉ lấy các bài viết của user_id đó
        query_posts = "SELECT post_id, title, content, created_at, user_id, status FROM Posts WHERE user_id = ?"
        cursor.execute(query_posts, (user_id,))
        posts = cursor.fetchall()
        users_post_counts = None

    # Trích xuất ảnh đại diện cho mỗi bài viết
    post_list = []
    for post in posts:
        post_id, title, content, created_at, user_id, status = post
        thumbnail = extract_thumbnail(content)  # Lấy ảnh đại diện từ nội dung bài viết
        post_list.append({
            'post_id': post_id,
            'title': title,
            'content': content[:150] + '...',  # Hiển thị 150 ký tự đầu của nội dung
            'created_at': created_at,
            'user_id': user_id,
            'status': status,
            'thumbnail': thumbnail  # Thêm ảnh đại diện vào kết quả bài viết
        })

    # Đóng con trỏ và kết nối
    cursor.close()
    conn.close()

    return {
        'username': username,
        'role': role,
        'created_at': created_at,
        'user_id': user_id,
        'users_post_counts': users_post_counts  # Thêm thông tin số bài viết của tất cả người dùng
    }, post_list


def get_activity_history(user_id):
    """Lấy lịch sử hoạt động của người dùng."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Lấy bài viết
    query_posts = """
        SELECT created_at, N'đã thêm 1 bài viết', title, status, post_id
        FROM Posts
        WHERE user_id = ?
    """
    cursor.execute(query_posts, (user_id,))
    posts = cursor.fetchall()


    # Lấy bình luận
    query_comments = """
        SELECT Comments.created_at, N'đã bình luận bài viết của ' + Users.username, Comments.content, Posts.title, Posts.post_id
        FROM Comments
        JOIN Posts ON Comments.post_id = Posts.post_id
        JOIN Users ON Posts.user_id = Users.user_id
        WHERE Comments.user_id = ?
    """

    cursor.execute(query_comments, (user_id,))
    comments = cursor.fetchall()

    # Lấy cảm xúc
    query_reactions = """
        SELECT Reactions.created_at,
               CASE WHEN Reactions.post_id IS NOT NULL THEN N'đã bày tỏ cảm xúc về bài viết' ELSE N'đã bày tỏ cảm xúc về bình luận' END AS action,
               COALESCE(Posts.title, Comments.content) AS content,
               Posts.post_id,
               Comments.comment_id
        FROM Reactions
        LEFT JOIN Posts ON Reactions.post_id = Posts.post_id
        LEFT JOIN Comments ON Reactions.comment_id = Comments.comment_id
        WHERE Reactions.user_id = ?
    """

    cursor.execute(query_reactions, (user_id,))
    reactions = cursor.fetchall()

    # Tổng hợp dữ liệu
    activity_history = []

    for row in posts:
        activity_history.append({
            'date': row[0],
            'action': row[1],
            'title': row[2],
            'status': row[3],
            'post_id': row[4]
        })

    for row in comments:
        activity_history.append({
            'date': row[0],
            'action': row[1],
            'content': row[2],
            'title': row[3],
            'post_id': row[4]
        })

    for row in reactions:
        if row[3] is not None and row[4] is None:  # Kiểm tra nếu chỉ có post_id (cảm xúc về bài viết)
            activity_history.append({
                'date': row[0],
                'action': 'đã bày tỏ cảm xúc về bài viết',
                'content': row[2],
                'post_id': row[3]  # Lưu post_id cho bài viết
            })
        elif row[4] is not None and row[3] is None:  # Kiểm tra nếu chỉ có comment_id (cảm xúc về bình luận)
            activity_history.append({
                'date': row[0],
                'action': 'đã bày tỏ cảm xúc về bình luận',
                'content': row[2],
                'comment_id': row[4]  # Lưu comment_id cho bình luận
            })

    # Đóng kết nối
    cursor.close()
    conn.close()

    # Sắp xếp hoạt động theo thời gian (gần nhất trước)
    activity_history.sort(key=lambda x: x['date'], reverse=True)

    return activity_history

def approve_post_in_db(post_id):
    """Cập nhật bài viết sang trạng thái 'approved'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Posts SET status = 'approved' WHERE post_id = ?", (post_id,))
    conn.commit()
    cursor.close()
    conn.close()

def delete_post_in_db(post_id):
    """Xóa bài viết khỏi cơ sở dữ liệu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Posts WHERE post_id = ?", (post_id,))
    conn.commit()
    cursor.close()
    conn.close()


# Hàm tìm kiếm người dùng theo từ khóa
def search_users_by_keyword(keyword):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT user_id, username
        FROM Users
        WHERE username LIKE ?
    """
    # Thêm ký tự `%` để tìm kiếm giống hoặc gần giống
    cursor.execute(query, f'%{keyword}%')

    users = [{"user_id": row.user_id, "username": row.username} for row in cursor.fetchall()]

    cursor.close()
    conn.close()
    return users


def search_posts_by_keyword(keyword):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT Posts.post_id, Posts.title, Posts.content, Categories.name AS category_name
        FROM Posts
        JOIN Categories ON Posts.category_id = Categories.category_id
        WHERE Posts.title LIKE ? OR Posts.content LIKE ?
    """
    # Thêm ký tự `%` để tìm kiếm giống hoặc gần giống
    cursor.execute(query, f'%{keyword}%', f'%{keyword}%')

    posts = []
    for row in cursor.fetchall():
        # Xử lý nội dung để tạo đoạn trích nếu từ khóa nằm trong content
        content_preview = ""
        if keyword.lower() in row.content.lower():
            idx = row.content.lower().find(keyword.lower())
            start = max(0, idx - 20)
            end = idx + len(keyword) + 100
            content_preview = f"...{row.content[start:end]}..."

        posts.append({
            "post_id": row.post_id,
            "title": row.title,
            "content": content_preview,
            "category": row.category_name
        })

    cursor.close()
    conn.close()
    return posts
