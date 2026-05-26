import os

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app, abort
from werkzeug.utils import secure_filename

from models import check_exists, SaveToDB, hash_password
from models import get_post_by_id,get_recent_posts,get_comments_by_post_id,get_post_reaction_count
auth = Blueprint('auth', __name__)
from flask import current_app
@auth.route('/')
def index():
    # Kiểm tra xem người dùng đã đăng nhập hay chưa
    if 'username' in session:
        username = session['username']
        # print("Người dùng đã đăng nhập:", username)
        #ghi ip máy chủ và máy truy cập


        recent_posts = get_recent_posts(10,category_id=4)  # Lấy 10 bài viết mới nhất
        qa_posts = get_recent_posts(10, category_id=3)

        return render_template(
            'index.html',
            username=username, recent_posts=recent_posts,qa_posts=qa_posts)


    recent_posts = get_recent_posts(10,category_id=4)  # Lấy 10 bài viết mới nhất
    qa_posts = get_recent_posts(10, category_id=3)
    # print(qa_posts)
    session['next'] = request.url  # Lưu URL hiện tại
    return render_template('index.html', username=None, recent_posts=recent_posts,qa_posts=qa_posts)

@auth.route('/faq')
def faq():
    # Lấy tất cả bài viết thuộc chuyên mục Hỏi đáp (ví dụ với category_id=1)
    faq_posts = get_recent_posts(limit=None, category_id=3)
    return render_template('faq.html', posts=faq_posts)

@auth.route('/news')
def news():
    # Lấy tất cả bài viết thuộc chuyên mục Tin tức (ví dụ với category_id=2)
    news_posts = get_recent_posts(limit=None, category_id=4)
    return render_template('news.html', posts=news_posts)
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Kiểm tra và lấy thông tin người dùng, bao gồm role
        user = check_exists(username, password)
        if user:  # Nếu tìm thấy người dùng
            session['username'] = user[1]  # Lưu username vào session
            session['user_id'] = user[0]  # Lưu user_id vào session
            session['role'] = user[2]  # Lưu role vào session
            print(f"{user[1]} đã đăng nhập với vai trò {user[2]}")
            # Kiểm tra URL trước đó trong session
            next_url = session.pop('next', None)  # Lấy URL đã lưu và xóa nó
            if next_url:
                return redirect(next_url)  # Chuyển hướng về URL trước đó
            return redirect(url_for('auth.index'))  # Nếu không có URL thì quay về trang chính

        else:
            flash('Tên đăng nhập hoặc mật khẩu không chính xác.', 'error')  # Thông báo lỗi
    return render_template('Login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        if not username or not password:
            flash('Username and password are required.', 'error')
        elif check_exists(username, password):
            flash('Username already exists.', 'error')
        else:
            SaveToDB(username, password, email)
            flash('Registration successful!', 'success')
            return redirect(url_for('auth.login'))

    return render_template('registration.html')


@auth.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    print("Đăng xuất thành công",session)
    return redirect(url_for('auth.index'))


from flask import render_template, request, redirect, url_for, flash, session
from models import get_categories, save_post


def allowed_file(filename):
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@auth.route('/addPost', methods=['GET', 'POST'])
def add_post():
    if 'username' not in session:
        flash('Bạn cần đăng nhập để thêm bài viết.')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        title = request.form.get('title')
        category_id = request.form.get('category_id')
        content = request.form.get('content')
        from models import parse_custom_syntax, add_paragraph_tags
        # Xử lý cú pháp tùy chỉnh và thêm thẻ <p>
        content = parse_custom_syntax(content)
        content = add_paragraph_tags(content)
        is_admin = session.get('role')
        # Gọi hàm lưu bài viết vào CSDL với nội dung đã xử lý
        status = save_post(title, content, category_id, session['user_id'], is_admin)
        # Lưu các tệp ảnh
        if 'images' in request.files:
            files = request.files.getlist('images')
            upload_folder = current_app.config['UPLOAD_FOLDER']
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(upload_folder, filename))
                    content += f'\n<img src="{url_for("static", filename="uploads/" + filename)}" alt="">\n'
        # Chuyển hướng đến trang thông báo thành công thay vì trang chủ
        return render_template('post_success.html', status=status)



    categories = get_categories()  # Gọi hàm lấy danh mục nếu có
    return render_template('addPost.html', categories=categories)
@auth.route('/updatePosts/<int:post_id>', methods=['GET', 'POST'])
def update_post(post_id):
    # Kiểm tra người dùng có đăng nhập và là chủ sở hữu của bài viết không
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập để cập nhật bài viết.')
        return redirect(url_for('auth.login'))
    from models import parse_custom_syntax_reverse, parse_custom_syntax, save_updated_post,get_post_by_id0,add_paragraph_tags
    post = get_post_by_id0(post_id)

    if not post or post[4] != session['user_id']:
        flash('Bạn không có quyền chỉnh sửa bài viết này.')
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        title = request.form.get('title')
        category_id = request.form.get('category_id')
        content = request.form.get('content')

        # Xử lý cú pháp và lưu lại bài viết
        content = parse_custom_syntax(content)
        content = add_paragraph_tags(content)
        save_updated_post(post_id, title, content, category_id)

        # Hiển thị thông báo cập nhật thành công
        return render_template('update_success.html', status=post[5],post_id=post_id)

    # Chuyển nội dung về cú pháp gốc để hiển thị trong form cập nhật
    content = parse_custom_syntax_reverse(post[2])
    categories = get_categories()

    return render_template(
        'updateposts.html',
        title=post[1],
        category_id=post[3],
        content=content,
        categories=categories
    )
@auth.route('/post/<int:post_id>')
def view_post(post_id):
    from models import get_user_comment_reaction
    post = get_post_by_id(post_id)
    if post is None:
        flash('Bài viết không tồn tại hoặc chưa được phê duyệt.', 'error')
        return redirect(url_for('auth.index'))

    user_id = session.get('user_id')
    # print(f"{session.get('username')} đang xem bài viết {post_id} ")
    comments = get_comments_by_post_id(post_id)
    reaction_count = get_post_reaction_count(post_id)
    # print(post['author_id'])
    # Lấy phản ứng của người dùng cho bài viết
    user_comment_reaction = get_user_comment_reaction(post_id, user_id)

    # Tạo liên kết đến trang cá nhân của tác giả
    author_profile_link = url_for('auth.personal_page', user_id=post['author_id'])

    session['next'] = request.url  # Lưu URL hiện tại
    return render_template('post_detail.html', post=post, comments=comments, reaction_count=reaction_count,
                           user_comment_reaction=user_comment_reaction, author_profile_link=author_profile_link)



from flask import jsonify

@auth.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập để bình luận.', 'error')
        print("bạn cần đănh nhập để bình luận")

        return redirect(url_for('auth.login'))  # Chuyển hướng sang trang đăng nhập
    from models import add_comment_to_db
    content = request.form.get('content')
    parent_comment_id = request.form.get('parent_comment_id', None)
    user_id = session['user_id']  # ID người dùng

    # Gọi hàm xử lý từ models.py
    add_comment_to_db(post_id, parent_comment_id, user_id, content)
    print(f"Người dùng {session.get('username')} đã thêm bình luận cho bài viết {post_id}")
    flash('Bình luận đã được thêm.', 'success')
    return redirect(url_for('auth.view_post', post_id=post_id))


@auth.route('/comment/<int:comment_id>/update', methods=['POST'])
def update_comment( comment_id):
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập để chỉnh sửa bình luận.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    content = request.form.get('content')
    from models import can_user_edit_comment,update_comment_in_db
    # Kiểm tra quyền chỉnh sửa bình luận
    if not can_user_edit_comment(comment_id, user_id):
        flash('Bạn không có quyền chỉnh sửa bình luận này.', 'error')
        next_url = session.pop('next', None)
        if next_url:
            return redirect(next_url)  # Chuyển hướng về URL trước đó

    # Cập nhật bình luận trong CSDL
    update_comment_in_db(comment_id, content)
    flash('Bình luận đã được cập nhật.', 'success')
    next_url = session.pop('next', None)
    if next_url:
        return redirect(next_url)  # Chuyển hướng về URL trước đó



@auth.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập để xóa bình luận.', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    from models import can_user_edit_comment, delete_comment_from_db

    # Kiểm tra quyền xóa bình luận
    if not can_user_edit_comment(comment_id, user_id):
        flash('Bạn không có quyền xóa bình luận này.', 'error')
        next_url = session.pop('next', None)
        if next_url:
            return redirect(next_url)  # Chuyển hướng về URL trước đó

    # Xóa bình luận trong CSDL
    delete_comment_from_db(comment_id)
    flash('Bình luận đã được xóa.', 'success')
    next_url = session.pop('next', None)
    if next_url:
        return redirect(next_url)  # Chuyển hướng về URL trước đó
    return redirect(url_for('auth.view_post'))



@auth.route('/post/<int:post_id>/react', methods=['POST'])
def react(post_id):
    from models import handle_reaction

    # Kiểm tra xem người dùng đã đăng nhập chưa
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401  # Trả về mã lỗi 401

    reaction_type = request.form.get('reaction_type')
    user_id = session['user_id']  # ID người dùng

    # Gọi hàm xử lý từ models.py
    reaction_count = handle_reaction(post_id, user_id, reaction_type)

    return jsonify({'status': 'success', 'reaction_count': reaction_count})



@auth.route('/react_comment/<int:post_id>', methods=['POST'])
def react_comment(post_id):
    if 'user_id' not in session:
        # Nếu chưa đăng nhập, trả về thông báo lỗi dưới dạng JSON
        return jsonify(status='error', message='Bạn cần đăng nhập để thêm cảm xúc.'), 401

    user_id = session['user_id']
    reaction_type = request.form.get('reaction_type')
    comment_id = request.form.get('comment_id')
    from models import update_comment_reaction

    # Cập nhật cảm xúc cho bình luận trong cơ sở dữ liệu
    reaction_count = update_comment_reaction(comment_id, user_id, reaction_type)

    # Trả về số cảm xúc mới dưới dạng JSON
    return jsonify(status='success', reaction_count=reaction_count)


# Trang cá nhân
@auth.route('/PersonalPageUser/<int:user_id>')
def personal_page(user_id):
    """Hiển thị trang cá nhân của người dùng."""
    from models import get_user_info_and_posts
    # Kiểm tra xem người dùng có phải là admin không
    is_admin = session.get('role')
    user_info, posts = get_user_info_and_posts(user_id, is_admin)
    post_ofUser = []

    for post in posts:
        # Kiểm tra user_id và status trong mỗi bài viết
        if post['user_id'] == user_id and post['status'] == 'approved':
            post_ofUser.append(post)
    # Sắp xếp post_ofUser theo 'created_at' giảm dần
    post_ofUser = sorted(post_ofUser, key=lambda x: x['created_at'], reverse=True)

    if user_info is None:
        return "Người dùng không tồn tại", 404

    # Render template với thông tin người dùng và bài viết
    return render_template('UserPage.html',
                           username=user_info['username'],
                           role=user_info['role'],
                           created_at=user_info['created_at'],
                           posts=post_ofUser)


@auth.route('/account_management/<string:username>')
def account_management(username):
    """Trang quản lý tài khoản với lịch sử hoạt động của người dùng."""

    # Kiểm tra người dùng có đăng nhập và khớp với session
    if 'username' not in session or session['username'] != username:
        return redirect(url_for('auth.index'))

    from models import get_user_info_and_posts, get_activity_history

    # Kiểm tra xem người dùng có phải là admin không
    is_admin = session.get('role')
    print(is_admin)
    # Lấy thông tin người dùng và bài viết phù hợp
    user_info, posts = get_user_info_and_posts(session['user_id'], is_admin)
    print("người dùng và số bài viết",user_info['users_post_counts'])
    # Sắp xếp post_ofUser theo 'created_at' giảm dần
    posts = sorted(posts, key=lambda x: x['created_at'], reverse=True)
    if user_info is None:
        return "Người dùng không tồn tại", 404
    user_id=session['user_id']
    # Lấy lịch sử hoạt động của người dùng
    activity_history = get_activity_history(session['user_id'])
    print(activity_history)
    session['next'] = request.url  # Lưu URL hiện tại
    # Render template với thông tin người dùng và danh sách bài viết
    return render_template('account_management.html',
                           user_info=user_info,
                           posts=posts,
                           is_admin=is_admin,
                           activity_history=activity_history)


@auth.route('/approve_post/<int:post_id>', methods=['POST'])
def approve_post(post_id):
    """Duyệt bài viết."""
    from models import approve_post_in_db
    approve_post_in_db(post_id)
    # Kiểm tra URL trước đó trong session
    next_url = session.pop('next', None)
    if next_url:
        return redirect(next_url)  # Chuyển hướng về URL trước đó

@auth.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    """Xóa bài viết."""
    from models import delete_post_in_db
    delete_post_in_db(post_id)
    # Kiểm tra URL trước đó trong session
    next_url = session.pop('next', None)
    if next_url:
        return redirect(next_url)  # Chuyển hướng về URL trước đó


@auth.route('/view_pendingPost/<int:post_id>', methods=['GET'])
def view_pending_post(post_id):
    # Kiểm tra nếu người dùng không phải là admin

    from models import get_pending_posts_byId
    # Lấy thông tin bài viết
    post = get_pending_posts_byId(post_id)
    if not post:
        flash('Không tìm thấy bài viết.', 'error')
        return redirect(url_for('auth.index'))
    if session.get('role') != 'admin' and post[5] != session['user_id']:
        abort(403)

    # Render template
    return render_template('pendingPost.html', post=post)

# Route tìm kiếm sử dụng auth.route
@auth.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').strip()
    if not query:
        flash("Vui lòng nhập từ khóa để tìm kiếm.", 'error')
        return redirect(url_for('index'))
    from models import search_posts_by_keyword,search_users_by_keyword
    # Gọi hàm truy vấn dữ liệu từ CSDL
    users = search_users_by_keyword(query)
    posts = search_posts_by_keyword(query)

    return render_template('search.html', query=query, users=users, posts=posts)

# Viết 1 route đếm số người truy cập trang web sử dụng Redis để lưu trữ số lượt truy cập
@auth.route('/visit_count')
def visit_count():
    from models import cache
    count = cache.incr('visit_count')
    return f'Số lượt truy cập trang web: {count}'