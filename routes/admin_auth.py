from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import pyodbc
from werkzeug.security import check_password_hash
from db import get_db_connection
import time
import json

admin_auth_bp = Blueprint('admin_auth', __name__, url_prefix='/admin')

# Rate Limiter Global (Memoria de Sesiones)
login_attempts = {}
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 900 # 15 minutos

@admin_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_user' in session:
        return redirect(url_for('admin_dashboard.admin_dashboard'))
        
    client_ip = request.remote_addr or '0.0.0.0'
    estado_ip = login_attempts.get(client_ip, {'count': 0, 'locked_until': 0})
    
    if estado_ip['locked_until'] > time.time():
        minutos_restantes = int((estado_ip['locked_until'] - time.time()) / 60)
        flash(f'¡Seguridad! Sistema bloqueado por demasiados intentos fallidos. Intente en {minutos_restantes} minutos.', 'error')
        return render_template('admin_login.html')

    if request.method == 'POST':
        usuario = request.form.get('usuario')
        password = request.form.get('password')

        if not usuario or not password:
            flash('Por favor ingrese usuario y contraseña.', 'error')
            return render_template('admin_login.html')

        conn = get_db_connection()
        if not conn:
            flash('Error de conexión a la base de datos.', 'error')
            return render_template('admin_login.html')

        cursor = conn.cursor()
        cursor.execute("SELECT Usuario, PasswordHash, Rol, Activo, SedeAsignada FROM UsuariosSistema WHERE Usuario = ?", (usuario,))
        row = cursor.fetchone()
        conn.close()

        if row and check_password_hash(row.PasswordHash, password):
            if not row.Activo:
                flash('Esta cuenta está desactivada.', 'error')
            else:
                # Login Correcto, purgar intentos
                login_attempts.pop(client_ip, None)
                    
                session['admin_user'] = row.Usuario
                session['admin_rol'] = row.Rol
                session['admin_sede'] = row.SedeAsignada or 'Central'
                return redirect(url_for('admin_dashboard.admin_dashboard'))
        else:
            # Login Incorrecto
            login_attempts[client_ip] = estado_ip
            login_attempts[client_ip]['count'] += 1
            
            if login_attempts[client_ip]['count'] >= MAX_INTENTOS:
                login_attempts[client_ip]['locked_until'] = int(time.time()) + BLOQUEO_SEGUNDOS
                
                # Inyección a Auditoría de Seguridad (El Gran Ojo)
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        payload = json.dumps({"Target": usuario, "Alerta": "Exceso de Ataques", "Bloqueo": "15 Minutos"})
                        cursor.execute("""
                            INSERT INTO AdminAuditLog (Usuario, Accion, Detalle, IP)
                            VALUES (?, ?, ?, ?)
                        """, ('Sistema de Defensa', 'SEC_BRUTEFORCE', payload, client_ip))
                        conn.commit()
                    except:
                        pass
                    finally:
                        conn.close()
                
                flash('¡Ataque detectado! IP bloqueada temporalmente por seguridad.', 'error')
            else:
                intentos = MAX_INTENTOS - login_attempts[client_ip]['count']
                flash(f'Usuario o contraseña incorrectos. Quedan {intentos} intento(s) antes del bloqueo.', 'error')

    return render_template('admin_login.html')

@admin_auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_auth.login'))
