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

# 1. Kiểm tra và Khởi tạo/Bật Cluster
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
echo -e "${YELLOW}▶ Running:${NC} ${GREEN}Kiểm tra & Khởi tạo Kind Cluster${NC}"
echo -e "  Kiểm tra cluster tồn tại, bật nếu đang tắt"
echo -e "${CYAN}----------------------------------------------------------------------${NC}"
if kind get clusters | grep -q "^kind$"; then
    echo -e "${GREEN}✓ Cluster 'kind' đã tồn tại.${NC}"
    if [ "$(docker inspect -f '{{.State.Running}}' kind-control-plane 2>/dev/null)" == "true" ]; then
        echo -e "${GREEN}✓ Cluster đang hoạt động.${NC}"
    else
        echo -e "${YELLOW}⚠ Cluster đang tắt. Đang bật lại...${NC}"
        docker start kind-control-plane
        sleep 15
        echo -e "${YELLOW}⚠ Chờ ingress-nginx sẵn sàng sau khi bật lại cluster...${NC}"
        kubectl wait \
            --namespace ingress-nginx \
            --for=condition=ready pod \
            --selector=app.kubernetes.io/component=controller \
            --timeout=3m 2>/dev/null || true
    fi
else
    echo -e "${YELLOW}⚠ Cluster chưa tồn tại. Đang tạo mới...${NC}"
    kind create cluster --config kind_conf.yaml
    sleep 5
fi



# 2. Tạo ConfigMap & Secret

echo -e "${YELLOW}▶ Running:${NC} ${GREEN}kubectl delete/create configmap & secret${NC}"
echo -e "  Tạo ConfigMap và Secret cho Database"

run kubectl delete configmap forum-sql-script --ignore-not-found
run kubectl create configmap forum-sql-script --from-file=../ForumWEB.sql
run kubectl delete secret forum-env-secret --ignore-not-found
run kubectl create secret generic forum-env-secret --from-env-file=../.env

# 3. Triển khai ứng dụng
run_desc "Triển khai Flask, Redis, SQL Server" \
    kubectl apply -f Deploy_forum_app_stacks_k8s.yaml

# 4. Chờ tất cả Pod Ready
run_desc "Chờ tất cả Pod Running" \
    kubectl wait --for=condition=ready pod --all --timeout=15m

# 5. Đổ dữ liệu vào SQL Server
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
echo -e "${YELLOW}▶ Running:${NC} ${GREEN}kubectl exec deployment/sqlserver -- sqlcmd -i /ForumWEB.sql${NC}"
echo -e "  Đổ dữ liệu mồi vào SQL Server"
echo -e "${CYAN}----------------------------------------------------------------------${NC}"
kubectl exec -it deployment/sqlserver -- \
    sh -c '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$DB_PASSWORD" -C -i /ForumWEB.sql'

# 6. Cài Ingress Nginx
run_desc "Cài đặt Ingress Nginx Controller" \
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

echo "Đang chờ Ingress Controller sẵn sàng..."
run kubectl wait \
    --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=controller \
    --timeout=5m

# 7. Cài Metrics Server
run_desc "Cài Metrics Server" \
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

sleep 3

run_desc "Patch Metrics Server cho phép insecure TLS" \
    kubectl patch deployment metrics-server -n kube-system --type=json --patch-file ../patch.json

# 8. Cài Kube-Prometheus-Stack
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
echo -e "${YELLOW}▶ Running:${NC} ${GREEN}helm install monitoring prometheus-community/kube-prometheus-stack --timeout 15m${NC}"
echo -e "  Cài đặt Prometheus + Grafana + Alertmanager"
echo -e "${CYAN}----------------------------------------------------------------------${NC}"
helm install monitoring prometheus-community/kube-prometheus-stack --timeout 15m \
    || echo -e "${YELLOW}⚠ Hệ thống giám sát đã được cài đặt, bỏ qua.${NC}"

# 9. Triển khai Ingress cho Monitoring
run_desc "Triển khai Ingress cho Monitoring" \
    kubectl apply -f monitoring-ingress-k8s.yaml

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}          ✅ TRIỂN KHAI HOÀN TẤT THÀNH CÔNG!${NC}"
echo -e "${GREEN}======================================================================${NC}\n"

echo -e "${YELLOW}📌 HƯỚNG DẪN TRUY CẬP:${NC}"
echo -e "Hãy thêm vào file hosts:"
echo -e "${GREEN}127.0.0.1    localhost prometheus.local grafana.local alertmanager.local${NC}\n"

echo -e "Truy cập qua trình duyệt:"
echo -e "  🌐 ${CYAN}Forum Web App:${NC}     http://localhost"
echo -e "  📈 ${CYAN}Prometheus:${NC}        http://prometheus.local"
echo -e "  📊 ${CYAN}Grafana:${NC}           http://grafana.local"
echo -e "  🚨 ${CYAN}Alertmanager:${NC}      http://alertmanager.local"