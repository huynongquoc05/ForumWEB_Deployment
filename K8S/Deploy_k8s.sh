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

# 4. Chờ các Pod ứng dụng cụ thể Ready (Sửa lỗi treo dứt điểm)
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
echo -e "${YELLOW}⏳ Đang chờ các Pod của ứng dụng khởi động thành công...${NC}"
# Chỉ chờ các pod có nhãn app thuộc dự án, không dùng --all để tránh bị kẹt bởi cụm monitoring
kubectl wait --for=condition=ready pod -l app=sqlserver --timeout=5m
kubectl wait --for=condition=ready pod -l app=redis --timeout=5m
kubectl wait --for=condition=ready pod -l app=flask-forum --timeout=5m

# 5. Đổ dữ liệu vào SQL Server
echo -e "\n${CYAN}----------------------------------------------------------------------${NC}"
echo -e "${YELLOW}▶ Running:${NC} ${GREEN}Tự động thực thi đổ dữ liệu ForumWEB.sql vào CSDL nội bộ...${NC}"
echo -e "${CYAN}----------------------------------------------------------------------${NC}"
# Đợi thêm 5s đảm bảo SQL Server Engine bên trong container đã sẵn sàng nhận kết nối
sleep 5

# Lấy chính xác tên Pod SQL Server đang chạy thực tế
SQL_POD_NAME=$(kubectl get pods -l app=sqlserver -o jsonpath="{.items[0].metadata.name}")

# Bốc biến mật khẩu từ file .env nội bộ của bạn để chạy lệnh mồi dữ liệu
DB_PASS=$(grep DB_PASSWORD ../.env | cut -d '=' -f2)

# Vì bản chất Pod SQL Server chứa v18, ta dùng đúng đường dẫn v18 và cờ -C
kubectl exec -i sqlserver-6989cf9f4d-zk98c -- /opt/mssql-tools18/bin/sqlcmd \
    -S localhost -U sa -P "$DB_PASS" -C -i /var/opt/mssql/scripts/ForumWEB.sql || echo -e "${YELLOW}⚠ Dữ liệu có thể đã tồn tại từ trước, bỏ qua mồi.${NC}"
echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}          ✅ TRIỂN KHAI ỨNG DỤNG HOÀN TẤT THÀNH CÔNG!${NC}"
echo -e "${GREEN}======================================================================${NC}\n"