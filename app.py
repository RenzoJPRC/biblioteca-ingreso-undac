from flask import Flask, render_template, request, session, redirect, url_for, g
import secrets
from datetime import timedelta
from db import get_db_connection
from routes.ingreso import ingreso_bp
from routes.visitantes import visitantes_bp

# Módulos Administrador segregados
from routes.admin_dashboard import admin_dashboard_bp
from routes.admin_reportes import admin_reportes_bp
from routes.admin_carnets import admin_carnets_bp
from routes.admin_egresados import admin_egresados_bp
from routes.admin_personal import admin_personal_bp
from routes.admin_eventos import admin_eventos_bp
from routes.admin_tasks import admin_tasks_bp
from routes.admin_auth import admin_auth_bp
from routes.admin_accesos import admin_accesos_bp
from routes.admin_auditoria import admin_auditoria_bp
from routes.admin_backup import admin_backup_bp

app = Flask(__name__)
app.secret_key = 'undac_biblioteca_secreto_seguro_2026'

@app.before_request
def requerir_login_admin():
    # Si la ruta empieza con /admin, no es el login y no es estática, bloquea:
    if request.path.startswith('/admin'):
        if request.path == '/admin/login' or request.path.startswith('/admin/static'):
            return
        if 'admin_user' not in session:
            return redirect(url_for('admin_auth.login'))
            
        # Generar Token CSRF
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(16)

        # Validaci\u00f3n Anti-Hackeo (CSRF Interceptor)
        if request.method in ['POST', 'DELETE'] and not request.path.startswith('/admin/api'):
            token_enviado = request.form.get('csrf_token') or request.args.get('csrf_token') or request.headers.get('X-CSRFToken')
            if not token_enviado or token_enviado != session.get('csrf_token'):
                return "<h1>403 Peligro - Bloqueo CSRF</h1><p>Se ha detectado una petici\u00f3n de servidor cruzado sin firma v\u00e1lida. Accesi\u00f3n denegada.</p>", 403
            
        # Hard-block para Supervisores: Solo pueden ver el Dashboard, Eventos y su perfil
        if session.get('admin_rol') == 'Supervisor':
            rutas_permitidas = [
                '/admin/', '/admin/login', '/admin/logout', '/admin/api/dashboard_data', '/admin/exportar_ingresos_csv',
                '/admin/eventos', '/admin/buscar_eventos', '/admin/guardar_evento', '/admin/importar_invitados_evento'
            ]
            # Permitir rutas dinámicas 
            es_dinamica = (
                request.path.startswith('/admin/api/dashboard') or
                request.path.startswith('/admin/evento_detalle') or 
                request.path.startswith('/admin/eliminar_evento') or
                request.path.startswith('/admin/eventos') # Maneja trailing slash
            )
            if request.path not in rutas_permitidas and not es_dinamica:
                return "<h1>403 Forbidden</h1><p>Tu rol de Supervisor no tiene permisos para visitar este módulo.</p><a href='/admin/'>Volver al Dashboard</a>", 403

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=session.get('csrf_token', ''))

@app.after_request
def log_admin_actions(response):
    if request.path.startswith('/admin') and request.method in ['POST', 'DELETE'] and request.path not in ['/admin/login', '/admin/logout']:
        # Auditar acciones destructivas o de carga en Base de Datos
        usuario = session.get('admin_user', 'SISTEMA')
        accion = request.method + " " + request.path
        detalle = "Form Payload Interceptado"
        ip = request.remote_addr
        
        # Guardado as\u00edncrono/s\u00edncrono en SQL
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO AdminAuditLog (Usuario, Accion, Detalle, IP)
                VALUES (?, ?, ?, ?)
            ''', (usuario, accion, detalle, ip))
            conn.commit()
            conn.close()
        except:
            pass # Falla silenciosa para no interrumpir el flujo del usuario si la BD est\u00e1 lenta
            
    return response

# Registrar los Blueprints (M\u00f3dulos)
app.register_blueprint(ingreso_bp)
app.register_blueprint(visitantes_bp)

app.register_blueprint(admin_dashboard_bp)
app.register_blueprint(admin_reportes_bp)
app.register_blueprint(admin_carnets_bp)
app.register_blueprint(admin_egresados_bp)
app.register_blueprint(admin_personal_bp)
app.register_blueprint(admin_eventos_bp)
app.register_blueprint(admin_tasks_bp)
app.register_blueprint(admin_auth_bp)
app.register_blueprint(admin_accesos_bp)
app.register_blueprint(admin_auditoria_bp)
app.register_blueprint(admin_backup_bp)

if __name__ == '__main__':
    # Entorno de Producción Multihilo WSGI (Waitress)
    import os
    port = int(os.environ.get('PORT', 5000))
    print(f"[*] Iniciando Servidor WSGI Waitress en el puerto {port} con 6 hilos concurrentes...")
    print(f"[*] Accede al sistema aquí: http://127.0.0.1:{port}")
    # Nota para Biblioteca: Para mostrar la IP correcta alla, pueden cambiar el print de arriba por:
    # print(f"[*] Accede al sistema en la red: http://<IP_BIBLIOTECA>:{port}")
    print("[*] (Despliegue Multi-Threading para soportar escaneos en paralelo sin cuellos de botella)")
    from waitress import serve
    # Nota Arquitectónica: Usar host='0.0.0.0' para escuchar en la IP de red automática. 
    # NO poner la IP manual estricta aquí porque si el módem cambia la IP, el sistema se caerá.
    serve(app, host='0.0.0.0', port=port, threads=6)