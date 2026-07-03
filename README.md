# Forum Web Deployment

Deploy một ứng dụng forum Flask lên Kubernetes, với đầy đủ autoscaling, monitoring và CI/CD. Repo này cover toàn bộ phần infrastructure và deployment — từ Docker Compose cho dev đến K8s cho production-like environment.

![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white) ![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?logo=kubernetes&logoColor=white) ![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white) ![Grafana](https://img.shields.io/badge/Grafana-F46800?logo=grafana&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

<img width="1528" height="839" alt="image" src="https://github.com/user-attachments/assets/878430d5-df7d-4027-ad06-913943a7747d" />

---

## 1. Kiến trúc
### Kubernetes
```mermaid
graph TD
    classDef client fill:#f25f4c,stroke:#7a271e,stroke-width:2px,color:#fff,font-weight:bold;
    classDef ingress fill:#2cb67d,stroke:#124a32,stroke-width:2px,color:#fff,font-weight:bold;
    classDef app fill:#3da9fc,stroke:#094067,stroke-width:2px,color:#fff,font-weight:bold;
    classDef svc fill:#33272a,stroke:#594a4e,stroke-width:2px,color:#fffffe;
    classDef monitor fill:#7f5af0,stroke:#3b237a,stroke-width:2px,color:#fffffe,font-weight:bold;
    classDef hpa fill:#ff8906,stroke:#7a3f00,stroke-width:2px,color:#fff,font-weight:bold;
    classDef note fill:#edf2f7,stroke:#4a5568,stroke-width:1px,color:#2d3748,font-size:12px,font-style:italic;

    Client["Client / Browser"]:::client
    Ingress["Nginx Ingress<br/>HTTP / HTTPS"]:::ingress

    Client -->|HTTP request| Ingress

    subgraph Apps["Application / Monitoring"]
        Flask["flask-forum Deployment<br/>8 → 15 replicas"]:::app
        Grafana["Grafana"]:::monitor
        Prometheus["Prometheus"]:::monitor
    end

    Ingress --> Flask
    Ingress --> Grafana
    Ingress --> Prometheus

    subgraph Internal["Internal Services"]
        SQL["sqlserver svc"]:::svc
        Redis["redis svc"]:::svc
    end

    Flask -->|read / write| SQL
    SQL -.->|response| Flask

    Flask -->|get / set| Redis
    Redis -.->|response| Flask

    Grafana -->|query metrics| Prometheus
    Prometheus -->|scrape metrics| Flask

    Metrics["Metrics Server / Metrics API"]:::note
    HPA["HPA<br/>CPU avg > 80m"]:::hpa

    HPA -->|read CPU metrics| Metrics
    Metrics -->|collect pod metrics| Flask
    HPA -.->|scale replicas| Flask

    style Apps fill:#f8f9fa,stroke:#b8c1ec,stroke-width:2px,stroke-dasharray: 5 5;
    style Internal fill:#f8f9fa,stroke:#b8c1ec,stroke-width:2px,stroke-dasharray: 5 5;
```
 
```
HPA: 8 → 15 replicas (trigger: CPU avg > 80m)
```


### Docker Compose:
```mermaid
graph TD
    %% =======================
    %% Style
    %% =======================
    classDef client fill:#f25f4c,stroke:#7a271e,stroke-width:2px,color:#fff,font-weight:bold;
    classDef proxy fill:#2cb67d,stroke:#124a32,stroke-width:2px,color:#fff,font-weight:bold;
    classDef app fill:#3da9fc,stroke:#094067,stroke-width:2px,color:#fff,font-weight:bold;
    classDef db fill:#33272a,stroke:#594a4e,stroke-width:2px,color:#fffffe;
    classDef network fill:#edf2f7,stroke:#4a5568,stroke-width:1px,color:#2d3748,font-style:italic;

    %% =======================
    %% Client
    %% =======================
    Client["Client / Browser"]:::client

    %% =======================
    %% Frontend Network
    %% =======================
    subgraph Frontend["frontend_network"]
        Nginx["Nginx"]:::proxy
        Web["flask-forum"]:::app
    end

    %% =======================
    %% Backend Network
    %% =======================
    subgraph Backend["backend_network"]
        Web2["flask-forum"]:::app
        SQL["SQL Server"]:::db
        Redis["Redis"]:::db
    end

    %% Traffic
    Client -->|HTTP / HTTPS| Nginx
    Nginx -->|reverse proxy| Web

    Web2 -->|read / write| SQL
    Web2 -->|get / set| Redis

    %% Same container on two networks
    Web -.->|"same container<br/>attached to both networks"| Web2

    %% Isolation note
    Note["SQL Server & Redis are isolated in backend_network<br/>Nginx cannot access them directly"]:::network

    SQL --- Note
    Redis --- Note

    style Frontend fill:#f8f9fa,stroke:#b8c1ec,stroke-width:2px,stroke-dasharray:5 5;
    style Backend fill:#f8f9fa,stroke:#b8c1ec,stroke-width:2px,stroke-dasharray:5 5;
```
---

## 2. Cấu trúc thư mục

```
.
├── App.py
├── Docker
│   ├── Nginx.conf
│   ├── auth_routes.py
│   ├── deploy_docker_compose.sh
│   ├── docker-compose.yaml
│   ├── monitoring-compose.yaml
│   └── prometheus.yml
├── Dockerfile
├── ForumWEB.sql
├── K6 Peformance Testing
│   ├── k61-login-route.js
│   ├── k62-homepage.js
│   └── k64-compose.js
├── K8S
│   ├── Deploy_forum_app_stacks_k8s.yaml
│   ├── Deploy_k8s.sh
│   ├── alertmanager-values.yaml
│   ├── grafana_values.yaml
│   └── k8s_allert.yaml
├── README.md
├── Các file ứng dụng
7 directories, 29 files

```

---

## 3. Điểm thiết kế đáng chú ý

 ### Docker
**Multi-stage Dockerfile**
Build stage cài compiler toolchain để compile `pyodbc`. Runtime stage chỉ copy `/opt/venv` sang — không có `gcc`, `g++` hay build deps trong image production. Giảm attack surface và image size đáng kể.

**Network isolation trong Docker Compose**
Tách `frontend_network` và `backend_network`. Nginx chỉ thấy Flask, Flask mới thấy SQL Server và Redis. Database không bao giờ expose ra ngoài.

### Kubernets
**HPA scale up tức thì, scale down chậm**
`stabilizationWindowSeconds: 0` cho scale up — pod mới tạo ngay khi CPU vượt ngưỡng, không chờ. Scale down giữ window 60s để tránh pod bị thu hồi rồi lại phải tạo lại khi traffic chỉ giảm tạm thời.
Trigger scale dựa trên CPU request trung bình > 80m (target 80% của request 100m/pod). HPA controller dùng dung sai (tolerance) mặc định 10% quanh target — nghĩa là chỉ khi CPU trung bình lệch khỏi khoảng 72m–88m thì mới kích hoạt scale, tránh việc pod bị scale liên tục (flapping) khi CPU dao động nhẹ quanh ngưỡng.

**Automation script end-to-end**
`Deploy_k8s.sh` xử lý toàn bộ: apply manifests → wait pods ready → inject SQL seed data.

**Extended Observability**

Mở rộng Prometheus stack kèm Grafana dashboards, chia theo từng lớp giám sát:

- ***Node-level dashboard***: theo dõi CPU và RAM tiêu thụ trên từng worker node (EC2 instance) — phát hiện node nào đang chịu tải cao hoặc sắp cạn tài nguyên.
- ***Container-level dashboard***: theo dõi CPU và RAM của từng container/pod riêng lẻ — giúp xác định chính xác pod nào đang ngốn tài nguyên, khác với view tổng ở cấp node.
- ***HTTP request dashboard***: theo dõi tổng số HTTP request (`http_requests_total`) theo thời gian — phản ánh lưu lượng truy cập thực tế vào hệ thống, dùng để đối chiếu với biểu đồ CPU khi có traffic spike.

Đi kèm là **4 alerting rules**, mỗi rule ứng với một tình huống vận hành cụ thể:

1. **Node failure** — cảnh báo khi một node trong cluster mất kết nối / không sẵn sàng (`NotReady`).
2. **CrashLoopBackOff** — cảnh báo khi pod liên tục crash và bị Kubernetes restart lặp lại, dấu hiệu lỗi ứng dụng hoặc cấu hình sai.
3–4. **Resource saturation** — cảnh báo khi CPU hoặc RAM (ở cấp node hoặc container) vượt ngưỡng an toàn trong một khoảng thời gian, báo hiệu nguy cơ thiếu tài nguyên trước khi pod bị OOMKilled hoặc node bị nghẽn.

Mục tiêu chung: không chỉ nhìn được **hiện trạng** (dashboard) mà còn được **chủ động cảnh báo** (alerting) trước khi sự cố ảnh hưởng đến người dùng cuối.

---

### Yêu cầu

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

### Cách chạy

#### Docker Compose 

```bash
chmod +x Docker/deploy_docker_compose.sh
./Docker/deploy_docker_compose.sh
```

#### Kubernetes

```bash
chmod +x K8S/Deploy_k8s.sh
./K8S/Deploy_k8s.sh
```


---

##  4. Performance testing
> Thực hiện trên cluster (AWS EC2, 3 worker nodes). Kết quả phản ánh hiệu năng thực tế của hạ tầng.

Script `K6 Peformance Testing/k64-compose.js` dùng k6, mô phỏng tải hỗn hợp bằng `scenarios` gồm 2 luồng chạy song song:
- **`guest_browsing`** (read-heavy): ramping-vus tăng dần lên 800 VUs, chỉ GET trang chủ `/`.
- **`user_login`** (write-heavy): ramping-vus tăng dần lên 200 VUs, mỗi VU thực hiện GET `/login` → parse CSRF token → POST đăng nhập. Bước lấy CSRF token là bắt buộc vì Flask bật CSRF protection — request thiếu token bị từ chối ngay (xem chi tiết trong file).

Mỗi request được gắn `tags: { name: ... }` (`GET_Homepage`, `GET_Login_Page`, `POST_Login_Submit`) để k6 bóc tách latency riêng theo từng endpoint, kèm threshold riêng cho từng loại:

```
scenarios: {
  guest_browsing: {
    executor: 'ramping-vus',
    stages: [
      { duration: '30s', target: 800 },
      { duration: '1m', target: 800 },
      { duration: '30s', target: 0 },
    ],
    exec: 'browsingFlow',
  },
  user_login: {
    executor: 'ramping-vus',
    stages: [
      { duration: '30s', target: 200 },
      { duration: '1m', target: 200 },
      { duration: '30s', target: 0 },
    ],
    exec: 'loginFlow',
  },
},
thresholds: {
  http_req_failed: ['rate<0.01'],
  'http_req_duration{name:GET_Homepage}': ['p(95)<1000'],
  'http_req_duration{name:GET_Login_Page}': ['p(95)<1500'],
  'http_req_duration{name:POST_Login_Submit}': ['p(95)<3000'],
},
```

```bash
k6 run k64-compose.js
```

### Kết quả tổng hợp

| Chỉ số | Giá trị |
|---|---|
| Tổng requests | 51,756 (424.2 req/s) |
| Iterations hoàn thành | 40,378 (330.9 iter/s) |
| Avg latency (chung) | 89.89ms |
| p90 latency (chung) | 96.29ms |
| p95 latency (chung) | 114.62ms |
| Max latency | 3.73s |
| Error rate | 0.00% (0/51,756) |
| Checks | 100.00% (46,067/46,067) |

### Latency theo từng endpoint

| Endpoint | Avg | p90 | p95 | Max |
|---|---|---|---|---|
| GET_Homepage | 98.41ms | 100.89ms | 122.42ms | 3.73s |
| GET_Login_Page | 56.41ms | 51.36ms | 63.91ms | 3.35s |
| POST_Login_Submit | 80.63ms | 90.04ms | 104.2ms | 3.67s |

Cả 3 threshold per-endpoint đều pass (p95 GET_Homepage < 1s, GET_Login_Page < 1.5s, POST_Login_Submit < 3s), dù max latency cá biệt vọt lên hơn 3s trong lúc HPA đang scale — không đủ để kéo p95 vượt ngưỡng.

### Quan sát HPA trong quá trình test

HPA cấu hình `min 8 / max 15` pods, target CPU 80%. Idle ban đầu CPU chỉ ~1%. Khi k6 bắt đầu bắn tải kết hợp (800 VUs browsing + 200 VUs login), CPU tăng nhanh: 35% → 127% → đỉnh 207%, HPA phản ứng scale từ 8 → 13 → 15 pods (chạm max pods cấu hình). Sau khi giữ tải ổn định, CPU hạ dần về vùng 108–125% rồi rớt nhanh khi k6 ramp-down.

Sau khi tải kết thúc, CPU về gần 1% nhưng HPA vẫn giữ nguyên 15 pods trong một khoảng thời gian (cooldown window) trước khi scale down dần 15 → 10 → 8 pods, tránh scale down non khi traffic chỉ giảm tạm thời:

```
NAME              REFERENCE                TARGETS        MINPODS   MAXPODS   REPLICAS
flask-forum-hpa   Deployment/flask-forum   cpu: 1%/80%    8         15        8
flask-forum-hpa   Deployment/flask-forum   cpu: 35%/80%   8         15        8
flask-forum-hpa   Deployment/flask-forum   cpu: 127%/80%  8         15        8
flask-forum-hpa   Deployment/flask-forum   cpu: 207%/80%  8         15        13
flask-forum-hpa   Deployment/flask-forum   cpu: 139%/80%  8         15        15
flask-forum-hpa   Deployment/flask-forum   cpu: 125%/80%  8         15        15
flask-forum-hpa   Deployment/flask-forum   cpu: 123%/80%  8         15        15
flask-forum-hpa   Deployment/flask-forum   cpu: 108%/80%  8         15        15
flask-forum-hpa   Deployment/flask-forum   cpu: 49%/80%   8         15        15
flask-forum-hpa   Deployment/flask-forum   cpu: 12%/80%   8         15        15
flask-forum-hpa   Deployment/flask-forum   cpu: 1%/80%    8         15        15
flask-forum-hpa   Deployment/flask-forum   cpu: 1%/80%    8         15        15
flask-forum-hpa   Deployment/flask-forum   cpu: 1%/80%    8         15        10
flask-forum-hpa   Deployment/flask-forum   cpu: 1%/80%    8         15        8
```

```
http_req_duration: avg=89.89ms  p(90)=96.29ms  p(95)=114.62ms  max=3.73s
http_req_failed:   0.00%  (0 / 51756 requests)
iterations:        40378  (330.9/s)
checks:            100.00% (46067 / 46067)
```

## 5. Xây dựng hệ thống monitoring
 
Dashboard `flask-forum-dashboard` được provision tự động vào Grafana qua `ConfigMap`, gắn label `grafana_dashboard: "1"` để **Grafana Sidecar** tự phát hiện và load — không cần import thủ công.

 ```kubectl apply -f grafana_values.yaml``` 
- Template variable `App_Name` — dùng chung 1 dashboard cho nhiều môi trường (`flask-forum`, `flask-forum-staging`, `flask-forum-prod`).
### Các panel theo dõi
 
| Panel | Cấp độ | Query |
|---|---|---|
| CPU node (%) | Node | `(1 - avg by (instance)(irate(node_cpu_seconds_total{mode="idle"}[5m])))*100` |
| CPU pod app (mCPU) | Pod | `sum by (pod)(rate(container_cpu_usage_seconds_total{container!='',container="${App_Name}"}[5m])*1000)` |
| RAM node (%) | Node | `sum by (instance) ((node_memory_MemTotal_bytes-node_memory_MemAvailable_bytes)/node_memory_MemTotal_bytes)*100` |
| RAM pod (MB) | Pod | `sum by (pod) (container_memory_working_set_bytes{container!='',container="${App_Name}"}/1024/1024)` |
| Request rate (req/s) | Application | `sum by (pod) (rate(flask_forum_http_requests_total{container="${App_Name}", container!="", pod=~"${App_Name}-.*"}[5m]))` |

 <img width="1482" height="811" alt="image" src="https://github.com/user-attachments/assets/68b38952-e8ab-4720-a122-8ec7e577eb29" />

Node-level lấy từ Node Exporter, pod-level lấy từ cAdvisor/kubelet, request rate lấy từ metric custom Flask expose qua `/metrics` — dùng để đối chiếu traffic với hành vi scale của HPA.
 