# scripts/import_padron.py
import os
import sys
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import math


load_dotenv()

DB_SERVER = os.getenv("DB_SERVER", "RENZO")
DB_NAME = os.getenv("DB_NAME", "BIBLIOTECA_INGRESO")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

CONN_STR = (
    f"mssql+pyodbc://@{DB_SERVER}/{DB_NAME}"
    f"?driver={DB_DRIVER.replace(' ', '+')}"
    f"&Trusted_Connection=yes"
    f"&TrustServerCertificate=yes"
)

def norm_col(c: str) -> str:
    return (
        str(c).strip()
        .lower()
        .replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u").replace("ñ","n")
        .replace(" ", "_")
    )

def digits_only(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    # si viene como 12345678.0
    if s.endswith(".0"):
        s = s[:-2]
    return "".join(ch for ch in s if ch.isdigit())

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_padron.py <ruta_excel>")
        sys.exit(1)

    excel_path = sys.argv[1]
    if not os.path.exists(excel_path):
        print(f"ERROR: No existe el archivo: {excel_path}")
        sys.exit(1)

    print("Leyendo Excel:", excel_path)
    df = pd.read_excel(excel_path, dtype=str)
    df.columns = [norm_col(c) for c in df.columns]

    # --- Mapeo flexible de columnas (según cómo venga el Excel) ---
    # Intenta encontrar automáticamente las columnas típicas
    col_dni = next((c for c in df.columns if c in ["dni", "num_dni", "documento", "nro_dni"]), None)
    col_cod = next((c for c in df.columns if c in ["codigo_matricula", "cod_matricula", "codigo", "codigomatricula", "codigo_de_matricula"]), None)
    col_nom = next((c for c in df.columns if c in ["apellidos_nombres", "apellidos_y_nombres", "apellidos_y_nombre", "nombres", "nombre_completo"]), None)
    col_esc = next((c for c in df.columns if c in ["escuela", "escuela_profesional"]), None)
    col_fac = next((c for c in df.columns if c in ["facultad"]), None)

    # Opcionales
    col_ci = next((c for c in df.columns if "correo" in c and "instit" in c), None)
    col_cp = next((c for c in df.columns if "correo" in c and "person" in c), None)
    col_sem = next((c for c in df.columns if c in ["semestre", "ciclo"]), None)

    faltantes = [x for x in [("DNI", col_dni), ("CODIGO_MATRICULA", col_cod), ("APELLIDOS_NOMBRES", col_nom), ("ESCUELA", col_esc), ("FACULTAD", col_fac)] if x[1] is None]
    if faltantes:
        print("ERROR: No pude detectar columnas obligatorias. Faltan:", [f[0] for f in faltantes])
        print("Columnas encontradas:", list(df.columns))
        sys.exit(1)

    # Limpieza/validación
    out = pd.DataFrame()
    out["dni"] = df[col_dni].apply(digits_only).str.zfill(8)
    out["codigo_matricula"] = df[col_cod].apply(digits_only).str.zfill(10)
    out["apellidos_nombres"] = df[col_nom].fillna("").astype(str).str.strip()
    out["escuela"] = df[col_esc].fillna("").astype(str).str.strip()
    out["facultad"] = df[col_fac].fillna("").astype(str).str.strip()

    if col_ci: out["correo_institucional"] = df[col_ci].fillna("").astype(str).str.strip()
    else: out["correo_institucional"] = None

    if col_cp: out["correo_personal"] = df[col_cp].fillna("").astype(str).str.strip()
    else: out["correo_personal"] = None

    if col_sem:
        out["semestre"] = df[col_sem].apply(digits_only)
        out.loc[~out["semestre"].isin([str(i) for i in range(1,11)]), "semestre"] = None
    else:
        out["semestre"] = None

    # Quitar filas vacías
    out = out[(out["dni"].str.len() == 8) & (out["codigo_matricula"].str.len() == 10)]
    out = out[out["apellidos_nombres"] != ""]

    # Duplicados dentro del Excel
    dup_dni = out[out.duplicated("dni", keep=False)].copy()
    dup_cod = out[out.duplicated("codigo_matricula", keep=False)].copy()

    if not dup_dni.empty or not dup_cod.empty:
        print("ERROR: Hay duplicados dentro del Excel (DNI o CODIGO_MATRICULA). Corrige antes de importar.")
        if not dup_dni.empty:
            print("Duplicados por DNI (muestra 10):")
            print(dup_dni[["dni","codigo_matricula","apellidos_nombres"]].head(10).to_string(index=False))
        if not dup_cod.empty:
            print("Duplicados por CODIGO_MATRICULA (muestra 10):")
            print(dup_cod[["dni","codigo_matricula","apellidos_nombres"]].head(10).to_string(index=False))
        sys.exit(1)

    engine = create_engine(CONN_STR, pool_pre_ping=True)

    insert_sql = text("""
        INSERT INTO PADRON_ALUMNO
        (dni, codigo_matricula, apellidos_nombres, escuela, facultad, correo_institucional, correo_personal, semestre, condicion)
        VALUES
        (:dni, :codigo_matricula, :apellidos_nombres, :escuela, :facultad, :correo_institucional, :correo_personal, :semestre, 'REGULAR')
    """)

    # Inserción fila por fila (simple para MVP). Luego optimizamos si quieres.
    ok = 0
    ya_existe = 0
    errores = 0

    with engine.begin() as conn:
        # Convertir NaN a None (SQL Server no acepta NaN)
        out = out.where(pd.notnull(out), None)

        for row in out.to_dict(orient="records"):
            # Normalizar semestre: NaN -> None
            sem = row.get("semestre", None)
            if sem is None or sem == "" or (isinstance(sem, float) and math.isnan(sem)):
                row["semestre"] = None
            else:
                # asegurar int (1..10) o None
                try:
                    row["semestre"] = int(str(sem))
                    if row["semestre"] < 1 or row["semestre"] > 10:
                        row["semestre"] = None
                except:
                    row["semestre"] = None
                    
            try:
                # Si ya existe, no insertamos (por ahora)
                existe = conn.execute(
                    text("SELECT 1 FROM PADRON_ALUMNO WHERE dni = :dni"),
                    {"dni": row["dni"]}
                ).first()

                if existe:
                    ya_existe += 1
                    continue

                conn.execute(insert_sql, row)
                ok += 1
            except Exception as e:
                errores += 1
                if errores <= 5:
                    print("ERROR fila:", row, "\n", e)

    print(f"Import finalizado: insertados={ok}, ya_existian={ya_existe}, errores={errores}")

if __name__ == "__main__":
    main()
