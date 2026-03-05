from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import pandas as pd
import sys
import os
from db import get_db_connection

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.validaciones import verificar_dni_global

admin_carnets_bp = Blueprint('admin_carnets', __name__, url_prefix='/admin')

def _get_global_expiration():
    """Calcula la fecha de vencimiento global según la lógica anual."""
    today = datetime.now().date()
    year = today.year
    # Enero-Marzo (Mes < 4): Vence año anterior
    if today.month < 4:
        return datetime(year - 1, 12, 31).date()
    # Abril-Diciembre: Vence año actual
    return datetime(year, 12, 31).date()

@admin_carnets_bp.route('/carnets')
def gestion_carnets():
    return render_template('admin_carnets.html')

@admin_carnets_bp.route('/buscar_alumno')
def buscar_alumno():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    limit = 20 # Elementos por página
    offset = (page - 1) * limit
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    params = []
    where_clause = ""
    
    if query:
        where_clause = "WHERE NombreCompleto LIKE ? OR DNI LIKE ? OR CodigoMatricula LIKE ?"
        p = f"%{query}%"
        params = [p, p, p]
    
    # 1. Obtener Total de registros
    count_sql = f"SELECT COUNT(*) FROM Alumnos {where_clause}"
    cursor.execute(count_sql, params)
    total_items = cursor.fetchone()[0]
    total_pages = (total_items + limit - 1) // limit

    # 2. Obtener Datos paginados
    data_sql = f"""
    SELECT AlumnoID, NombreCompleto, DNI, CodigoMatricula, Escuela, FechaVencimientoCarnet
    FROM Alumnos 
    {where_clause}
    ORDER BY NombreCompleto
    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """
    
    # Agregar params de paginación al final
    full_params = params + [offset, limit]
    
    cursor.execute(data_sql, full_params)
    rows = cursor.fetchall()
    conn.close()
    
    resultados = []
    today = datetime.now().date()
    global_expiration = _get_global_expiration()

    for r in rows:
        fecha_manual = r[5] # Date object or None
        
        # Calcular fecha efectiva
        fecha_efectiva = fecha_manual if fecha_manual else global_expiration
        
        # Determinar estado
        estado = 'ACTIVO' if fecha_efectiva >= today else 'VENCIDO'

        resultados.append({
            'id': r[0],
            'nombre': r[1],
            'dni': r[2],
            'codigo': r[3],
            'escuela': r[4],
            'fecha_manual': fecha_manual.strftime('%Y-%m-%d') if fecha_manual else None,
            'fecha_efectiva': fecha_efectiva.strftime('%d/%m/%Y'),
            'estado': estado
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

@admin_carnets_bp.route('/actualizar_carnet', methods=['POST'])
def actualizar_carnet():
    data = request.json
    alumno_id = data.get('id')
    nueva_fecha = data.get('fecha') # String 'YYYY-MM-DD' o vacío

    if not alumno_id: return jsonify({'status': 'error', 'msg': 'Faltan datos'})

    # Si nueva_fecha es vacío, se guarda NULL (Auto)
    val_fecha = nueva_fecha if nueva_fecha else None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Alumnos SET FechaVencimientoCarnet = ? WHERE AlumnoID = ?", (val_fecha, alumno_id))
        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

@admin_carnets_bp.route('/actualizar_carnet_masivo', methods=['POST'])
def actualizar_carnet_masivo():
    data = request.json
    ids = data.get('ids', [])
    accion = data.get('accion') # 'activar' | 'desactivar' | 'auto'

    if not ids: return jsonify({'status': 'error', 'msg': 'No seleccionaste ningun alumno'})

    año_actual = datetime.now().year
    fecha_val = None

    if accion == 'activar':
        fecha_val = f"{año_actual}-12-31"
    elif accion == 'desactivar':
        fecha_val = f"{año_actual - 1}-12-31"
    elif accion == 'auto':
        fecha_val = None
    else:
        return jsonify({'status': 'error', 'msg': 'Acción no válida'})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(ids))
        sql = f"UPDATE Alumnos SET FechaVencimientoCarnet = ? WHERE AlumnoID IN ({placeholders})"
        
        params = [fecha_val] + ids
        cursor.execute(sql, params)
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'msg': f'Se actualizaron {len(ids)} carnets.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

@admin_carnets_bp.route('/subir_excel', methods=['POST'])
def subir_excel():
    if 'archivo_excel' not in request.files: return jsonify({'status': 'error', 'msg': 'Falta archivo'})
    file = request.files['archivo_excel']
    if file.filename == '': return jsonify({'status': 'error', 'msg': 'Nombre vacío'})

    try:
        df = pd.read_excel(file, dtype={'DNI': str})
        conn = get_db_connection()
        cursor = conn.cursor()
        contador = 0
        
        for _, row in df.iterrows():
            dni = str(row.get('DNI', '')).strip()
            nombre = row.get('APELLIDOS Y NOMBRE', '')
            codigo = str(row.get('CODIGO DE MATRICULA', '')).strip()
            escuela = row.get('ESCUELA', '')
            semestre = row.get('SEMESTRE', '')
            
            if not dni or len(dni) < 5: continue

            # --- VALIDACIÓN GLOBAL ---
            err_bool, _ = verificar_dni_global(dni, ignora_tabla='Alumnos')
            if err_bool: 
                continue # Saltar alumnos conflictivos silenciosamente (quizás es visitante o egresado)
            # -------------------------

            # Lógica Upsert (Insertar o Actualizar)
            cursor.execute("SELECT AlumnoID FROM Alumnos WHERE DNI = ?", (dni,))
            if cursor.fetchone():
                cursor.execute("UPDATE Alumnos SET NombreCompleto=?, CodigoMatricula=?, Escuela=?, Semestre=?, Estado=1 WHERE DNI=?", 
                               (nombre, codigo, escuela, semestre, dni))
            else:
                cursor.execute("INSERT INTO Alumnos (NombreCompleto, DNI, CodigoMatricula, Escuela, Semestre) VALUES (?,?,?,?,?)", 
                               (nombre, dni, codigo, escuela, semestre))
            contador += 1
            
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'msg': f'Procesados {contador} alumnos.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})
