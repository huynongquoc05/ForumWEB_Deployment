

## 📌 Mục lục
- [1. Tổng quan về dự án ForumWeb](#1-tổng-quan-về-dự-án-forumweb---devops--deployment)
- [2. 🚀 Quick Start (Khởi động nhanh)](#2--quick-start-khởi-động-nhanh)
- [3. Triển khai với Docker Compose](#3-triển-khai-với-docker-compose)
- [4. Triển khai với Kubernetes (K8s)](#4-triển-khai-với-kubernetes-k8s)
- [5. Kiểm thử chịu tải và phản ứng của HPA](#5-kiểm-thử-chịu-tải-và-phản-ứng-của-hpa)


<br>

# 1. Tổng quan về dự án ForumWeb - Deployment 
Repo này chứa phần application và toàn bộ cấu hình deploy cho project ForumWeb. Ứng dụng chính là một forum viết bằng Flask, còn phần trọng tâm của repo nằm ở việc containerize service, setup CI/CD, chạy multi-container bằng Docker Compose và triển khai thử nghiệm trên Kubernetes.
<img width="1528" height="839" alt="image" src="https://github.com/user-attachments/assets/878430d5-df7d-4027-ad06-913943a7747d" />

<br><br><br>
# 2. 🚀 Quick Start (Khởi động nhanh)

> ⚠️ **LƯU Ý QUAN TRỌNG:** Trước khi thực hiện bất kỳ lệnh khởi chạy nào bên dưới, bạn **bắt buộc** phải tạo và cấu hình đầy đủ các thông tin trong file `.env` ở thư mục gốc để hệ thống có thể inject cấu hình vào các container thành công. Chi tiết các biến vui lòng xem tại mục [Environment Variables](#environment-variables).

Sau khi đã chuẩn bị xong file `.env`, bạn có thể lựa chọn một trong hai phương thức triển khai tự động dưới đây tùy theo môi trường thử nghiệm:

### Phương án 1: Triển khai nhanh với Docker Compose (Dev/Test)
Môi trường này sẽ tự động khởi chạy 2 stack độc lập bao gồm các dịch vụ lõi (Nginx, Flask, SQL Server, Redis) và hệ thống giám sát (cAdvisor, Prometheus, Grafana, Portainer, Dozzle).
```bash
chmod +x Docker/deploy_docker_compose.sh
./Docker/deploy_docker_compose.sh

```

### Phương án 2: Triển khai toàn diện trên Kubernetes Cluster (Local với kind)

Kịch bản này sẽ tự động thiết lập một cluster local, cấu hình PVC cho cơ sở dữ liệu, khởi tạo Ingress Controller, cài đặt Metrics Server, thiết lập cơ chế tự động co giãn Horizontal Pod Autoscaler (HPA) và deploy trọn bộ kube-prometheus-stack qua Helm.

```bash
chmod +x K8S/Deploy_k8s.sh
./K8S/Deploy_k8s.sh

```

---

## Tech Stack

| Category | Tools |
| --- | --- |
| Backend | Flask, Gunicorn |
| Database | SQL Server 2019 |
| Cache | Redis |
| Reverse Proxy | Nginx |
| Containerization | Docker, Docker Compose |
| Orchestration | Kubernetes (kind) |
| Monitoring | Prometheus, Grafana |
| CI/CD | GitHub Actions |
| Load Testing | k6 |

---

## Environment Variables

Project sử dụng file `.env` để inject config cho container.
Ví dụ mẫu cấu hình:

```env
ACCEPT_EULA=Y
MSSQL_SA_PASSWORD=YourStrongPassword123!
REDIS_HOST=redis
DB_SERVER=sqlserver
DB_NAME=ForumWEB
DB_USER=sa
DB_PASSWORD=YourStrongPassword123!
FLASK_SECRET_KEY=supersecretkeyandhardtoguess

```


<br><br><br>

# 3. Triển khai với Docker Compose
Chạy nhanh hệ thống:
```bash
bash Docker/deploy_docker_compose.sh
```
hoặc
```bash
chmod +x Docker/deploy_docker_compose.sh
./Docker/deploy_docker_compose.sh
```

Môi trường dev/test được triển khai bằng Docker Compose, tách biệt thành hai stack độc lập: **App Stack** và **Monitoring Stack**.

## a) Multi-stage Dockerfile

Sử dụng multi-stage build để giải quyết vấn đề compile `pyodbc` và Microsoft ODBC Driver.

- **Stage 1 (builder)**: Dựa trên `python:3.12-slim`, cài `gcc`, `g++`, `unixodbc-dev` và các build dependencies. Toàn bộ Python packages được cài vào virtual environment tại `/opt/venv`.
- **Stage 2 (runtime)**: Dựa trên `python:3.12-slim`, cài `msodbcsql18` driver. Copy `/opt/venv` từ builder stage sang.
- **Kết quả**: Image production không chứa compiler toolchain, giảm đáng kể kích thước và attack surface. Application chạy dưới Gunicorn với worker class `gthread`.

## b) App Stack (`docker-compose.yaml`)

Stack gồm 4 services: `nginx`, `web`, `sqlserver`, `redis`.

**Network design:**
- Hai network riêng biệt: `frontend_network` và `backend_network`.
- `nginx` chỉ attach `frontend_network`.
- `web` attach cả hai network (làm bridge).
- `sqlserver` và `redis` chỉ attach `backend_network`.

**Traffic flow:**
`Client` 
  ➔ `[Nginx]` *(frontend_network)* ➔ `[Flask App]` *(frontend_network & backend_network)* ➔ `[SQL Server / Redis]` *(backend_network)*


**Chi tiết services:**
- **Nginx**: Serve static files (`/static/`) trực tiếp, proxy dynamic requests đến Flask. Chỉ expose port 80.
- **Web (Flask)**: Chạy Gunicorn, không expose port ra host.
- **SQL Server**: Healthcheck sử dụng `sqlcmd` với interval 10s để đảm bảo DB sẵn sàng (startup time thường 20-30s).
- **Redis**: Dùng làm cache layer.

## c) Monitoring Stack (`monitoring-compose.yaml`)
cAdvisor + Prometheus + Grafana + Portainer + Dozzle.

## d) Deployment Automation (`deploy_docker_compose.sh`)

Script thực hiện các bước sau:
1. Tạo các Docker networks nếu chưa tồn tại (`frontend_network`, `backend_network`, `monitoring_network`).
2. Load biến môi trường từ `.env`.
3. Khởi động App Stack và Monitoring Stack.
4. Chờ 30s cho SQL Server khởi động.
5. Thực thi `ForumWEB.sql` vào database qua `sqlcmd` trong container để đổ dữ liệu mẫu.

<img width="1057" height="845" alt="Screenshot 2026-05-26 160916" src="https://github.com/user-attachments/assets/f2637461-768f-440e-89af-3cd7a81bfd20" />

<br><br><br>
# 4. Triển khai với Kubernetes - K8s
Chạy nhanh hệ thống:
```bash
bash K8S/Deploy_k8s.sh
```
hoặc
```bash
chmod +x K8S/Deploy_forum_app_stacks_k8s.yaml
./K8S/Deploy_k8s.sh
```

## a) Công cụ K8s Local: kind
Để chạy và test cụm K8s ở môi trường local, project sử dụng `kind` (Kubernetes IN Docker). Lý do chọn `kind` là tốc độ khởi tạo cluster nhanh, ít tốn tài nguyên hệ thống và hỗ trợ test đầy đủ các thành phần như Ingress, HPA, PVC mà không cần config quá phức tạp.

## b) Kiến trúc K8s
Cấu hình manifest nằm trong file `K8S/Deploy_forum_app_stacks_k8s.yaml`. Các thành phần chính bao gồm:
* **ConfigMap & Secret:** Biến môi trường được load từ file `.env` vào Secret. File `ForumWEB.sql` được load qua ConfigMap để mount thẳng vào thư mục gốc của container SQL Server.
* **PVC (PersistentVolumeClaim):** Cấp phát 1Gi lưu trữ cho SQL Server (`/var/opt/mssql`). Việc này giữ cho database không bị mất dữ liệu khi Pod bị xóa hoặc restart.
* **Deployment & Service:** Tách biệt 3 service (`flask-forum`, `sqlserver`, `redis`). Riêng Flask app được set cứng resource requests/limits để cấp phát RAM và CPU hợp lý, tránh hiện tượng OOM (Out Of Memory).
* **Ingress:** Cấu hình `ingress-nginx` định tuyến traffic từ domain `localhost` vào service của ứng dụng web.

## c) Cấu hình Autoscaling (HPA)
Web app được thiết lập Horizontal Pod Autoscaler (HPA) dao động từ 4 đến 10 replicas. Metric tính toán dựa vào CPU: khi CPU trung bình chạm mốc 150m, HPA sẽ scale up ngay lập tức (`stabilizationWindowSeconds: 0`) để chống sập server. Khi hết tải, hệ thống đợi 60s trước khi thu hồi các pod thừa.
```yaml
---
#Khai báo hpa cho deployment flask-forum
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: flask-forum-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: flask-forum
  minReplicas: 4
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 150  # Kích hoạt đẻ Pod khi CPU trung bình chạm mốc 150m

  behavior:
    scaleDown:
      stabilizationWindowSeconds: 60 # 1 phút sau khi k6 ngừng bắn (CPU rớt về 1m), HPA sẽ hành động
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15          # Trảm sạch Pod dư thừa nhanh chóng
    scaleUp:
      stabilizationWindowSeconds: 0  # Đẻ ngay lập tức khi CPU vọt lên để cứu server
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
```

Để HPA hoạt động, cluster cần lấy được metric tài nguyên thông qua `metrics-server`. Quá trình này được tự động hóa trong file `Deploy_k8s.sh` bằng lệnh:
```bash
kubectl apply -f [https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml](https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml)
kubectl patch deployment metrics-server -n kube-system --type=json --patch-file ../patch.json
```

## d) Giám sát trên K8s (Prometheus Stack & Ingress)
Hệ thống dùng Helm để triển khai trọn bộ kube-prometheus-stack (bao gồm Prometheus, Grafana, Alertmanager) qua lệnh:
```bash
helm install monitoring prometheus-community/kube-prometheus-stack --timeout 15m
```
Để truy cập vào các dashboard giám sát này, file monitoring-ingress-k8s.yaml định nghĩa thêm 3 Ingress rule map cổng ra bên ngoài.

## e) Hướng dẫn chạy Script tự động (Deploy_k8s.sh)
Toàn bộ quá trình triển khai K8s từ con số không được gom vào một script duy nhất. Flow của kịch bản bao gồm:
Check và khởi tạo kind cluster.

Xóa (nếu có) và tạo lại ConfigMap, Secret.

Apply file deployment chung (Deploy_forum_app_stacks_k8s.yaml).

Wait cho đến khi tất cả Pod chuyển sang trạng thái Ready.

Gọi kubectl exec chui vào pod SQL Server và chạy lệnh sqlcmd nạp dữ liệu khởi tạo.

Cài đặt Ingress Controller, Metrics Server và bộ giám sát Helm.

**Cách khởi chạy:**
```bash
bash K8S/Deploy_k8s.sh
```
Cấu hình truy cập:
Mở file hosts của hệ điều hành (ví dụ: /etc/hosts trên Linux/Mac hoặc C:\Windows\System32\drivers\etc\hosts trên Windows) và thêm dòng sau để phân giải tên miền:
```Plaintext
127.0.0.1    localhost prometheus.local grafana.local alertmanager.local
```
Sau đó truy cập:
Web App: http://localhost
Prometheus: http://prometheus.local
Grafana: http://grafana.local

<br><br><br>

# 5. Kiểm thử chịu tải và phản ứng của HPA

Phần này dùng để kiểm tra cách cluster xử lý khi traffic tăng đột biến, đồng thời quan sát phản ứng của HPA trong cả hai chiều scale up và scale down.

## a) Kịch bản kiểm thử với k6

Load test được thực hiện bằng `k6` với file `kiem_thu_dot_bien.js`.

Mục tiêu của kịch bản là tăng dần số lượng người dùng ảo lên mức cao trong thời gian ngắn, thay vì bơm tải đột ngột ngay từ đầu.

Cấu hình chính:

```js
export const options = {
  stages: [
    { duration: '30s', target: 75 },
    { duration: '1m', target: 300 },
    { duration: '30s', target: 300 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['avg<5000'],
  },
};
```

Luồng xử lý của mỗi VU:

1. Gửi request `GET` tới trang `/login`
2. Parse HTML để lấy `csrf_token`
3. Gửi request `POST` đăng nhập kèm token

Bước lấy `csrf_token` là cần thiết vì Flask đang bật cơ chế bảo vệ CSRF, nên request thiếu token sẽ bị từ chối.

---

## b) Cấu hình autoscaling với HPA

Deployment của Flask app được gắn `resource requests/limits` để HPA có dữ liệu theo dõi.

Thông số chính:

* `minReplicas`: 4
* `maxReplicas`: 10
* target CPU: `150m`

Khi CPU trung bình của các pod vượt ngưỡng này, HPA bắt đầu tăng số lượng replica để chia tải.

### Hành vi scale up

Rule `scaleUp` được cấu hình với:

```yaml
stabilizationWindowSeconds: 0
```

Điều này có nghĩa là khi CPU tăng vượt ngưỡng, HPA phản ứng ngay thay vì chờ thêm một khoảng ổn định.

Trong thực tế, khi chạy k6, HPA tăng từ 4 pod lên 7 pod, rồi tiếp tục lên mức tối đa 10 pod.

### Hành vi scale down

Rule `scaleDown` được giữ với window 60 giây.

Mục đích là tránh tình trạng scale xuống quá sớm khi traffic chỉ vừa giảm tạm thời. Nếu hạ replica quá nhanh, hệ thống dễ bị dao động liên tục giữa tăng và giảm pod.

---

## c) Quá trình scale up và scale down của HPA khi tải cao
<img width="1012" height="190" alt="image" src="https://github.com/user-attachments/assets/72016497-2b21-4f60-8cc5-503fa2afc415" />

Khi hệ thống ở trạng thái bình thường, mỗi Flask pod chỉ sử dụng khoảng `1m CPU` và hơn `120Mi RAM`
<br>
Sau khi chạy kịch bản k6 với mức tải tăng dần lên 300 virtual users, CPU usage bắt đầu tăng nhanh. HPA theo dõi giá trị CPU trung bình của deployment và so sánh với target 150% đã cấu hình trước đó.
<br>
<img width="1097" height="604" alt="image" src="https://github.com/user-attachments/assets/145a05fa-bd2e-4439-b022-c76e48a3956f" />

Ban đầu dù CPU đã vượt ngưỡng 150%, HPA vẫn giữ nguyên 4 replicas trong một khoảng ngắn để đánh giá xu hướng tải thay vì scale ngay lập tức. Khi mức sử dụng CPU tiếp tục tăng mạnh lên 402% rồi 683%, cluster bắt đầu scale từ 4 -> 7 -> 10 pods.

Sau khi replica tăng lên mức tối đa, CPU usage giảm dần do request được phân phối lại sang các pod mới tạo.

Sau khi traffic giảm, CPU usage hạ dần về mức rất thấp nhưng HPA chưa scale down ngay lập tức. Replica vẫn được giữ ở mức cao thêm một khoảng ngắn trước khi giảm về 4 pod ban đầu

<details>
<summary>📊 <b>Click để xem chi tiết Output kết quả kiểm thử chịu tải (k6 load test)</b></summary>

```text
(.venv) PS C:\Users\VICTUS\PycharmProjects\ForumWeb> k6 run .\kiem_thu_dot_bien.js                                                                             

          /\      Grafana   /‾‾/
     /\  /  \     |\  __   /  /
    /  \/    \    | |/ /  /   ‾‾\
   /          \   |   (  |  (‾)  |
  / __________ \  |_|\_\  \_____/


     execution: local
        script: .\kiem_thu_dot_bien.js
        output: -

     scenarios: (100.00%) 1 scenario, 300 max VUs, 3m0s max duration (incl. graceful stop):
              * default: Up to 300 looping VUs for 2m30s over 4 stages (gracefulRampDown: 30s, gracefulStop: 30s)


  █ THRESHOLDS

    http_req_duration
    ✓ 'avg<5000' avg=576.53ms

    http_req_failed
    ✓ 'rate<0.01' rate=0.00%


  █ TOTAL RESULTS

    checks_total.......: 19176  127.664042/s
    checks_succeeded...: 99.99% 19175 out of 19176
    checks_failed......: 0.00%  1 out of 19176

    ✓ Trang GET tải thành công và có CSRF Token
    ✗ Đăng nhập thành công (Trả về 302 hoặc 200)
      ↳  99% — ✓ 9587 / ✗ 1

    HTTP
    http_req_duration..............: avg=576.53ms min=1.15ms med=227.75ms max=7.78s  p(90)=1.53s p(95)=2.3s
      { expected_response:true }...: avg=576.55ms min=1.15ms med=227.8ms  max=7.78s  p(90)=1.53s p(95)=2.3s
    http_req_failed................: 0.00%  1 out of 28763
    http_reqs......................: 28763  191.489406/s

    EXECUTION
    iteration_duration.............: avg=2.73s    min=1.01s  med=2.18s    max=13.31s p(90)=5.11s p(95)=6.34s
    iterations.....................: 9588   63.832021/s
    vus............................: 11     min=3          max=300
    vus_max........................: 300    min=300        max=300

    NETWORK
    data_received..................: 264 MB 1.8 MB/s
    data_sent......................: 7.3 MB 49 kB/s
                                                                                                                                                                    
running (2m30.2s), 000/300 VUs, 9588 complete and 0 interrupted iterations                                                                                               
default ✓ [======================================] 000/300 VUs  2m30s
                                                                                                                                                                    
running (2m30.2s), 000/300 VUs, 9588 complete and 0 interrupted iterations                                                                                               
default ✓ [======================================] 000/300 VUs  2m30s     
```
