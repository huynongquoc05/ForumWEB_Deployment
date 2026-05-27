#!/bin/bash
# --- ĐỊNH NGHĨA MÀU SẮC ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

set -e
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

# --- FIXED: Tự động di chuyển thư mục làm việc vào nơi chứa file bash script này ---
cd "$(dirname "$0")"

run() {
    echo -e "${YELLOW}▶ $*${NC}"
    "$@"
}

echo "Khởi tạo mạng ảo cho Docker..."
run docker network create backend_network || true
run docker network create frontend_network || true
run docker network create monitoring_network || true

run docker compose --env-file ../.env -f docker-compose.yaml up -d --scale web=2
run docker compose -f monitoring-compose.yaml up -d

echo -e "${CYAN}⏳ Đang chờ SQL Server đạt trạng thái Healthy...${NC}"

until [ "$(docker inspect --format='{{.State.Health.Status}}' forum_sql_server)" = "healthy" ]; do
    echo -e "${YELLOW}⏳ SQL Server chưa ready, đợi 5s...${NC}"
    sleep 5
done

echo -e "${YELLOW}▶ docker exec forum_sql_server /bin/bash -c '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"\$MSSQL_SA_PASSWORD\" -C -i /ForumWEB.sql'${NC}"
docker exec forum_sql_server \
    /bin/bash -c '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -i /ForumWEB.sql'

echo -e "${GREEN}✅ Hệ thống đã sẵn sàng 100%!${NC}"

echo -e "  🌐 ${CYAN}Forum Web App:${NC}     http://localhost"
echo -e "  📈 ${CYAN}Prometheus:${NC}        http://localhost:9090/"
echo -e "  📊 ${CYAN}Grafana:${NC}           http://localhost:3000/"