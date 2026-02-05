# app/db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()  # lee .env desde la raíz

server = os.getenv("DB_SERVER", "localhost")  # ej: "RENZO\\SQLEXPRESS" o "localhost"
database = os.getenv("DB_NAME", "BIBLIOTECA_INGRESO")
driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

conn_str = (
    f"mssql+pyodbc://@{server}/{database}"
    f"?driver={driver.replace(' ', '+')}"
    f"&Trusted_Connection=yes"
    f"&TrustServerCertificate=yes"
)

engine = create_engine(conn_str, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
