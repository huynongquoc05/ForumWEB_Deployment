import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 75 },   // Tăng dần tải lên 75 VUs
    { duration: '1m', target: 350 },   // Ép xung lên 350 VUs trong 1 phút
    { duration: '30s', target: 350 },  // Duy trì đỉnh tải 350 VUs liên tục 30 giây
    { duration: '30s', target: 0 },    // Hạ tải dần về 0
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],    // Tỷ lệ lỗi phải dưới 1%
    http_req_duration: ['avg<5000'],   // Thời gian phản hồi trung bình dưới 5 giây
  },
};

const BASE_URL = 'http://localhost';

export default function () {
  // Chỉ nã duy nhất vào trang chi tiết bài viết số 13
  const postUrl = `${BASE_URL}/post/13`;
  const res = http.get(postUrl);

  check(res, {
    'Tải trang chi tiết post 13 thành công (200)': (r) => r.status === 200,
  });

  // Mô phỏng người dùng thật dừng lại đọc bài viết 1 giây trước khi chuyển tiếp
  sleep(1);
}