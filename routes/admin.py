from flask import Blueprint, render_template, request, jsonify, send_file
import pandas as pd
import io
from datetime import datetime
from db import get_db_connection

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Totales
    cursor.execute("SELECT COUNT(*) FROM RegistroIngresos WHERE CAST(FechaHora AS DATE) = CAST(GETDATE() AS DATE)")
    total_hoy = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM RegistroIngresos WHERE VisitanteID IS NOT NULL AND CAST(FechaHora AS DATE) = CAST(GETDATE() AS DATE)")
    total_visitantes = cursor.fetchone()[0]

    # 2. Por Piso
    cursor.execute("SELECT Piso, COUNT(*) FROM RegistroIngresos WHERE CAST(FechaHora AS DATE) = CAST(GETDATE() AS DATE) GROUP BY Piso")
    pisos_dict = {row[0]: row[1] for row in cursor.fetchall()}

    # 3. Gráfico Horas
    cursor.execute("""
        SELECT DATEPART(HOUR, FechaHora) as Hora, COUNT(*) 
        FROM RegistroIngresos WHERE CAST(FechaHora AS DATE) = CAST(GETDATE() AS DATE) 
        GROUP BY DATEPART(HOUR, FechaHora) ORDER BY Hora
    """)
    datos_horas = cursor.fetchall()
    chart_horas_labels = [f"{row[0]}:00" for row in datos_horas]
    chart_horas_values = [row[1] for row in datos_horas]

    # 4. Top Orígenes (Unificado)
    cursor.execute("""
        SELECT TOP 5 Origen, COUNT(*) as Cantidad FROM (
            SELECT A.Escuela as Origen FROM RegistroIngresos R JOIN Alumnos A ON R.AlumnoID = A.AlumnoID 
            WHERE CAST(R.FechaHora AS DATE) = CAST(GETDATE() AS DATE)
            UNION ALL
            SELECT V.Institucion as Origen FROM RegistroIngresos R JOIN Visitantes V ON R.VisitanteID = V.VisitanteID 
            WHERE CAST(R.FechaHora AS DATE) = CAST(GETDATE() AS DATE)
        ) as T GROUP BY Origen ORDER BY Cantidad DESC
    """)
    datos_escuelas = cursor.fetchall()
    chart_escuelas_labels = [row[0] for row in datos_escuelas]
    chart_escuelas_values = [row[1] for row in datos_escuelas]

    # 5. Tabla Últimos
    cursor.execute("""
        SELECT TOP 10 COALESCE(A.NombreCompleto, V.NombreCompleto), R.Piso, FORMAT(R.FechaHora, 'HH:mm:ss'), 
        COALESCE(A.Escuela, V.Institucion), CASE WHEN R.VisitanteID IS NOT NULL THEN 'Visitante' ELSE 'Alumno' END
        FROM RegistroIngresos R
        LEFT JOIN Alumnos A ON R.AlumnoID = A.AlumnoID
        LEFT JOIN Visitantes V ON R.VisitanteID = V.VisitanteID
        ORDER BY R.FechaHora DESC
    """)
    ultimos = cursor.fetchall()
    conn.close()

    return render_template('admin_dashboard.html', total_hoy=total_hoy, total_visitantes=total_visitantes, 
                           pisos=pisos_dict, ultimos=ultimos, labels_horas=chart_horas_labels, 
                           data_horas=chart_horas_values, labels_escuelas=chart_escuelas_labels, 
                           data_escuelas=chart_escuelas_values)

# --- RUTAS DE EXCEL Y REPORTES ---

@admin_bp.route('/subir_excel', methods=['POST'])
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

@admin_bp.route('/reporte_hoy')
def descargar_reporte():
    conn = get_db_connection()
    sql = """
    SELECT R.RegistroID, A.NombreCompleto, A.DNI, A.Escuela, R.Piso, FORMAT(R.FechaHora, 'HH:mm:ss') as Hora
    FROM RegistroIngresos R JOIN Alumnos A ON R.AlumnoID = A.AlumnoID
    WHERE CAST(R.FechaHora AS DATE) = CAST(GETDATE() AS DATE) ORDER BY R.FechaHora DESC
    """
    df = pd.read_sql(sql, conn)
    conn.close()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(output, download_name=f"Reporte_{datetime.now().date()}.xlsx", as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# --- REPORTES ADICIONALES ---

@admin_bp.route('/reporte_rango')
def reporte_rango():
    # Recibimos las fechas desde la URL (ej: ?inicio=2026-02-01&fin=2026-02-05)
    fecha_inicio = request.args.get('inicio')
    fecha_fin = request.args.get('fin')

    if not fecha_inicio or not fecha_fin:
        return "Error: Debes seleccionar ambas fechas", 400

    conn = get_db_connection()
    
    # Consulta SQL filtrando por rango de fechas
    sql = """
    SELECT 
        R.RegistroID as ID,
        COALESCE(A.NombreCompleto, V.NombreCompleto) as Persona,
        COALESCE(A.DNI, V.DNI) as DNI,
        COALESCE(A.Escuela, V.Institucion) as Origen,
        CASE WHEN R.VisitanteID IS NOT NULL THEN 'VISITANTE' ELSE 'ALUMNO' END as Tipo,
        R.Piso as Piso_Acceso,
        R.Turno,
        FORMAT(R.FechaHora, 'HH:mm:ss') as Hora,
        FORMAT(R.FechaHora, 'dd/MM/yyyy') as Fecha
    FROM RegistroIngresos R
    LEFT JOIN Alumnos A ON R.AlumnoID = A.AlumnoID
    LEFT JOIN Visitantes V ON R.VisitanteID = V.VisitanteID
    WHERE CAST(R.FechaHora AS DATE) >= ? 
    AND CAST(R.FechaHora AS DATE) <= ?
    ORDER BY R.FechaHora DESC
    """
    
    # Ejecutamos la consulta enviando las fechas
    # IMPORTANTE: Asegúrate de tener instalado openpyxl (pip install openpyxl)
    df = pd.read_sql(sql, conn, params=(fecha_inicio, fecha_fin))
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte_Rango')
    output.seek(0)

    return send_file(output, 
                    download_name=f"Reporte_{fecha_inicio}_al_{fecha_fin}.xlsx", 
                    as_attachment=True,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# --- HELPER FUNCTIONS ---

def _get_global_expiration():
    """Calcula la fecha de vencimiento global según la lógica anual."""
    today = datetime.now().date()
    year = today.year
    # Enero-Marzo (Mes < 4): Vence año anterior
    if today.month < 4:
        return datetime(year - 1, 12, 31).date()
    # Abril-Diciembre: Vence año actual
    return datetime(year, 12, 31).date()

# --- GESTIÓN DE CARNETS ---

@admin_bp.route('/carnets')
def gestion_carnets():
    return render_template('admin_carnets.html')

@admin_bp.route('/buscar_alumno')
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
    # SQL Server 2012+ usa OFFSET ... FETCH NEXT
    # Asegúrate de tener ORDER BY siempre
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

@admin_bp.route('/actualizar_carnet', methods=['POST'])
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

@admin_bp.route('/actualizar_carnet_masivo', methods=['POST'])
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