import os

import pyodbc
import redis

from db_helper import extract_thumbnail

# Khởi tạo Redis Client
cache = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=6379,
    db=0,
    decode_responses=True
)
def get_recent_posts1(limit=None, category_id=None):
    """Lấy ra tất cả các bài viết hoặc số lượng bài viết được chỉ định và tùy chọn lọc theo chuyên mục."""
    conn = pyodbc.connect(
        'Server=DESKTOP-AMN3OI8;Database=ForumWebsite;UID=sa;PWD=051120;PORT=1433;DRIVER={SQL Server}'
    )
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


import json


def get_cached_posts_test(limit, category_id, ttl=60):
    cache_key = f"posts:cat_{category_id}:limit_{limit}"

    # 1. Thử lấy dữ liệu từ Redis RAM trước
    cached_data = cache.get(cache_key)

    if cached_data:
        # Cache Hit: Trả về kết quả luôn, không print rác màn hình khi test chịu tải
        return json.loads(cached_data)

    # 2. Cache Miss: Gọi xuống SQL Server qua hàm gốc của bạn
    posts = get_recent_posts1(limit=limit, category_id=category_id)

    # 3. Ép kiểu datetime thành string để tránh lỗi ép kiểu JSON
    for post in posts:
        if post['created_at']:
            # Đổi object datetime thành chuỗi dạng '2026-06-27 18:00:00'
            post['created_at'] = post['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    # 4. Lưu lại vào Redis cho các request sau hưởng sái
    cache.setex(cache_key, ttl, json.dumps(posts, ensure_ascii=False))
    return posts



import time
from concurrent.futures import ThreadPoolExecutor




# =====================================================================
# KỊCH BẢN GIẢ LẬP KHỦNG - ÉP TẢI TOÀN DIỆN
# =====================================================================
NUM_REQUESTS = 10000       # Tăng gấp 6 lần (Tổng số 3,000 request nã dồn dập)
CONCURRENT_THREADS = 300  # Tăng gấp 4 lần (200 container/user cùng F5 một lúc)

LIMIT_TEST = None         # Lấy TOÀN BỘ bài viết để bắt DB phải xử lý dữ liệu nặng
CAT_TEST = 4              # Chuyên mục cần test
# =====================================================================


def run_db_raw(_):
    """Hàm chạy chay xuống SQL Server"""
    try:
        get_recent_posts1(limit=LIMIT_TEST, category_id=CAT_TEST)
        return True
    except Exception:
        return False


def run_redis(_):
    """Hàm đọc từ Redis (Đã được nạp cache sẵn)"""
    try:
        get_cached_posts_test(limit=LIMIT_TEST, category_id=CAT_TEST)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # 0. Nạp sẵn cache vào Redis trước khi test đọc dữ liệu đồng thời
    print("Pre-loading data into Redis...")
    get_cached_posts_test(limit=LIMIT_TEST, category_id=CAT_TEST)

    print("\n=========================================================")
    print(f"💥 GIẢ LẬP ĐỒNG THỜI: {NUM_REQUESTS} Requests (Cường độ: {CONCURRENT_THREADS} luồng cùng lúc) 💥")
    print("=========================================================\n")

    # -----------------------------------------------------------
    # PHẦN 1: TẤN CÔNG ĐỒNG THỜI VÀO SQL SERVER
    # -----------------------------------------------------------
    print(f"⏳ 1. Đang nã {NUM_REQUESTS} requests đồng thời vào SQL Server...")
    start_db = time.perf_counter()

    # Tạo một Pool gồm 50 luồng chạy song song
    with ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
        # Giả lập gửi 500 request
        results_db = list(executor.map(run_db_raw, range(NUM_REQUESTS)))

    end_db = time.perf_counter()
    db_total_time = end_db - start_db
    success_db = sum(1 for r in results_db if r)

    print(f"❌ KẾT QUẢ SQL SERVER:")
    print(f"   - Tổng thời gian hoàn thành: {db_total_time:.2f} giây")
    print(f"   - Tốc độ xử lý (RPS): {NUM_REQUESTS / db_total_time:.1f} request/giây")
    print(f"   - Thành công: {success_db}/{NUM_REQUESTS}")
    print("-" * 50)

    # -----------------------------------------------------------
    # PHẦN 2: TẤN CÔNG ĐỒNG THỜI VÀO RAM REDIS
    # -----------------------------------------------------------
    print(f"⏳ 2. Đang nã {NUM_REQUESTS} requests đồng thời vào RAM Redis...")
    start_redis = time.perf_counter()

    with ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
        results_redis = list(executor.map(run_redis, range(NUM_REQUESTS)))

    end_redis = time.perf_counter()
    redis_total_time = end_redis - start_redis
    success_redis = sum(1 for r in results_redis if r)

    print(f"🚀 KẾT QUẢ RAM REDIS:")
    print(f"   - Tổng thời gian hoàn thành: {redis_total_time:.2f} giây")
    print(f"   - Tốc độ xử lý (RPS): {NUM_REQUESTS / redis_total_time:.1f} request/giây")
    print(f"   - Thành công: {success_redis}/{NUM_REQUESTS}")

    # -----------------------------------------------------------
    # TỔNG KẾT
    # -----------------------------------------------------------
    print("\n=========================================================")
    print(f"🔥 KẾT LUẬN CHỊU TẢI:")
    print(
        f"   Redis giúp hệ thống xử lý nhanh hơn khoảng {db_total_time / redis_total_time:.1f} lần khi bị 'nã' dồn dập!")
    print("=========================================================")