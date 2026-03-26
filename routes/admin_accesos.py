from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import pyodbc
from werkzeug.security import generate_password_hash
from db import get_db_connection
from utils.cache_manager import global_cache

admin_accesos_bp = Blueprint('admin_accesos', __name__, url_prefix='/admin/accesos')

@admin_accesos_bp.route('/', methods=['GET'])
def index():
    # Solo el SuperAdmin puede ver esta página
    if session.get('admin_rol') != 'SuperAdmin':
        flash('Acceso denegado. No tienes permisos para gestionar administradores.', 'error')
        return redirect(url_for('admin_dashboard.admin_dashboard'))
        
    usuarios = global_cache.get('usuarios_sistema')
    
    if usuarios is None:
        conn = get_db_connection()
        if not conn:
            flash('Error de BD', 'error')
            return redirect(url_for('admin_dashboard.admin_dashboard'))
            
        cursor = conn.cursor()
        cursor.execute("SELECT UsuarioID, Usuario, Email, Rol, SedeAsignada, Activo, FORMAT(CreadoEn, 'dd/MM/yyyy') FROM UsuariosSistema")
        usuarios = cursor.fetchall()
        conn.close()
        
        # Guardar en caché LRU por 60 segundos
        global_cache.set('usuarios_sistema', usuarios)
    
    return render_template('admin_accesos.html', usuarios=usuarios)

@admin_accesos_bp.route('/crear', methods=['POST'])
def crear():
    if session.get('admin_rol') != 'SuperAdmin':
        return redirect(url_for('admin_dashboard.admin_dashboard'))

    usuario = request.form.get('usuario')
    password = request.form.get('password')
    rol = request.form.get('rol') # 'SuperAdmin' o 'Supervisor'
    sede = request.form.get('sede', 'Central')
    
    if not usuario or not password or not rol:
        flash('Por favor completa todos los campos obligatorios.', 'error')
        return redirect(url_for('admin_accesos.index'))
        
    hash_pw = generate_password_hash(password)
    email_generado = f"{usuario}@undac.edu.pe"
    
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_accesos.index'))
    try:
        cursor = conn.cursor()
        # Check if exists
        cursor.execute("SELECT 1 FROM UsuariosSistema WHERE Usuario = ?", (usuario,))
        if cursor.fetchone():
            flash(f'El usuario {usuario} ya existe.', 'error')
            return redirect(url_for('admin_accesos.index'))
            
        cursor.execute('''
            INSERT INTO UsuariosSistema (Usuario, PasswordHash, Email, Rol, Activo, SedeAsignada)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (usuario, hash_pw, email_generado, rol, 1, sede))
        conn.commit()
        flash(f'Usuario {usuario} creado con éxito.', 'success')
        
        # Invalidar caché para forzar recarga la próxima vez
        global_cache.clear('usuarios_sistema')
        
    except Exception as e:
        flash(f'Error al crear usuario: {e}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('admin_accesos.index'))

@admin_accesos_bp.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    if session.get('admin_rol') != 'SuperAdmin':
        return redirect(url_for('admin_dashboard.admin_dashboard'))
        
    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_accesos.index'))
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM UsuariosSistema WHERE UsuarioID = ? AND Usuario != 'admin'", (id,))
        conn.commit()
        flash('Usuario eliminado.', 'success')
        
        # Invalidar caché
        global_cache.clear('usuarios_sistema')
        
    except Exception as e:
        flash(f'Error al eliminar: {e}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('admin_accesos.index'))
