from db import get_db_connection
from datetime import datetime
from utils.validaciones import verificar_dni_global

def _get_global_expiration():
    """Calcula la fecha de vencimiento global según la lógica anual."""
    today = datetime.now().date()
    year = today.year
    # Enero-Marzo (Mes < 4): Vence año anterior
    if today.month < 4:
        return datetime(year - 1, 12, 31).date()
    # Abril-Diciembre: Vence año actual
    return datetime(year, 12, 31).date()

def buscar_alumnos_paginados(query, page, limit):
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
    
    return resultados, total_items, total_pages

def actualizar_vencimiento_individual(alumno_id, nueva_fecha):
    val_fecha = nueva_fecha if nueva_fecha else None
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Alumnos SET FechaVencimientoCarnet = ? WHERE AlumnoID = ?", (val_fecha, alumno_id))
        conn.commit()
        return True, "Success"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def actualizar_vencimiento_masivo(ids, accion):
    año_actual = datetime.now().year
    fecha_val = None

    if accion == 'activar':
        fecha_val = f"{año_actual}-12-31"
    elif accion == 'desactivar':
        fecha_val = f"{año_actual - 1}-12-31"
    elif accion == 'auto':
        fecha_val = None
    else:
        return False, 'Acción no válida'

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(ids))
        sql = f"UPDATE Alumnos SET FechaVencimientoCarnet = ? WHERE AlumnoID IN ({placeholders})"
        
        params = [fecha_val] + ids
        cursor.execute(sql, params)
        conn.commit()
        return True, f"Se actualizaron {len(ids)} carnets."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def procesar_excel_alumnos(df):
    conn = get_db_connection()
    contador = 0
    try:
        cursor = conn.cursor()
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
                continue # Saltar alumnos conflictivos silenciosamente
            # -------------------------

            cursor.execute("SELECT AlumnoID FROM Alumnos WHERE DNI = ?", (dni,))
            if cursor.fetchone():
                cursor.execute("UPDATE Alumnos SET NombreCompleto=?, CodigoMatricula=?, Escuela=?, Semestre=?, Estado=1 WHERE DNI=?", 
                               (nombre, codigo, escuela, semestre, dni))
            else:
                cursor.execute("INSERT INTO Alumnos (NombreCompleto, DNI, CodigoMatricula, Escuela, Semestre) VALUES (?,?,?,?,?)", 
                               (nombre, dni, codigo, escuela, semestre))
            contador += 1
            
        conn.commit()
        return True, f'Procesados {contador} alumnos.'
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()
