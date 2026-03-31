from flask import Blueprint, render_template, request, session, redirect, url_for
from db import get_db_connection

admin_auditoria_bp = Blueprint('admin_auditoria', __name__, url_prefix='/admin/auditoria')

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
    
    return render_template('admin_auditoria.html', logs=logs, total=total_logs, tops=top_usuarios)
