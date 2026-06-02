import os
import pyodbc
from dotenv import load_dotenv

# Load file .env
load_dotenv()

connection_string = (
    f"Driver={{ODBC Driver 17 for SQL Server}};"
    f"Server={os.getenv('DB_SERVER')};"
    f"Database={os.getenv('DB_NAME')};"
    f"UID={os.getenv('DB_USER')};"
    f"PWD={os.getenv('DB_PASSWORD')};"
    f"Connection Timeout=10;"
)

print(connection_string)

try:
    conn = pyodbc.connect(connection_string)

    cursor = conn.cursor()
    cursor.execute("SELECT 1")

    print("✅ Kết nối thành công")

    conn.close()

except Exception as e:
    print(f"❌ Kết nối database thất bại: {e}")