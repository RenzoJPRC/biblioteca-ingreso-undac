import math
import pandas as pd
from sqlalchemy import text
from app.db import SessionLocal

# Mapeo flexible de columnas (por si llegan con nombres distintos)
COL_MAP = {
    "apellidos_nombres": ["APELLIDOS_NOMBRES", "APELLIDOS Y NOMBRES", "APELLIDOS Y NOMBRE", "apellidos_y_nombre", "apellidos_nombres"],
    "dni": ["DNI", "dni"],
    "codigo_matricula": ["CODIGO_DE_MATRICULA", "CODIGO DE MATRICULA", "codigo_de_matricula", "codigo_matricula"],
    "correo_institucional": ["CORREO_INSTITUCIONAL", "correo_institucional"],
    "correo_personal": ["CORREO_PERSONAL", "correo_personal"],
    "escuela": ["ESCUELA", "escuela"],
    "facultad": ["FACULTAD", "facultad"],
    "semestre": ["SEMESTRE", "semestre"],
}

REQUIRED = ["dni", "codigo_matricula", "apellidos_nombres", "escuela", "facultad"]

def _find_col(cols, aliases):
    cols_lower = {c.lower(): c for c in cols}
    for a in aliases:
        if a.lower() in cols_lower:
            return cols_lower[a.lower()]
    return None

def _clean_str(x):
    if x is None:
        return None
    s = str(x).strip()
    return s if s != "" and s.lower() != "nan" else None

def import_padron_from_excel(path_xlsx: str):
    df = pd.read_excel(path_xlsx)

    # Resolver nombres de columnas
    resolved = {}
    for key, aliases in COL_MAP.items():
        col = _find_col(df.columns, aliases)
        if col:
            resolved[key] = col

    missing = [k for k in REQUIRED if k not in resolved]
    if missing:
        return {
            "ok": False,
            "error": f"Faltan columnas obligatorias: {missing}",
            "cols": list(df.columns),
        }

    # Construir df normalizado
    out = pd.DataFrame()
    for k, colname in resolved.items():
        out[k] = df[colname]

    # limpieza
    out = out.where(pd.notnull(out), None)

    insertados = 0
    ya_existian = 0
    errores = 0
    detalle_errores = []

    db = SessionLocal()
    try:
        for _, r in out.iterrows():
            dni = _clean_str(r.get("dni"))
            if dni and dni.isdigit():
                dni = dni.zfill(8)

            cod = _clean_str(r.get("codigo_matricula"))
            if cod and cod.isdigit():
                cod = cod.zfill(10)

            nom = _clean_str(r.get("apellidos_nombres"))
            esc = _clean_str(r.get("escuela"))
            fac = _clean_str(r.get("facultad"))
            ci = _clean_str(r.get("correo_institucional"))
            cp = _clean_str(r.get("correo_personal"))

            sem = r.get("semestre")
            # semestre: permitir None o int 1..10
            semestre = None
            try:
                if sem is None or (isinstance(sem, float) and math.isnan(sem)):
                    semestre = None
                else:
                    semestre = int(str(sem).strip())
                    if semestre < 1 or semestre > 10:
                        semestre = None
            except:
                semestre = None

            # validar obligatorios
            if not (dni and cod and nom and esc and fac):
                errores += 1
                if len(detalle_errores) < 10:
                    detalle_errores.append(f"Fila inválida (faltan obligatorios): dni={dni}, cod={cod}, nom={nom}")
                continue

            # validar formatos (DNI 8, matrícula 10) - opcional, pero recomendado
            if not (dni.isdigit() and len(dni) == 8):
                errores += 1
                if len(detalle_errores) < 10:
                    detalle_errores.append(f"DNI inválido: {dni} (debe ser 8 dígitos)")
                continue

            if not (cod.isdigit() and len(cod) == 10):
                errores += 1
                if len(detalle_errores) < 10:
                    detalle_errores.append(f"Código matrícula inválido: {cod} (debe ser 10 dígitos)")
                continue

            # ¿existe por DNI o por código?
            exists = db.execute(text("""
                SELECT TOP 1 dni
                FROM PADRON_ALUMNO
                WHERE dni = :dni OR codigo_matricula = :cod
            """), {"dni": dni, "cod": cod}).fetchone()

            if exists:
                ya_existian += 1
                continue

            try:
                db.execute(text("""
                    INSERT INTO PADRON_ALUMNO
                    (dni, codigo_matricula, apellidos_nombres, escuela, facultad,
                     correo_institucional, correo_personal, semestre, condicion)
                    VALUES
                    (:dni, :cod, :nom, :esc, :fac, :ci, :cp, :sem, 'REGULAR')
                """), {
                    "dni": dni,
                    "cod": cod,
                    "nom": nom,
                    "esc": esc,
                    "fac": fac,
                    "ci": ci,
                    "cp": cp,
                    "sem": semestre
                })
                insertados += 1
            except Exception as e:
                errores += 1
                if len(detalle_errores) < 10:
                    detalle_errores.append(f"Error insert dni={dni} cod={cod}: {e}")

        db.commit()
    finally:
        db.close()

    return {
        "ok": True,
        "insertados": insertados,
        "ya_existian": ya_existian,
        "errores": errores,
        "detalle_errores": detalle_errores,
    }
