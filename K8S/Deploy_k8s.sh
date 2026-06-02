#!/bin/bash
set -e
cd "$(dirname "$0")"

# --- ĐỊNH NGHĨA MÀU SẮC ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

run() {
    echo -e "${YELLOW}▶ Running:${NC} ${GREEN}$*${NC}"
    "$@"
}

run_desc() {
    local desc="$1"
    shift
    echo -e "${YELLOW}▶ Running:${NC} ${GREEN}$*${NC}"
    echo -e "  ${desc}"
    "$@"
}

# 1. Kiểm tra Kết nối Cluster (Thay thế cho phần tạo Kind)
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
echo -e "${YELLOW}▶ Running:${NC} ${GREEN}Kiểm tra kết nối tới Kubeadm Cluster${NC}"
echo -e "${CYAN}----------------------------------------------------------------------${NC}"
if kubectl get nodes >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Đã kết nối thành công tới Cluster K8s.${NC}"
    kubectl get nodes
else
    echo -e "${YELLOW}⚠ Lỗi: Không thể kết nối tới Cluster. Vui lòng kiểm tra file kubeconfig (~/.kube/config) của bạn.${NC}"
    exit 1
fi

# 2. Tạo ConfigMap & Secret
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
run_desc "Tạo ConfigMap và Secret cho Database" \
    kubectl delete configmap forum-sql-script --ignore-not-found
run kubectl create configmap forum-sql-script --from-file=../ForumWEB.sql
run kubectl delete secret forum-env-secret --ignore-not-found
run kubectl create secret generic forum-env-secret --from-env-file=../.env

# 3. Triển khai ứng dụng
run_desc "Triển khai Flask, Redis, SQL Server" \
    kubectl apply -f Deploy_forum_app_stacks_k8s.yaml

# 4. Chờ tất cả Pod Ready
run_desc "Chờ tất cả Pod Running (có thể mất vài phút để pull image mới)" \
    kubectl wait --for=condition=ready pod --all --timeout=15m

# 5. Cài Ingress Nginx (Dùng bản Bare-metal thay vì Kind)
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
run_desc "Cài đặt Ingress Nginx Controller cho Bare-metal" \
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/baremetal/deploy.yaml

echo "Đang chờ Ingress Controller sẵn sàng..."
run kubectl wait \
    --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=controller \
    --timeout=5m

# 6. Cài Metrics Server
run_desc "Cài Metrics Server" \
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

sleep 3

run_desc "Patch Metrics Server cho phép insecure TLS" \
    kubectl patch deployment metrics-server -n kube-system --type=json --patch-file ../patch.json

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}          ✅ TRIỂN KHAI HOÀN TẤT THÀNH CÔNG LÊN KUBEADM!${NC}"
echo -e "${GREEN}======================================================================${NC}\n"

echo -e "${YELLOW}📌 HƯỚNG DẪN TRUY CẬP (MÔI TRƯỜNG CLOUD):${NC}"
echo -e "Trong môi trường Kubeadm/EC2, Ingress Nginx Bare-metal sẽ sử dụng NodePort."
echo -e "Hãy kiểm tra Port của Ingress Nginx bằng lệnh:"
echo -e "${GREEN}kubectl get svc ingress-nginx-controller -n ingress-nginx${NC}\n"
echo -e "Sau đó, thêm vào file hosts trên máy cá nhân của bạn IP PUBLIC của một trong các Worker Node:"
echo -e "${GREEN}<IP_PUBLIC_CỦA_WORKER_NODE>   forum.local prometheus.local grafana.local alertmanager.local${NC}\n"
echo -e "Truy cập qua trình duyệt (Kèm theo NodePort, ví dụ :30080):"
echo -e "  🌐 ${CYAN}Forum Web App:${NC}     http://forum.local:<NodePort>"
echo -e "  📈 ${CYAN}Prometheus:${NC}        http://prometheus.local:<NodePort>"
echo -e "  📊 ${CYAN}Grafana:${NC}           http://grafana.local:<NodePort>"