from flask import Blueprint, render_template, request, session, redirect, url_for, flash, send_file
import pandas as pd
import io
import zipfile
from datetime import datetime
from db import get_db_connection

admin_backup_bp = Blueprint('admin_backup', __name__, url_prefix='/admin/backup')

@admin_backup_bp.route('/')
def index():
    if session.get('admin_rol') != 'SuperAdmin':
        flash('Acceso denegado. Se requiere Nivel SuperAdmin para generar y descargar copias de seguridad de la Base de Datos.', 'error')
        return redirect(url_for('admin_dashboard.admin_dashboard'))
    return render_template('admin_backup.html')

@admin_backup_bp.route('/generar', methods=['POST'])
def generar():
    if session.get('admin_rol') != 'SuperAdmin':
        return redirect(url_for('admin_dashboard.admin_dashboard'))
        
    conn = get_db_connection()
    if not conn:
        flash("Error de conexión a la base de datos.", "error")
        return redirect(url_for('admin_backup.index'))
    
    try:
        # Generar dataframes de las tablas principales
        tablas = {
            'Alumnos': "SELECT * FROM Alumnos",
            'Egresados': "SELECT * FROM Egresados",
            'PersonalAdm': "SELECT * FROM PersonalAdministrativo",
            'Visitantes': "SELECT * FROM Visitantes",
            'EventosEspeciales': "SELECT * FROM Eventos",
            'UsuariosSistema': "SELECT * FROM UsuariosSistema",
            'AdminAuditLog': "SELECT * FROM AdminAuditLog",
            'Libros_BD_Externa': "SELECT * FROM Libros",
            'Prestamos_BD_Externa': "SELECT * FROM Prestamos",
            'Facultades_BD_Externa': "SELECT * FROM Facultades"
        }
        
        memory_file = io.BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for nombre_tabla, query in tablas.items():
                df = pd.read_sql(query, conn)
                
                # Crear Excel en memoria Buffer
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name=nombre_tabla)
                
                # Escribir el binario compilado excel dentro de la raíz del ZIP
                zf.writestr(f"{nombre_tabla}_backup_{datetime.now().strftime('%d%m%Y')}.xlsx", excel_buffer.getvalue())
                
    except Exception as e:
        flash(f"Error crítico generando el backup perimetral: {str(e)}", "error")
        return redirect(url_for('admin_backup.index'))
    finally:
        conn.close()
        
    # Reset stream cursor prior flush
    memory_file.seek(0)
    
    fecha_hoy = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"DB_SistemaBiblioteca_Backup_{fecha_hoy}.zip"
    
    return send_file(
        memory_file,
        download_name=filename,
        as_attachment=True,
        mimetype='application/zip'
    )
