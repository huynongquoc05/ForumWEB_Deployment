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

# 1. Kiểm tra kết nối tới Kubeadm Cluster
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
echo -e "${YELLOW}▶ Running:${NC} ${GREEN}Kiểm tra kết nối Cluster${NC}"
echo -e "  Đảm bảo kubectl đã kết nối tới cụm Kubeadm"
echo -e "${CYAN}----------------------------------------------------------------------${NC}"
if kubectl cluster-info > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Đã kết nối thành công tới cluster.${NC}"
else
    echo -e "${YELLOW}⚠ Không thể kết nối tới cluster. Vui lòng kiểm tra lại cấu hình Kubeconfig!${NC}"
    exit 1
fi

# 2. Tạo ConfigMap & Secret
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
echo -e "${YELLOW}▶ Running:${NC} ${GREEN}kubectl delete/create configmap & secret${NC}"
echo -e "  Tạo ConfigMap và Secret cho Database"
echo -e "${CYAN}----------------------------------------------------------------------${NC}"
run kubectl delete configmap forum-sql-script --ignore-not-found
run kubectl create configmap forum-sql-script --from-file=../ForumWEB.sql
run kubectl delete secret forum-env-secret --ignore-not-found
run kubectl create secret generic forum-env-secret --from-env-file=../.env

# 3. Triển khai ứng dụng
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
run_desc "Triển khai Flask, Redis, SQL Server" \
    kubectl apply -f Deploy_forum_app_stacks_k8s.yaml

# 4. Chờ tất cả Pod Ready
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
run_desc "Chờ tất cả Pod Running" \
    kubectl wait --for=condition=ready pod --all --timeout=15m

# 5. Đổ dữ liệu vào SQL Server
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
echo -e "${YELLOW}▶ Running:${NC} ${GREEN}kubectl exec deployment/sqlserver -- sqlcmd -i /ForumWEB.sql${NC}"
echo -e "  Đổ dữ liệu mồi vào SQL Server"
echo -e "${CYAN}----------------------------------------------------------------------${NC}"
# Đợi thêm 3-5s đảm bảo process SQL bên trong Pod đã thực sự nhận port
sleep 5
kubectl exec -it deployment/sqlserver -- \
    sh -c '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$DB_PASSWORD" -C -i /ForumWEB.sql'

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}          ✅ TRIỂN KHAI ỨNG DỤNG HOÀN TẤT THÀNH CÔNG!${NC}"
echo -e "${GREEN}======================================================================${NC}\n"