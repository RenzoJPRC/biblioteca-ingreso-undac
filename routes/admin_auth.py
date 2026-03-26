from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import pyodbc
from werkzeug.security import check_password_hash
from db import get_db_connection

admin_auth_bp = Blueprint('admin_auth', __name__, url_prefix='/admin')

@admin_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'admin_user' in session:
        return redirect(url_for('admin_dashboard.admin_dashboard'))

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
                session['admin_user'] = row.Usuario
                session['admin_rol'] = row.Rol
                session['admin_sede'] = row.SedeAsignada or 'Central'
                return redirect(url_for('admin_dashboard.admin_dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')

    return render_template('admin_login.html')

@admin_auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin_auth.login'))
