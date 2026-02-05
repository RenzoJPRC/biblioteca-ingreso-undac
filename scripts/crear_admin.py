import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

load_dotenv()

server = os.getenv("DB_SERVER", "RENZO")
db = os.getenv("DB_NAME", "BIBLIOTECA_INGRESO")
driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

conn_str = (
    f"mssql+pyodbc://@{server}/{db}"
    f"?driver={driver.replace(' ', '+')}"
    f"&Trusted_Connection=yes"
    f"&TrustServerCertificate=yes"
)

engine = create_engine(conn_str)

usuario = "admin"
email = "admin@undac.edu.pe"
password = "Admin12345"   # luego lo cambias

pwd_hash = generate_password_hash(password)  # 🔐 seguro

with engine.begin() as conn:
    conn.execute(text("""
        IF NOT EXISTS (SELECT 1 FROM ADMIN_USUARIO WHERE usuario=:u)
        INSERT INTO ADMIN_USUARIO(usuario, email, password_hash)
        VALUES (:u, :e, :p)
    """), {"u": usuario, "e": email, "p": pwd_hash})

print("✅ Admin creado/verificado")
print("Usuario:", usuario)
print("Password:", password)
