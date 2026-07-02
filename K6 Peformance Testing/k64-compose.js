import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  // SỬ DỤNG SCENARIOS ĐỂ CHIA TỶ LỆ KỊCH BẢN HỖN HỢP
  scenarios: {
    // Luồng 1: Khách vãng lai truy cập trang chủ (Read-heavy)
    guest_browsing: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 800 }, // Tăng vọt lên 250 user
        { duration: '1m', target: 800 },
        { duration: '30s', target: 0 },
      ],
      exec: 'browsingFlow', // Trỏ tới function browsingFlow ở dưới
    },
    // Luồng 2: Thực hiện đăng nhập (Write-heavy)
    user_login: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 200 }, // Cùng lúc đó, tăng vọt 100 user đăng nhập
        { duration: '1m', target: 200 },
        { duration: '30s', target: 0 },
      ],
      exec: 'loginFlow', // Trỏ tới function loginFlow ở dưới
    },
  },

  thresholds: {
    // 1. Kiểm tra tỷ lệ lỗi chung toàn hệ thống
    http_req_failed: ['rate<0.01'],

    // 2. ĐO THỜI GIAN THEO TỪNG ENDPOINT CỤ THỂ BẰNG TAGS
    // p(95) nghĩa là: 95% số request phải hoàn thành dưới mức thời gian này
    'http_req_duration{name:GET_Homepage}': ['p(95)<1000'],    // Homepage < 1s
    'http_req_duration{name:GET_Login_Page}': ['p(95)<1500'],  // GET form login < 1.5s
    'http_req_duration{name:POST_Login_Submit}': ['p(95)<3000'], // Xử lý POST login < 3s
  },
};

const BASE_URL = 'http://localhost';

// ==========================================
// KỊCH BẢN 1: DÀNH CHO KHÁCH VÃNG LAI
// ==========================================
export function browsingFlow() {
  // Thêm thuộc tính { tags: { name: '...' } } để k6 bóc tách số liệu
  const res = http.get(`${BASE_URL}/`, { tags: { name: 'GET_Homepage' } });

  check(res, {
    'Trang chủ tải thành công': (r) => r.status === 200,
  });

  sleep(Math.random() * 2 + 1); // Tạm nghỉ ngẫu nhiên 1-3s giữa các vòng lặp
}

// ==========================================
// KỊCH BẢN 2: DÀNH CHO ĐĂNG NHẬP
// ==========================================
export function loginFlow() {
  const url = `${BASE_URL}/login`;

  // BƯỚC 1: GET trang login
  // Gắn tag 'GET_Login_Page'
  const resGet = http.get(url, { tags: { name: 'GET_Login_Page' } });
  const csrfToken = resGet.html().find('input[name="csrf_token"]').val() || '';

  check(resGet, {
    'Trang GET tải thành công và có CSRF Token': (r) => r.status === 200 && csrfToken !== '',
  });

  // BƯỚC 2: POST đăng nhập
  const payload = {
    username: 'Putin',
    password: 'admin_password',
    csrf_token: csrfToken,
  };

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    // Gắn tag 'POST_Login_Submit'
    tags: { name: 'POST_Login_Submit' },
  };

  sleep(1); // Thời gian giả lập người dùng điền form

  const resPost = http.post(url, payload, params);

  check(resPost, {
    'Đăng nhập thành công (Trả về 302 hoặc 200)': (r) => r.status === 200 || r.status === 302,
  });

  sleep(2);
}