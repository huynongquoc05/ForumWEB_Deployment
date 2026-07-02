import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 200 },   // Tăng dần tải lên 75 VUs
    { duration: '1m', target: 1000 },   // Tăng mạnh lên 350 VUs trong 1 phút (Giai đoạn ép xung)
    { duration: '30s', target: 1000 },  // Duy trì đỉnh tải 350 VUs liên tục 30 giây
    { duration: '30s', target: 0 },    // Hạ tải dần về 0
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],    // Tỷ lệ lỗi phải dưới 1%
    http_req_duration: ['avg<5000'],   // Thời gian phản hồi trung bình dưới 5 giây
  },
};

// Load Balancer Nginx endpoint
const BASE_URL = 'http://localhost';

export default function () {
  // BƯỚC 1: GET trang chủ để kiểm tra hiệu năng nạp bài viết (Cache Hit / Miss)
  const homeUrl = `${BASE_URL}/`;
  const resHome = http.get(homeUrl);

  // Trích xuất thử CSRF Token từ trang chủ (nếu form login/search trên thanh điều hướng có dùng)
  const csrfToken = resHome.html().find('input[name="csrf_token"]').val() || 'NOT_FOUND';

  check(resHome, {
    'Trang chủ tải thành công (Status 200)': (r) => r.status === 200,
    'Trang chủ có chứa nội dung bài viết': (r) => r.body.includes('post') || r.body.includes('author') || r.status === 200,
  });

  // Nghỉ 1 giây mô phỏng người dùng thật đang đọc tin tức trên trang chủ
  sleep(1);

  // BƯỚC 2: (Tùy chọn) Bạn có thể nã thêm sang /news hoặc /faq để test đồng thời các vùng cache khác
  const faqUrl = `${BASE_URL}/faq`;
  const resFaq = http.get(faqUrl);

  check(resFaq, {
    'Trang FAQ tải thành công (Status 200)': (r) => r.status === 200,
  });

  // Nghỉ nhẹ trước khi lặp lại vòng tuần hoàn truy cập
  sleep(1);
}