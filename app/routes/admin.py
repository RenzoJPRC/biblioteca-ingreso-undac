import os
import tempfile
import io
import zipfile
from datetime import datetime

import pandas as pd
from pydantic import BaseModel
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import SessionLocal
from app.services.auth import check_admin_ip, get_allowed_ips
from app.services.padron_importer import import_padron_from_excel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

def require_admin(request: Request):
    # Primero validar IP
    if not check_admin_ip(request):
        return False
    return request.session.get("admin_user") is not None

class PasswordPayload(BaseModel):
    password: str

@router.post("/api/admin/verify")
def verify_password_endpoint(request: Request, payload: PasswordPayload):
    # No requerimos sesión activa, solo conocer la clave maestra
    # para permitir salir del modo Kiosco
    db = SessionLocal()
    try:
        # Verificamos contra cualquier admin activo (o uno especifico 'admin')
        row = db.execute(
            text("SELECT password_hash FROM ADMIN_USUARIO WHERE usuario = 'admin' AND activo = 1")
        ).mappings().first()
        
        if row and check_password_hash(row["password_hash"], payload.password):
            # Desbloquear Kiosco (Sticky Session)
            request.session.pop("kiosk_floor", None)
            return {"ok": True}
            
        return {"ok": False}
    finally:
        db.close()

@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    # Seguridad IP en Login
    if not check_admin_ip(request):
        return HTMLResponse("<h1>Acceso Prohibido</h1><p>Su IP no está autorizada para acceder a este panel.</p>", status_code=403)

    if require_admin(request):
        return RedirectResponse(url="/panel", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@router.post("/login", response_class=HTMLResponse)
def login_post(request: Request, usuario: str = Form(...), password: str = Form(...)):
    # Seguridad IP en Login Post
    if not check_admin_ip(request):
        return HTMLResponse("Acceso Prohibido", status_code=403)

    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT usuario, password_hash, activo FROM ADMIN_USUARIO WHERE usuario = :u"),
            {"u": usuario},
        ).mappings().first()

        if (not row) or (row["activo"] == 0) or (not check_password_hash(row["password_hash"], password)):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Usuario o contraseña incorrectos."},
                status_code=401,
            )

        request.session["admin_user"] = row["usuario"]
        return RedirectResponse(url="/panel", status_code=302)
    finally:
        db.close()

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@router.get("/panel", response_class=HTMLResponse)
def panel(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=302)

    db = SessionLocal()
    try:
        # métricas básicas
        total_hoy = db.execute(text("""
            SELECT COUNT(*) 
            FROM INGRESO 
            WHERE fecha = CAST(GETDATE() AS DATE)
        """)).scalar() or 0

        por_piso = db.execute(text("""
            SELECT piso, COUNT(*) as total
            FROM INGRESO
            WHERE fecha = CAST(GETDATE() AS DATE)
            GROUP BY piso
            ORDER BY piso
        """)).mappings().all()

        por_turno = db.execute(text("""
            SELECT turno, COUNT(*) as total
            FROM INGRESO
            WHERE fecha = CAST(GETDATE() AS DATE)
            GROUP BY turno
            ORDER BY turno
        """)).mappings().all()

        # Datos para Gráfico: Por Hora
        por_hora_raw = db.execute(text("""
            SELECT DATEPART(HOUR, fecha_hora) as h, COUNT(*) as total
            FROM INGRESO
            WHERE fecha = CAST(GETDATE() AS DATE)
            GROUP BY DATEPART(HOUR, fecha_hora)
            ORDER BY h
        """)).mappings().all()

        chart_labels = []
        chart_data = []
        
        for r in por_hora_raw:
            h_str = f"{r.h}:00"
            chart_labels.append(h_str)
            chart_data.append(r.total)

        return templates.TemplateResponse(
            "panel.html",
            {
                "request": request,
                "admin_user": request.session.get("admin_user"),
                "total_hoy": total_hoy,
                "por_piso": por_piso,
                "por_turno": por_turno,
                "chart_labels": chart_labels,
                "chart_data": chart_data,
            },
        )
    finally:
        db.close()


@router.get("/admin/reportes", response_class=HTMLResponse)
def reportes_view(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("reportes.html", {"request": request})


@router.get("/admin/api/stats")
def api_stats(request: Request, start: str, end: str):
    if not require_admin(request):
        return {"ok": False, "msg": "Unauthorized"}
    
    # Validar fechas (simple)
    if not start or not end:
         return {"ok": False, "msg": "Fechas requeridas"}

    db = SessionLocal()
    try:
        # 1. KPIs
        kpi_total = db.execute(text("""
            SELECT COUNT(*) FROM INGRESO WHERE fecha BETWEEN :start AND :end
        """), {"start": start, "end": end}).scalar() or 0

        kpi_unique = db.execute(text("""
            SELECT COUNT(DISTINCT codigo_leido) FROM INGRESO WHERE fecha BETWEEN :start AND :end
        """), {"start": start, "end": end}).scalar() or 0

        # Dias en el rango para promedio
        # diff days basic SQL: DATEDIFF(day, :start, :end) + 1
        num_days = db.execute(text("SELECT DATEDIFF(day, :start, :end) + 1"), {"start": start, "end": end}).scalar() or 1
        if num_days < 1: num_days = 1
        
        avg_daily = round(kpi_total / num_days, 1) if num_days > 0 else 0

        # Top Day (el dia con mas ingresos)
        top_day_row = db.execute(text("""
             SELECT TOP 1 fecha, COUNT(*) as total 
             FROM INGRESO 
             WHERE fecha BETWEEN :start AND :end
             GROUP BY fecha 
             ORDER BY total DESC
        """), {"start": start, "end": end}).mappings().first()
        
        top_day_str = str(top_day_row.fecha) if top_day_row else "-"

        # 2. Trend (Ingresos por dia)
        trend_raw = db.execute(text("""
            SELECT fecha, COUNT(*) as total
            FROM INGRESO
            WHERE fecha BETWEEN :start AND :end
            GROUP BY fecha
            ORDER BY fecha
        """), {"start": start, "end": end}).mappings().all()

        trend_labels = [str(r.fecha) for r in trend_raw]
        trend_values = [r.total for r in trend_raw]

        # 3. Faculty Distribution (JOIN con Padron)
        # Ojo: Padron puede tener apellidos_nombres, escuela, facultad
        # Mapeamos por DNI o codigo, igual que el Excel
        # Agrupamos por PADRON_ALUMNO.facultad
        fac_raw = db.execute(text("""
            SELECT p.facultad, COUNT(*) as total
            FROM INGRESO i
            JOIN PADRON_ALUMNO p ON (
                (i.dni_enlazado IS NOT NULL AND i.dni_enlazado = p.dni) OR
                (i.dni_enlazado IS NULL AND i.codigo_leido = p.codigo_matricula)
            )
            WHERE i.fecha BETWEEN :start AND :end
            GROUP BY p.facultad
            ORDER BY total DESC
        """), {"start": start, "end": end}).mappings().all()

        fac_labels = [str(r.facultad or 'Desconocido') for r in fac_raw]
        fac_values = [r.total for r in fac_raw]

        # 4. Top Schools
        schools_raw = db.execute(text("""
            SELECT TOP 10 p.escuela, p.facultad, COUNT(*) as total
            FROM INGRESO i
            JOIN PADRON_ALUMNO p ON (
                (i.dni_enlazado IS NOT NULL AND i.dni_enlazado = p.dni) OR
                (i.dni_enlazado IS NULL AND i.codigo_leido = p.codigo_matricula)
            )
            WHERE i.fecha BETWEEN :start AND :end
            GROUP BY p.escuela, p.facultad
            ORDER BY total DESC
        """), {"start": start, "end": end}).mappings().all()
        
        top_schools = [{"escuela": r.escuela, "facultad": r.facultad, "total": r.total} for r in schools_raw]

        return {
            "ok": True,
            "kpi": {
                "total": kpi_total,
                "avg_daily": avg_daily,
                "unique_students": kpi_unique,
                "top_day_name": top_day_str
            },
            "trend": { "labels": trend_labels, "values": trend_values },
            "faculty": { "labels": fac_labels, "values": fac_values },
            "top_schools": top_schools
        }

    except Exception as e:
        print(f"Error api stats: {e}")
        return {"ok": False, "msg": str(e)}
    finally:
        db.close()



@router.get("/admin/reporte/excel")
def reporte_excel(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=302)

    db = SessionLocal()
    try:
        # Query todos los ingresos de hoy
        q = text("""
            SELECT 
                FORMAT(fecha_hora, 'HH:mm:ss') as Hora,
                tipo_codigo as Tipo,
                codigo_leido as Codigo,
                dni_enlazado as DNI_Real,
                piso as Piso,
                turno as Turno
            FROM INGRESO
            WHERE fecha = CAST(GETDATE() AS DATE)
            ORDER BY fecha_hora DESC
        """)
        # Podríamos hacer un JOIN con PADRON_ALUMNO para sacar nombres si queremos
        # Pero por rendimiento/simplicidad, primero volcamos lo que hay en INGRESO
        # Si quieres nombres, hacemos JOIN. El usuario pidió "Nombre, Escuela".
        
        q_full = text("""
            SELECT 
                FORMAT(i.fecha_hora, 'HH:mm:ss') as Hora,
                i.codigo_leido as Codigo,
                p.apellidos_nombres as Nombre,
                p.escuela as Escuela,
                p.facultad as Facultad,
                i.piso as Piso,
                i.turno as Turno
            FROM INGRESO i
            LEFT JOIN PADRON_ALUMNO p ON (
                (i.dni_enlazado IS NOT NULL AND i.dni_enlazado = p.dni) OR
                (i.dni_enlazado IS NULL AND i.codigo_leido = p.codigo_matricula)
                -- Lógica simplificada de join, asumiendo enlace por DNI principalmente
            )
            WHERE i.fecha = CAST(GETDATE() AS DATE)
            ORDER BY i.fecha_hora DESC
        """)
        
        result = db.execute(q_full)
        rows = result.mappings().all()
        
        # Convertir a DataFrame
        df = pd.DataFrame(rows)
        
        # Generar Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Ingresos Hoy')
        
        output.seek(0)
        
        headers = {
            'Content-Disposition': 'attachment; filename="reporte_ingresos.xlsx"'
        }
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    finally:
        db.close()


@router.get("/admin/alumno", response_class=HTMLResponse)
def alumno_get(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("alumno.html", {"request": request, "alumno": None, "msg": None})


@router.post("/admin/alumno", response_class=HTMLResponse)
def alumno_post(request: Request, q: str = Form(...)):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=302)

    db = SessionLocal()
    try:
        q = q.strip()
        row = db.execute(text("""
            SELECT TOP 1 dni, codigo_matricula, apellidos_nombres, escuela, facultad,
                          correo_institucional, correo_personal, semestre, condicion
            FROM PADRON_ALUMNO
            WHERE dni = :q OR codigo_matricula = :q OR apellidos_nombres LIKE '%' + :q + '%'
        """), {"q": q}).mappings().first()

        msg = None if row else "No se encontró alumno."
        return templates.TemplateResponse("alumno.html", {"request": request, "alumno": row, "msg": msg})
    finally:
        db.close()


@router.post("/admin/alumno/condicion")
def alumno_cambiar_condicion(request: Request, dni: str = Form(...), condicion: str = Form(...)):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=302)

    condicion = condicion.strip().upper()
    if condicion not in ("REGULAR", "EGRESADO"):
        return RedirectResponse(url="/admin/alumno", status_code=302)

    db = SessionLocal()
    try:
        db.execute(text("""
            UPDATE PADRON_ALUMNO
            SET condicion = :c
            WHERE dni = :dni
        """), {"c": condicion, "dni": dni})
        db.commit()
        return RedirectResponse(url="/admin/alumno", status_code=302)
    finally:
        db.close()


@router.get("/admin/padron", response_class=HTMLResponse)
def padron_page(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("padron_upload.html", {"request": request, "resultado": None})


@router.post("/admin/padron/upload", response_class=HTMLResponse)
async def padron_upload(request: Request, file: UploadFile = File(...)):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=302)

    if not file.filename.lower().endswith(".xlsx"):
        return templates.TemplateResponse("padron_upload.html", {
            "request": request,
            "resultado": {"insertados": 0, "ya_existian": 0, "errores": 1, "detalle_errores": ["Archivo no es .xlsx"]}
        })

    # guardar temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp_path = tmp.name
        tmp.write(await file.read())

    try:
        resultado = import_padron_from_excel(tmp_path)
        if not resultado.get("ok"):
            # error por columnas
            return templates.TemplateResponse("padron_upload.html", {
                "request": request,
                "resultado": {"insertados": 0, "ya_existian": 0, "errores": 1, "detalle_errores": [resultado.get("error"), f"Columnas: {resultado.get('cols')}"]}
            })

        return templates.TemplateResponse("padron_upload.html", {"request": request, "resultado": resultado})
    finally:
        try:
            os.remove(tmp_path)
        except:
            pass


@router.get("/admin/mantenimiento", response_class=HTMLResponse)
def mantenimiento_page(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mantenimiento.html", {"request": request})


@router.get("/admin/backup/download")
def backup_download(request: Request):
    if not require_admin(request):
        return RedirectResponse(url="/login", status_code=302)

    db = SessionLocal()
    try:
        # 1. Dump Tables to CSV in memory
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zip_file:
            
            # --- Tabla INGRESO ---
            ingresos = db.execute(text("SELECT * FROM INGRESO")).mappings().all()
            if ingresos:
                df_ing = pd.DataFrame(ingresos)
                csv_ing = df_ing.to_csv(index=False)
                zip_file.writestr("ingresos.csv", csv_ing)
            else:
                zip_file.writestr("ingresos.csv", "id,fecha_hora,codigo_leido,tipo_codigo,dni_enlazado,piso,turno\n")

            # --- Tabla PADRON_ALUMNO ---
            # Solo exportamos columnas clave para no hacer el archivo gigante innecesariamente, 
            # o todo si es respaldo completo. Vamos con todo.
            padron = db.execute(text("SELECT * FROM PADRON_ALUMNO")).mappings().all()
            if padron:
                df_pad = pd.DataFrame(padron)
                csv_pad = df_pad.to_csv(index=False)
                zip_file.writestr("padron_alumno.csv", csv_pad)
            else:
                zip_file.writestr("padron_alumno.csv", "dni,codigo_matricula,apellidos_nombres,escuela,facultad,semestre,condicion\n")

            # --- Tabla ADMIN_USUARIO ---
            admins = db.execute(text("SELECT usuario, activo FROM ADMIN_USUARIO")).mappings().all()
            if admins:
                df_adm = pd.DataFrame(admins)
                csv_adm = df_adm.to_csv(index=False)
                zip_file.writestr("admin_usuarios.csv", csv_adm)
            else:
                zip_file.writestr("admin_usuarios.csv", "usuario,activo\n")

            # Metadata
            meta = f"Backup generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            zip_file.writestr("metadata.txt", meta)

        output.seek(0)
        
        filename = f"backup_biblioteca_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        return StreamingResponse(output, headers=headers, media_type='application/zip')

    except Exception as e:
        return HTMLResponse(f"Error generando backup: {str(e)}", status_code=500)
    finally:
        db.close()
