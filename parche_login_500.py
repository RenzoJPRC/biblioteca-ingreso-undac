import os
import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=BibliotecaUNDAC;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    print(">> REPARANDO ESTRUCTURA DE CREDENCIALES ADMINISTRATIVAS <<")

    # 1. Crear tabla si no existe
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'UsuariosSistema')
    BEGIN
        CREATE TABLE UsuariosSistema (
            UsuarioID INT IDENTITY(1,1) PRIMARY KEY,
            Usuario NVARCHAR(100) UNIQUE NOT NULL,
            PasswordHash NVARCHAR(255) NOT NULL,
            Email NVARCHAR(150) NULL,
            Rol NVARCHAR(50) DEFAULT 'Administrador',
            SedeAsignada NVARCHAR(50) DEFAULT 'Central',
            Activo BIT DEFAULT 1,
            CreadoEn DATETIME DEFAULT GETDATE()
        );
    END
    """)
    
    # 2. Agregar columnas extra por si era muy vieja
    columnas = [
        ("Email", "NVARCHAR(150) NULL"),
        ("SedeAsignada", "NVARCHAR(50) DEFAULT 'Central'"),
        ("Activo", "BIT DEFAULT 1"),
        ("Rol", "NVARCHAR(50) DEFAULT 'Administrador'"),
        ("CreadoEn", "DATETIME DEFAULT GETDATE()")
    ]
    for col, tipo in columnas:
        cursor.execute(f"""
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE Name = N'{col}' AND Object_ID = Object_ID(N'UsuariosSistema'))
        BEGIN
            ALTER TABLE UsuariosSistema ADD {col} {tipo};
        END
        """)

    # 3. Usuario Rescate admin123
    cursor.execute("SELECT COUNT(*) FROM UsuariosSistema")
    if cursor.fetchone()[0] == 0:
        hash_rescate = "scrypt:32768:8:1$YFwM0aX55jFqjM7t$97ebcd38e9ab5f25c88b0a70f3f26010d8a55b0a3acb670f59013c706fe2dcf1b1dbd8ff26191b9f6b986b6279f5fddfd3c1af0ba6b75825310619a96e6d1c92"
        cursor.execute("""
            INSERT INTO UsuariosSistema (Usuario, PasswordHash, Email, Rol, SedeAsignada, Activo) 
            VALUES ('admin', ?, 'rescate@undac.edu.pe', 'SuperAdmin', 'Central', 1)
        """, (hash_rescate,))
        print("\n[!] USUARIO DE RESCATE CREADO [!]")
        print(" -> Usuario: admin")
        print(" -> Clave: admin123")
    else:
        print("\n[OK] Ya existen administradores, no se creo el cuenta de rescate.")

    conn.commit()
    print("\n[EXITO] Login 500 Reparado.")

except Exception as e:
    print(f"\n[X] Hubo un error: {e}")
finally:
    if 'conn' in locals():
        conn.close()

input("\nPresiona ENTER para salir y volver a probar...")
