from flask import Blueprint, render_template, request, session, redirect, url_for
from db import get_db_connection
import json

admin_auditoria_bp = Blueprint('admin_auditoria', __name__, url_prefix='/admin/auditoria')

def traducir_accion(accion_raw):
    if not accion_raw: return "Acción Desconocida"
    a = accion_raw.upper()
    if 'GUARDAR_EVENTO' in a: return 'Crear Evento'
    if 'ELIMINAR_EVENTO' in a: return 'Eliminar Evento'
    if 'VISITANTES/ELIMINAR' in a: return 'Borrar Visitante'
    if 'VISITANTES/VACIAR' in a: return 'Vaciar Visitantes'
    if 'PROCESAR_EXCEL_VISITANTES' in a: return 'Importar Visitantes'
    if 'ELIMINAR_ALUMNOS_MASIVO' in a: return 'Borrar Alumnos Masivo'
    if 'ACTUALIZAR_CARNET_MASIVO' in a: return 'Alterar Carnets Masivo'
    if 'ACTUALIZAR_CARNET_GLOBAL' in a: return 'Alterar Carnets (Global)'
    if 'SUBIR_EXCEL' in a: return 'Importar Alumnos'
    if 'BACKUP/GENERAR' in a: return 'Exportar Backup .ZIP'
    if 'AGREGAR_VISITANTE' in a: return 'Crear Visitante'
    if 'ELIMINAR_VISITANTE' in a: return 'Borrar Visitante'
    if 'ACCESOS/CREAR' in a: return 'Crear Gestor RBAC'
    if 'ACCESOS/ELIMINAR' in a: return 'Eliminar Gestor RBAC'
    if 'ACCESOS/EDITAR' in a: return 'Editar Gestor RBAC'
    if 'GUARDAR_EGRESADO' in a: return 'Registrar Múltiple Egresado'
    if 'EGRESADOS/ELIMINAR' in a: return 'Eliminar Egresado'
    if 'EGRESADOS/VACIAR' in a: return 'Vaciar Egresados'
    if 'EGRESADOS/IMPORTAR' in a: return 'Importar Egresados'
    if 'EGRESADOS/ACCION_MASIVA' in a: return 'Alterar Egresados Max'
    if 'PERSONAL/ELIMINAR' in a: return 'Eliminar Personal'
    if 'PERSONAL/VACIAR' in a: return 'Vaciar Personal'
    if 'PERSONAL/IMPORTAR' in a: return 'Importar Personal'
    return accion_raw

def parsear_detalle(detalle_str):
    if not detalle_str: return "Sin detalles adjuntos"
    try:
        if "Interceptado:" in detalle_str:
            raw_json = detalle_str.split(":", 1)[1].strip()
            parsed = json.loads(raw_json)
            
            items = []
            for k, v in parsed.items():
                k_lower = k.lower()
                if 'csrf' in k_lower or 'password' in k_lower: continue
                if str(v).strip():
                    items.append(f"{k}: {v}")
            return " ➔ ".join(items) if items else "Sin metadatos relevantes"
        return detalle_str
    except:
        return detalle_str

@admin_auditoria_bp.route('/')
def index():
    if session.get('admin_rol') != 'SuperAdmin':
        return redirect(url_for('admin_dashboard.admin_dashboard'))
        
    conn = get_db_connection()
    if not conn:
        return "Error BD"
        
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TOP 200 LogID, Usuario, Accion, Detalle, IP, FORMAT(Fecha, 'dd/MM/yyyy HH:mm:ss') as FechaFmt
        FROM AdminAuditLog
        ORDER BY Fecha DESC
    """)
    logs = cursor.fetchall()
    
    # Algunas métricas rápidas
    cursor.execute("SELECT COUNT(*) FROM AdminAuditLog")
    total_logs = cursor.fetchone()[0]
    
    cursor.execute("SELECT TOP 5 Usuario, COUNT(*) as Ops FROM AdminAuditLog GROUP BY Usuario ORDER BY Ops DESC")
    top_usuarios = cursor.fetchall()

    conn.close()
    
    # Post-Procesamiento Semántico
    processed_logs = []
    for log in logs:
        lid, usr, acc, det, ip, ffmt = log
        acc_legible = traducir_accion(acc)
        det_legible = parsear_detalle(det)
        processed_logs.append((lid, usr, acc_legible, det_legible, ip, ffmt))
    
    return render_template('admin_auditoria.html', logs=processed_logs, total=total_logs, tops=top_usuarios)
