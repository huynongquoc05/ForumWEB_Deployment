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
        

HPA: 4 → 10 replicas (trigger: CPU avg > 150m)
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
│   └── patch.json
│
├── kiem_thu_dot_bien.js            # k6 load test script
└── .env.example
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

## Load test
 
> ⚠️ Thực hiện trên môi trường kind (local). Trên cluster thật hiệu năng sẽ khác tùy cấu hình node.
 
Script `kiem_thu_dot_bien.js` dùng k6, tăng dần lên 300 VUs qua 4 stages. Mỗi VU thực hiện GET `/login` → parse CSRF token → POST đăng nhập. Bước lấy CSRF token là bắt buộc vì Flask bật CSRF protection — request thiếu token bị từ chối ngay.
 
**Quan sát HPA trong quá trình test:**
 
Idle bình thường mỗi pod chỉ dùng ~1m CPU. Khi k6 bắt đầu bắn tải, CPU trung bình tăng lên 402% rồi 683% — HPA scale từ 4 → 7 → 10 pods. `stabilizationWindowSeconds: 0` cho scale up nên pod mới được tạo gần như ngay lập tức, không chờ.
 
Sau khi k6 ngừng, CPU rớt về thấp nhưng HPA giữ nguyên replica thêm 60s (window scale down) trước khi thu hồi pod thừa — tránh trường hợp traffic chỉ giảm tạm thời mà đã vội scale down rồi lại phải scale up lại.
 
![HPA scale](https://github.com/user-attachments/assets/72016497-2b21-4f60-8cc5-503fa2afc415)
![HPA scale](https://github.com/user-attachments/assets/145a05fa-bd2e-4439-b022-c76e48a3956f)
 
```
http_req_duration: avg=576ms  p(90)=1.53s  p(95)=2.3s
http_req_failed:   0.00%  (1 / 28763 requests)
```