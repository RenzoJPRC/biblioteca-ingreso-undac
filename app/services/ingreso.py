# app/services/ingreso.py
from datetime import datetime, date, time
from sqlalchemy import text
from sqlalchemy.orm import Session

def detectar_tipo_codigo(codigo: str) -> str:
    codigo = codigo.strip()
    if codigo.isdigit() and len(codigo) == 8:
        return "DNI"
    if codigo.isdigit() and len(codigo) == 10:
        return "MATRICULA"
    return "INVALIDO"

def obtener_turno(session: Session, ahora: datetime) -> str:
    row = session.execute(text("""
        SELECT TOP 1 inicio_manana, fin_manana, inicio_tarde, fin_tarde
        FROM CONFIG_TURNO
        ORDER BY id_config ASC
    """)).mappings().first()

    t = ahora.time()

    # fallback por si no hay fila de config (aunque tú ya insertaste default)
    if row is None:
        return "MANANA" if t < time(13, 30) else "TARDE"

    if row["inicio_manana"] <= t < row["fin_manana"]:
        return "MANANA"
    if row["inicio_tarde"] <= t < row["fin_tarde"]:
        return "TARDE"

    # Fuera de rangos: por defecto lo asignamos a TARDE
    return "TARDE"

def buscar_alumno(session: Session, tipo_codigo: str, codigo: str):
    if tipo_codigo == "DNI":
        q = text("""
            SELECT dni, apellidos_nombres, escuela, facultad
            FROM PADRON_ALUMNO
            WHERE dni = :codigo
        """)
    else:
        q = text("""
            SELECT dni, apellidos_nombres, escuela, facultad
            FROM PADRON_ALUMNO
            WHERE codigo_matricula = :codigo
        """)

    return session.execute(q, {"codigo": codigo}).mappings().first()

def ya_registrado(session: Session, dni: str | None, piso: int, turno: str, fecha_hoy: date,
                  tipo_codigo: str, codigo: str) -> bool:
    """
    Regla final:
    - Si alumno ENCONTRADO (dni no None): bloquear por dni_enlazado + piso + turno + fecha
    - Si NO_ENCONTRADO: bloquear por tipo_codigo + codigo_leido + piso + turno + fecha
    """
    if dni:
        q = text("""
            SELECT TOP 1 1
            FROM INGRESO
            WHERE dni_enlazado = :dni
              AND piso = :piso
              AND turno = :turno
              AND fecha = :fecha
        """)
        r = session.execute(q, {"dni": dni, "piso": piso, "turno": turno, "fecha": fecha_hoy}).first()
        return r is not None

    # fallback (por si no hay dni enlazado)
    q2 = text("""
        SELECT TOP 1 1
        FROM INGRESO
        WHERE tipo_codigo = :tipo
          AND codigo_leido = :codigo
          AND piso = :piso
          AND turno = :turno
          AND fecha = :fecha
    """)
    r2 = session.execute(q2, {"tipo": tipo_codigo, "codigo": codigo, "piso": piso, "turno": turno, "fecha": fecha_hoy}).first()
    return r2 is not None

def registrar_ingreso(session: Session, piso: int, codigo: str):
    ahora = datetime.now()
    fecha_hoy = ahora.date()

    tipo = detectar_tipo_codigo(codigo)
    if tipo == "INVALIDO":
        return {"ok": False, "mensaje": "Código inválido (DNI=8 dígitos o Matrícula=10 dígitos)."}

    turno = obtener_turno(session, ahora)

    alumno = buscar_alumno(session, tipo, codigo)

    if alumno:
        dni = alumno["dni"]
        dni = str(dni).zfill(8)
        estado = "ENCONTRADO"
        datos = {
            "apellidos_nombres": alumno["apellidos_nombres"],
            "escuela": alumno["escuela"],
            "facultad": alumno["facultad"],
        }
    else:
        dni = None
        estado = "NO_ENCONTRADO"
        datos = None

    if ya_registrado(session, dni, piso, turno, fecha_hoy, tipo, codigo):
        return {
            "ok": False,
            "bloqueado": True,
            "mensaje": "Ya se registró en este piso y turno.",
            "turno": turno,
            "hora": ahora.strftime("%H:%M:%S"),
        }

    session.execute(text("""
        INSERT INTO INGRESO (fecha_hora, fecha, piso, turno, tipo_codigo, codigo_leido, dni_enlazado, estado_busqueda)
        VALUES (:fecha_hora, :fecha, :piso, :turno, :tipo_codigo, :codigo_leido, :dni_enlazado, :estado_busqueda)
    """), {
        "fecha_hora": ahora,
        "fecha": fecha_hoy,
        "piso": piso,
        "turno": turno,
        "tipo_codigo": tipo,
        "codigo_leido": codigo,
        "dni_enlazado": dni,
        "estado_busqueda": estado,
    })
    session.commit()

    return {
        "ok": True,
        "mensaje": "Ingreso registrado" if alumno else "Alumno no encontrado - Ingreso registrado",
        "turno": turno,
        "hora": ahora.strftime("%H:%M:%S"),
        "datos": datos,
    }
