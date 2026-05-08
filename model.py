class Users:
    def __init__(self, user_id, username, password, email, role):
        self.user_id = user_id
        self.username = username
        self.password = password
        self.email = email
        self.role = role

    def showInfor(self):
        print(
            f'Mã người dùng: {self.user_id}, \nTên người dùng: {self.username}, '
            f'\nMật khẩu: {self.password}, \nEmail: {self.email}, \nVai trò: {self.role}'
        )


class Categories:
    def __init__(self, category_id, name, description):
        self.category_id = category_id
        self.name = name
        self.description = description

    def showInfor(self):
        print(
            f'Mã chuyên mục: {self.category_id}, \nTên chuyên mục: {self.name}, '
            f'\nMô tả: {self.description}'
        )


class Posts:
    def __init__(self, post_id, title, content, category_id, user_id, status, created_at, updated_at):
        self.post_id = post_id
        self.title = title
        self.content = content
        self.category_id = category_id
        self.user_id = user_id
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    def showInfor(self):
        print(
            f'Mã bài viết: {self.post_id}, \nTiêu đề: {self.title}, \nNội dung: {self.content}, '
            f'\nChuyên mục ID: {self.category_id}, \nTác giả ID: {self.user_id}, '
            f'\nTrạng thái: {self.status}, \nNgày tạo: {self.created_at}, \nNgày cập nhật: {self.updated_at}'
        )


class Comments:
    def __init__(self, comment_id, post_id, parent_comment_id, user_id, content, created_at):
        self.comment_id = comment_id
        self.post_id = post_id
        self.parent_comment_id = parent_comment_id
        self.user_id = user_id
        self.content = content
        self.created_at = created_at

    def showInfor(self):
        print(
            f'Mã bình luận: {self.comment_id}, \nBài viết ID: {self.post_id}, '
            f'\nBình luận cha ID: {self.parent_comment_id}, \nTác giả ID: {self.user_id}, '
            f'\nNội dung: {self.content}, \nNgày tạo: {self.created_at}'
        )


class Reactions:
    def __init__(self, reaction_id, user_id, post_id, comment_id, reaction_type, created_at):
        self.reaction_id = reaction_id
        self.user_id = user_id
        self.post_id = post_id
        self.comment_id = comment_id
        self.reaction_type = reaction_type
        self.created_at = created_at

    def showInfor(self):
        print(
            f'Mã cảm xúc: {self.reaction_id}, \nNgười dùng ID: {self.user_id}, '
            f'\nBài viết ID: {self.post_id}, \nBình luận ID: {self.comment_id}, '
            f'\nLoại cảm xúc: {self.reaction_type}, \nThời gian: {self.created_at}'
        )
