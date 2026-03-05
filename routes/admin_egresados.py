from flask import Blueprint, render_template, request, jsonify
import pandas as pd
from db import get_db_connection
import sys
import os

# Agregamos la ruta base para que Python pueda encontrar 'utils'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.validaciones import verificar_dni_global

admin_egresados_bp = Blueprint('admin_egresados', __name__, url_prefix='/admin')

@admin_egresados_bp.route('/egresados')
def gestion_egresados():
    return render_template('admin_egresados.html')

@admin_egresados_bp.route('/buscar_egresado')
def buscar_egresado():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    limit = 20
    offset = (page - 1) * limit
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    params = []
    where_clause = ""
    
    if query:
        where_clause = "WHERE NombreCompleto LIKE ? OR DNI LIKE ? OR CodigoMatricula LIKE ?"
        p = f"%{query}%"
        params = [p, p, p]
    
    count_sql = f"SELECT COUNT(*) FROM Egresados {where_clause}"
    cursor.execute(count_sql, params)
    total_items = cursor.fetchone()[0]
    total_pages = (total_items + limit - 1) // limit

    data_sql = f"""
    SELECT EgresadoID, NombreCompleto, DNI, CodigoMatricula, Facultad, EscuelaProfesional, CorreoPersonal, CorreoInstitucional, Celular, Estado
    FROM Egresados 
    {where_clause}
    ORDER BY NombreCompleto
    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    
    full_params = params + [offset, limit]
    cursor.execute(data_sql, full_params)
    rows = cursor.fetchall()
    conn.close()
    
    resultados = []
    for r in rows:
        resultados.append({
            'id': r[0],
            'nombre': r[1],
            'dni': r[2],
            'codigo': r[3],
            'facultad': r[4],
            'escuela': r[5],
            'correo_personal': r[6] if r[6] else '',
            'correo_inst': r[7] if r[7] else '',
            'celular': r[8] if r[8] else '',
            'estado': 'ACTIVO' if r[9] else 'INACTIVO'
        })
    
    return jsonify({
        'data': resultados,
        'pagination': {
            'page': page,
            'limit': limit,
            'total_items': total_items,
            'total_pages': total_pages
        }
    })

@admin_egresados_bp.route('/guardar_egresado', methods=['POST'])
def guardar_egresado():
    data = request.json
    egresado_id = data.get('id')
    nombre = data.get('nombre')
    dni = data.get('dni')
    codigo = data.get('codigo')
    facultad = data.get('facultad')
    escuela = data.get('escuela')
    correo_personal = data.get('correo_personal')
    correo_inst = data.get('correo_inst')
    celular = data.get('celular')

    if not all([nombre, dni, codigo, facultad, escuela]):
        return jsonify({'status': 'error', 'msg': 'Faltan campos obligatorios'})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # --- VALIDACIÓN GLOBAL DE DNI ---
        err_bool, err_msg = verificar_dni_global(dni, ignora_tabla='Egresados', ignora_id=egresado_id)
        if err_bool:
            return jsonify({'status': 'error', 'msg': err_msg})
        # --------------------------------

        if egresado_id:
            cursor.execute("""
                UPDATE Egresados 
                SET NombreCompleto=?, DNI=?, CodigoMatricula=?, Facultad=?, EscuelaProfesional=?, CorreoPersonal=?, CorreoInstitucional=?, Celular=?
                WHERE EgresadoID=?
            """, (nombre, dni, codigo, facultad, escuela, correo_personal, correo_inst, celular, egresado_id))
        else:
            # Ya verifiqué duplicados con verificar_dni_global, solo inserto
            cursor.execute("""
                INSERT INTO Egresados (NombreCompleto, DNI, CodigoMatricula, Facultad, EscuelaProfesional, CorreoPersonal, CorreoInstitucional, Celular, Estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (nombre, dni, codigo, facultad, escuela, correo_personal, correo_inst, celular))
            
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'msg': 'Egresado guardado correctamente'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

@admin_egresados_bp.route('/subir_excel_egresados', methods=['POST'])
def subir_excel_egresados():
    if 'archivo_excel' not in request.files: return jsonify({'status': 'error', 'msg': 'Falta archivo'})
    file = request.files['archivo_excel']
    if file.filename == '': return jsonify({'status': 'error', 'msg': 'Nombre vacío'})

    try:
        df = pd.read_excel(file, dtype={'DNI': str, 'CELULAR': str, 'CODIGO DE MATRICULA': str})
        df = df.fillna('')
        conn = get_db_connection()
        cursor = conn.cursor()
        contador = 0
        
        for _, row in df.iterrows():
            dni = str(row.get('DNI', '')).strip()
            nombre = row.get('APELLIDOS Y NOMBRE', '')
            codigo = str(row.get('CODIGO DE MATRICULA', '')).strip()
            facultad = row.get('FACULTAD', '')
            escuela = row.get('ESCUELA', '')
            c_personal = row.get('CORREO PERSONAL', '')
            c_institucional = row.get('CORREO INSTITUCIONAL', '')
            celular = row.get('CELULAR', '')
            
            if not dni or len(dni) < 5 or not nombre: continue

            cursor.execute("SELECT EgresadoID FROM Egresados WHERE DNI = ?", (dni,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE Egresados 
                    SET NombreCompleto=?, CodigoMatricula=?, Facultad=?, EscuelaProfesional=?, CorreoPersonal=?, CorreoInstitucional=?, Celular=?, Estado=1 
                    WHERE DNI=?
                """, (nombre, codigo, facultad, escuela, c_personal, c_institucional, celular, dni))
            else:
                cursor.execute("""
                    INSERT INTO Egresados (NombreCompleto, DNI, CodigoMatricula, Facultad, EscuelaProfesional, CorreoPersonal, CorreoInstitucional, Celular, Estado) 
                    VALUES (?,?,?,?,?,?,?,?,1)
                """, (nombre, dni, codigo, facultad, escuela, c_personal, c_institucional, celular))
            contador += 1
            
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'msg': f'Procesados {contador} egresados.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

@admin_egresados_bp.route('/eliminar_egresado/<int:id>', methods=['DELETE'])
def eliminar_egresado(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Primero necesitamos eliminar los registros de ingreso que tenga este egresado
        # para no violar la llave foránea (Integridad Referencial)
        cursor.execute("DELETE FROM RegistroIngresos WHERE EgresadoID = ?", (id,))
        
        # Luego eliminamos al egresado
        cursor.execute("DELETE FROM Egresados WHERE EgresadoID = ?", (id,))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'msg': 'Egresado eliminado permanentemente.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': f"No se pudo eliminar: {str(e)}"})
