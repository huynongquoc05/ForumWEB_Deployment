FROM python:3.12-slim
WORKDIR /app
# 3. Cài đặt các thư viện hệ thống cần thiết cho pyodbc và các package khác
# Cài đặt công cụ và thêm kho lưu trữ của Microsoft để tải Driver SQL Server
# 3. Cài đặt các thư viện hệ thống và Driver SQL Server (Đã cập nhật chuẩn Debian 12)
RUN apt-get update && apt-get install -y curl apt-transport-https gnupg2 \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# copy file requirements.txt vào container
COPY requirements.txt .

# 4. Cài đặt các thư viện Python cần thiết
RUN pip install --no-cache-dir -r requirements.txt
# copy toàn bộ mã nguồn vào container
COPY . .


# 5. Chạy ứng dụng

# 7. Báo cho Docker biết ứng dụng sẽ chạy ở cổng 8005
EXPOSE 8005


# ==========================================
# GIAI ĐOẠN 1: XƯỞNG CHẾ TẠO (Đặt tên là "builder")
# ==========================================
FROM python:3.12-slim AS builder
WORKDIR /app

# 1. Cài đặt các công cụ "hạng nặng" để biên dịch thư viện C/C++
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ unixodbc-dev curl gnupg2

# 2. Cài driver SQL Server (để lấy mã nguồn dev cho pyodbc)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17

# 3. BÍ QUYẾT TẠO "CHIẾC HỘP ĐỰNG KIẾM": Tạo môi trường ảo (venv)
# Chúng ta sẽ cài mọi thư viện Python vào cái hộp /opt/venv này để lát nữa dễ dàng bê đi
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ==========================================
# GIAI ĐOẠN 2: CĂN PHÒNG SẠCH (Thành phẩm cuối cùng)
# ==========================================
FROM python:3.12-slim
WORKDIR /app

# 1. Chỉ cài đặt công cụ cần thiết ĐỂ CHẠY (Runtime), KHÔNG cài công cụ BIÊN DỊCH (gcc, dev)
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg2 \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* # Xóa sạch bộ nhớ tạm của apt-get

# 2. HÀNH ĐỘNG CƯỚP ĐỒ: Bê "chiếc hộp" chứa thư viện thành phẩm từ xưởng 'builder' sang đây
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 3. Copy mã nguồn của bạn vào (mã nguồn thì cực nhẹ rồi)
COPY . .

EXPOSE 8005


# 8. Lệnh khởi chạy ứng dụng
# 8. Lệnh khởi chạy ứng dụng
CMD ["gunicorn", "-b", "0.0.0.0:8005", "run:app", \
     "-w", "4", \
     "-k", "gthread", \
     "--threads", "4", \
     "--timeout", "300", \
     "--limit-request-field_size", "65536", \
     "--limit-request-line", "65536", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--capture-output", \
     "--enable-stdio-inheritance"]