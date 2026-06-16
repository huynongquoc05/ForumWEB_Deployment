# Forum Web Deployment

Deploy một ứng dụng forum Flask lên Kubernetes, với đầy đủ autoscaling, monitoring và CI/CD. Repo này cover toàn bộ phần infrastructure và deployment — từ Docker Compose cho dev đến K8s cho production-like environment.

![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white) ![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white) ![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white) ![Grafana](https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

<img width="1528" height="839" alt="image" src="https://github.com/user-attachments/assets/878430d5-df7d-4027-ad06-913943a7747d" />

---

## Kiến trúc

```
 Client ──HTTP──► Nginx Ingress
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
flask-forum     grafana      prometheus
     │
     ├── read/write ──► sqlserver svc
     │◄───────────────┤
     │
     ├── get/set ─────► redis svc
     │◄───────────────┤
        

HPA: 4 → 9 replicas (trigger: CPU avg > 150m)
```

---

## Cấu trúc thư mục

```
├── Docker/
│   ├── deploy_docker_compose.sh    # Script deploy Docker Compose
│   ├── docker-compose.yaml         # App stack (Nginx, Flask, SQL Server, Redis)
│   └── monitoring-compose.yaml     # Monitoring stack (Prometheus, Grafana, ...)
│
├── K8S/
│   ├── Deploy_k8s.sh               # Script deploy toàn bộ K8s từ đầu
│   ├── Deploy_forum_app_stacks_k8s.yaml
│   ├── monitoring-ingress-k8s.yaml
│   
│
├── kiem_thu_dot_bien.js            # k6 load test script
└── .env.example
└── patch.json
```

---

## Điểm thiết kế đáng chú ý

**Multi-stage Dockerfile**
Build stage cài compiler toolchain để compile `pyodbc`. Runtime stage chỉ copy `/opt/venv` sang — không có `gcc`, `g++` hay build deps trong image production. Giảm attack surface và image size đáng kể.

**Network isolation trong Docker Compose**
Tách `frontend_network` và `backend_network`. Nginx chỉ thấy Flask, Flask mới thấy SQL Server và Redis. Database không bao giờ expose ra ngoài.

**HPA scale up tức thì, scale down chậm**
`stabilizationWindowSeconds: 0` cho scale up — pod mới tạo ngay khi CPU vượt ngưỡng, không chờ. Scale down giữ window 60s để tránh pod bị thu hồi rồi lại phải tạo lại khi traffic chỉ giảm tạm thời.

**Automation script end-to-end**
`Deploy_k8s.sh` xử lý toàn bộ: apply manifests → wait pods ready → inject SQL seed data.

---

## Yêu cầu

- Docker
- kubectl, helm
- File `.env` 
```
ACCEPT_EULA=Y
MSSQL_SA_PASSWORD=YourStrongPassword123!
REDIS_HOST=redis
DB_SERVER=sqlserver
DB_NAME=ForumWEB
DB_USER=sa
DB_PASSWORD=YourStrongPassword123!
FLASK_SECRET_KEY=supersecretkeyandhardtoguess
```
---

## Cách chạy

### Docker Compose (dev/test)

```bash
chmod +x Docker/deploy_docker_compose.sh
./Docker/deploy_docker_compose.sh
```

### Kubernetes

```bash
chmod +x K8S/Deploy_k8s.sh
./K8S/Deploy_k8s.sh
```


---

## Performance testing

> Thực hiện trên cluster (AWS EC2, 2 worker nodes). Kết quả phản ánh hiệu năng thực tế của hạ tầng.

Script `kiem_thu_dot_bien.js` dùng k6, tăng dần lên 300 VUs qua 4 stages. Mỗi VU thực hiện GET `/login` → parse CSRF token → POST đăng nhập. Bước lấy CSRF token là bắt buộc vì Flask bật CSRF protection — request thiếu token bị từ chối ngay (Xem chi tiết trong file).
```
stages: [
    { duration: '30s', target: 75 },
    { duration: '1m', target: 300 },
    { duration: '30s', target: 300 },
    { duration: '30s', target: 0 },
  ],
```
```bash
 k6 run .\kiem_thu_dot_bien.js
```

### Kết quả so sánh: có HPA vs không có HPA

| Chỉ số | Có HPA (4→9 pods) | Không HPA (4 pods cố định) |
|---|---|---|
| Avg latency | 256ms | 1,450ms |
| p90 latency | 442ms | 2,960ms |
| p95 latency | 599ms | 3,580ms |
| Max latency | 3.72s | 11.37s |
| Iterations hoàn thành | 14,724 | 4,943 |
| Throughput | 97.7 iter/s | 32.7 iter/s |
| Error rate | 0.06% | 0.00% |

> Lưu ý: error rate 0% khi không có HPA không có nghĩa là hệ thống hoạt động tốt hơn — server đang xử lý chậm thay vì từ chối request, response time kéo dài đến 11s nhưng vẫn trả về 200/302 nên không tính là lỗi. Throughput thấp hơn 3x là hệ quả trực tiếp của việc VU phải chờ lâu hơn mới hoàn thành mỗi iteration.

### Quan sát HPA trong quá trình test

Idle bình thường mỗi pod chỉ dùng ~1% CPU. Khi k6 bắt đầu bắn tải, CPU trung bình vượt ngưỡng 150% và tiếp tục leo lên 285% — HPA scale từ 4 → 7→ 9 pods. `stabilizationWindowSeconds: 0` cho scale up nên pod mới được tạo gần như ngay lập tức, không chờ.

Sau khi k6 ngừng, CPU rớt về thấp nhưng HPA giữ nguyên replica thêm 60s (window scale down) trước khi thu hồi pod thừa — tránh trường hợp traffic chỉ giảm tạm thời mà đã vội scale down rồi lại phải scale up lại.

<img width="1247" height="518" alt="image" src="https://github.com/user-attachments/assets/9dfb76c5-f3b8-4280-a15a-9df0521f853c" />


```
http_req_duration: avg=256ms  p(90)=442ms  p(95)=599ms
http_req_failed:   0.06%  (27 / 44145 requests)
iterations:        14724  (97.7/s)
```