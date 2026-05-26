import http from 'k6/http';
import { check, sleep } from 'k6';

// 1. Cấu hình kịch bản chịu tải an toàn cho máy 8GB RAM
export const options = {
  stages: [
    { duration: '30s', target: 75 },  // Trong 30s đầu: Tăng từ từ lên 50 user
    { duration: '1m', target: 300 },  // 1 phút tiếp theo: Tăng dần lên 200 user (Để Gunicorn có thời gian xoay vòng xử lý)
    { duration: '30s', target: 300 }, // Giữ nguyên tải đỉnh 200 user trong 30s
    { duration: '30s', target: 0 },   // Hạ nhiệt, giảm dần về 0 user
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],   // Vẫn giữ kỳ vọng lỗi < 1%
    http_req_duration: ['avg<5000'],
  },
};

export default function () {
  // Tạo khoảng trễ ngẫu nhiên (0-5s) ở vòng lặp đầu tiên
  // Để tránh tình trạng 200 user đồng loạt "dội bom" ngay giây số 0
//  if (__ITER === 0) {
//    sleep(Math.random() * 5);
//  }

  const url = 'http://flask-forum-service:8005/login';

  // ==========================================
  // BƯỚC 1: TRUY CẬP TRANG LOGIN ĐỂ LẤY TOKEN
  // ==========================================
  const resGet = http.get(url);

  // Dùng hàm find() của k6 để tìm thẻ input ẩn chứa CSRF Token trong mã HTML
  // Ghi chú: Nếu web của bạn đặt tên khác cho thẻ này (ví dụ: csrfmiddlewaretoken), hãy đổi lại cho khớp.
  const csrfToken = resGet.html().find('input[name="csrf_token"]').val() || '';

  // Kiểm tra xem có lấy được token không (tùy chọn, giúp debug dễ hơn)
  check(resGet, {
    'Trang GET tải thành công và có CSRF Token': (r) => r.status === 200 && csrfToken !== '',
  });

  // ==========================================
  // BƯỚC 2: GỬI REQUEST POST ĐĂNG NHẬP
  // ==========================================
  const payload = {
    username: 'Putin',
    password: 'admin_password',
    csrf_token: csrfToken, // <--- Đạn xuyên giáp đã được nạp
  };

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  };

  // Nghỉ 1 giây để mô phỏng thời gian người dùng gõ phím user/pass
  sleep(1);

  // Bắn request POST lên server
  const resPost = http.post(url, payload, params);

  // Kiểm tra kết quả trả về từ Flaskk
  // Chú ý: Vì Flask dùng Redirect khi login thành công, mã trạng thái sẽ là 302 Found
  check(resPost, {
    'Đăng nhập thành công (Trả về 302 hoặc 200)': (r) => r.status === 200 || r.status === 302,
  });
}