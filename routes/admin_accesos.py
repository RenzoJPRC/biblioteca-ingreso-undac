from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
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

@admin_accesos_bp.route('/editar', methods=['POST'])
def editar():
    # El usuario actual (quien edita) debe ser SuperAdmin
    if session.get('admin_rol') != 'SuperAdmin':
        flash('Acceso denegado. Se requiere nivel SuperAdmin.', 'error')
        return redirect(url_for('admin_dashboard.admin_dashboard'))

    admin_username = session.get('admin_user')
    password_admin = request.form.get('password_admin')
    
    id_usuario_target = request.form.get('id_usuario')
    nuevo_usuario = request.form.get('nuevo_usuario', '').strip()
    nuevo_correo = request.form.get('nuevo_correo', '').strip()
    nueva_password = request.form.get('nueva_password', '').strip()

    if not password_admin or not id_usuario_target:
        flash('Faltan credenciales de verificación para editar el perfil.', 'error')
        return redirect(url_for('admin_accesos.index'))

    conn = get_db_connection()
    if not conn: return redirect(url_for('admin_accesos.index'))

    try:
        cursor = conn.cursor()
        
        # 1. Verificar la identidad del SuperAdmin que está ejecutando la acción
        cursor.execute("SELECT PasswordHash FROM UsuariosSistema WHERE Usuario = ?", (admin_username,))
        row_admin = cursor.fetchone()
        
        if not row_admin or not check_password_hash(row_admin[0], password_admin):
            flash('La contraseña actual es incorrecta. Operación abortada por seguridad.', 'error')
            return redirect(url_for('admin_accesos.index'))

        # 2. Proceder con la actualización si los campos no están vacíos
        updates = []
        params = []
        
        if nuevo_usuario:
            updates.append("Usuario = ?")
            params.append(nuevo_usuario)
            
        if nuevo_correo:
            updates.append("Email = ?")
            params.append(nuevo_correo)
            
        if nueva_password:
            updates.append("PasswordHash = ?")
            params.append(generate_password_hash(nueva_password))
            
        if updates:
            sql = f"UPDATE UsuariosSistema SET {', '.join(updates)} WHERE UsuarioID = ?"
            params.append(id_usuario_target)
            
            cursor.execute(sql, tuple(params))
            conn.commit()
            
            global_cache.clear('usuarios_sistema')
            flash('Gestor actualizado con éxito.', 'success')
        else:
            flash('No detectamos ningún cambio para aplicar.', 'warning')

    except Exception as e:
        flash(f'Error de sistema al editar: {e}', 'error')
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
