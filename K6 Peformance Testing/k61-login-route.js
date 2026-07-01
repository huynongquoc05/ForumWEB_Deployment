//import http from 'k6/http';
//import { check, sleep } from 'k6';
//
//export const options = {
//  stages: [
//    { duration: '30s', target: 75 },
//    { duration: '1m', target: 350 },
//    { duration: '30s', target: 350 },
//    { duration: '30s', target: 0 },
//  ],
//  thresholds: {
//    http_req_failed: ['rate<0.01'],
//    http_req_duration: ['avg<5000'],
//  },
//};
//
//// Danh sách các worker endpoint
//const WORKERS = [
//  'http://54.255.247.142:32546',
//  'http://13.212.254.166:32546',
//];
//
//export default function () {
//  // Phân phối VU đều sang 2 worker, dùng __VU để tránh mọi VU đều chọn cùng 1 node
//  const baseUrl = WORKERS[__VU % WORKERS.length];
//  const url = `${baseUrl}/login`;
//
//  // BƯỚC 1: GET trang login để lấy CSRF Token
//  const resGet = http.get(url);
//  const csrfToken = resGet.html().find('input[name="csrf_token"]').val() || '';
//
//  check(resGet, {
//    'Trang GET tải thành công và có CSRF Token': (r) => r.status === 200 && csrfToken !== '',
//  });
//
//  // BƯỚC 2: POST đăng nhập
//  const payload = {
//    username: 'Putin',
//    password: 'admin_password',
//    csrf_token: csrfToken,
//  };
//
//  const params = {
//    headers: {
//      'Content-Type': 'application/x-www-form-urlencoded',
//    },
//  };
//
//  sleep(1);
//
//  const resPost = http.post(url, payload, params);
//
//  check(resPost, {
//    'Đăng nhập thành công (Trả về 302 hoặc 200)': (r) => r.status === 200 || r.status === 302,
//  });
//}

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 75 },
    { duration: '1m', target: 350 },
    { duration: '30s', target: 350 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['avg<5000'],
  },
};

// Load Balancer Nginx endpoint
const BASE_URL = 'http://localhost';

export default function () {
  const url = `${BASE_URL}/login`;

  // BƯỚC 1: GET trang login để lấy CSRF Token
  const resGet = http.get(url);

  const csrfToken = resGet.html().find('input[name="csrf_token"]').val() || '';

  check(resGet, {
    'Trang GET tải thành công và có CSRF Token': (r) =>
      r.status === 200 && csrfToken !== '',
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
  };

  sleep(1);

  const resPost = http.post(url, payload, params);

  check(resPost, {
    'Đăng nhập thành công (Trả về 302 hoặc 200)': (r) =>
      r.status === 200 || r.status === 302,
  });
}