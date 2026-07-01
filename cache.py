import json
from datetime import datetime
import redis

from db_helper import cache, get_recent_posts


# Đảm bảo đối tượng cache của bạn đã được khởi tạo ở đâu đó trong file hoặc import từ models
# cache = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_cached_posts(limit, category_id, ttl=300):
    # print("Đây là ma code moi, dang bindmount tu docker compose")
    cache_key = f"posts:cat_{category_id}:limit_{limit}"

    # -----------------------------------------------------------------
    # 1. THỬ LẤY DỮ LIỆU TỪ RAM REDIS (CACHE HIT)
    # -----------------------------------------------------------------
    try:
        cached_data = cache.get(cache_key)
        if cached_data:
            posts = json.loads(cached_data)

            # Khôi phục kiểu dữ liệu datetime từ chuỗi string để Jinja2 .strftime không bị lỗi
            for post in posts:
                if post.get('created_at') and isinstance(post['created_at'], str):
                    try:
                        post['created_at'] = datetime.strptime(post['created_at'], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        pass
            return posts
    except redis.RedisError as e:
        print(f"❌ Redis Error khi đọc cache: {e}")

    # -----------------------------------------------------------------
    # 2. CACHE MISS -> TĂNG SỐ ĐẾM & GỌI XUỐNG SQL SERVER THẬT
    # -----------------------------------------------------------------
    try:
        # Tăng số đếm tổng số lần hệ thống phải chọc xuống DB thật
        cache.incr('real_db_call_count')
    except redis.RedisError as e:
        print(f"❌ Không thể tăng số đếm real_db_call_count trên Redis: {e}")

    try:
        # Gọi hàm gốc lấy dữ liệu từ SQL Server qua pyodbc
        posts = get_recent_posts(limit=limit, category_id=category_id)
        if not posts or not isinstance(posts, list):
            posts = []
    except Exception as db_err:
        print(f"❌ SQL Server bị lỗi kết nối hoặc Timeout: {db_err}")
        # Trả về mảng rỗng fail-safe để tránh crash sập trang web lỗi 500
        return []

    # -----------------------------------------------------------------
    # 3. CHUẨN BỊ DỮ LIỆU TRẢ VỀ CHO FLASK VÀ GHI VÀO REDIS
    # -----------------------------------------------------------------
    redis_posts = []

    for post in posts:
        if not isinstance(post, dict):
            continue

        # Tạo bản sao shallow sao chép dictionary để không làm biến đổi mảng gốc trả về cho Flask
        post_copy = post.copy()

        if post.get('created_at'):
            # Chiều ghi vào Redis: Ép buộc đối tượng datetime thành chuỗi string JSON-safe
            if isinstance(post['created_at'], datetime):
                post_copy['created_at'] = post['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(post['created_at'], str):
                post_copy['created_at'] = post['created_at']

            # Chiều trả về cho Jinja2 render: Ép buộc phải là đối tượng datetime
            if isinstance(post['created_at'], str):
                try:
                    post['created_at'] = datetime.strptime(post['created_at'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # Nếu chuỗi ngày tháng bị dị dạng, gán tạm datetime hiện tại để tránh crash giao diện
                    post['created_at'] = datetime.now()

        redis_posts.append(post_copy)

    # Chỉ thực hiện lưu vào Redis nếu Database thực sự có dữ liệu trả về
    if posts:
        try:
            cache.setex(cache_key, ttl, json.dumps(redis_posts, ensure_ascii=False))
        except redis.RedisError as e:
            print(f"❌ Không thể ghi dữ liệu cache mới vào Redis: {e}")

    return posts


import json
from datetime import datetime
import redis
from db_helper import get_post_by_id  # Import hàm gốc từ database


def get_cached_post_by_id(post_id, ttl=600):
    """
    Chỉ cache duy nhất nội dung chi tiết bài viết (giữ trong RAM 10 phút).
    """
    print("Đây là ma code moi, dang bindmount tu docker compose")
    cache_key = f"post:detail:{post_id}"

    # 1. THỬ LẤY TỪ RAM REDIS
    try:
        cached_data = cache.get(cache_key)
        if cached_data:
            post = json.loads(cached_data)

            # Khôi phục kiểu dữ liệu datetime object cho Jinja2 render
            for field in ['created_at', 'updated_at']:
                if post.get(field) and isinstance(post[field], str):
                    try:
                        post[field] = datetime.strptime(post[field], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        pass
            return post
    except redis.RedisError as e:
        print(f"❌ Redis Error khi đọc chi tiết post: {e}")

    # 2. CACHE MISS -> TĂNG METRICS & GỌI XUỐNG SQL SERVER
    try:
        cache.incr('real_db_call_count')
    except redis.RedisError as e:
        print(f"❌ Không thể tăng số đếm real_db_call_count: {e}")

    try:
        post = get_post_by_id(post_id)
        if not post:
            return None
    except Exception as db_err:
        print(f"❌ SQL Server bị lỗi hoặc Timeout khi đọc post {post_id}: {db_err}")
        return None

    # 3. CHUẨN BỊ GHI CACHE VÀ TRẢ VỀ
    post_copy = post.copy()

    # Chiều ghi vào Redis: Chuyển sang string an toàn với chuỗi JSON
    for field in ['created_at', 'updated_at']:
        if post.get(field):
            if isinstance(post[field], datetime):
                post_copy[field] = post[field].strftime('%Y-%m-%d %H:%M:%S')

            # Chiều trả về luôn giữ datetime object cho Flask
            if isinstance(post[field], str):
                try:
                    post[field] = datetime.strptime(post[field], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass

    try:
        cache.setex(cache_key, ttl, json.dumps(post_copy, ensure_ascii=False))
    except redis.RedisError as e:
        print(f"❌ Không thể ghi cache bài viết vào Redis: {e}")

    return post