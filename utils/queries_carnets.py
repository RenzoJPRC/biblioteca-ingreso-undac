from db import get_db_connection
from datetime import datetime
from utils.validaciones import verificar_dni_global, formatear_nombre_estetico
import pandas as pd
import io
from utils.task_manager import update_task_progress, finish_task

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

def actualizar_vencimiento_global(accion):
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
        sql = "UPDATE Alumnos SET FechaVencimientoCarnet = ?"
        cursor.execute(sql, (fecha_val,))
        conn.commit()
        return True, "Se actualizó el estado de todos los alumnos en la base de datos."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def procesar_excel_alumnos_async(file_bytes, task_id):
    conn = get_db_connection()
    contador = 0
    errores = []
    try:
        update_task_progress(task_id, 0, msg="Leyendo archivo Excel de Alumnos...")
        
        # Lectura sin tipo rígido
        df = pd.read_excel(io.BytesIO(file_bytes))
        df = df.fillna('')
        df.columns = df.columns.astype(str).str.strip().str.upper()
        
        total_filas = len(df)
        update_task_progress(task_id, 0, total=total_filas, msg=f"Validando cabeceras y preparando {total_filas} registros...")
        
        cursor = conn.cursor()
        
        for index, row in df.iterrows():
            num_fila = index + 2
            
            # Limpieza exhaustiva
            dni = str(row.get('DNI', '')).strip()
            if dni.endswith('.0'): dni = dni[:-2]
            
            # Buscar variaciones comunes de cabeceras EN MAYÚSCULAS Y CON/SIN S
            nombre_raw = str(row.get('APELLIDOS Y NOMBRE', 
                         row.get('APELLIDOS Y NOMBRES',
                         row.get('NOMBRE COMPLETO', 
                         row.get('NOMBRES Y APELLIDOS', ''))))).strip()
            nombre = formatear_nombre_estetico(nombre_raw)
            
            codigo = str(row.get('CÓDIGO', 
                     row.get('CODIGO', row.get('CODIGO DE MATRICULA', '')))).strip()
            if codigo.endswith('.0'): codigo = codigo[:-2]
            
            escuela = str(row.get('ESCUELA PROFESIONAL', row.get('ESCUELA', ''))).strip()
            semestre = str(row.get('SEMESTRE', '')).strip()
            if semestre.endswith('.0'): semestre = semestre[:-2]
            
            if not nombre: 
                errores.append(f"Fila {num_fila}: Celda de nombre vacía.")
                continue

            # --- VALIDACIÓN GLOBAL ---
            skip_row = False
            if dni not in ['0', '', '0.0'] and len(dni) >= 5:
                err_bool, msg_valid = verificar_dni_global(dni, ignora_tabla='Alumnos', cursor=cursor)
                if err_bool: 
                    errores.append(f"Fila {num_fila}: {msg_valid} - DNI {dni}")
                    skip_row = True
            elif not codigo:
                # Si ni DNI válido ni código existe, no podemos identificar
                errores.append(f"Fila {num_fila}: DNI y Código ausentes o inválidos.")
                skip_row = True
                
            if not skip_row:
                # Buscar por código primero
                cursor.execute("SELECT AlumnoID FROM Alumnos WHERE CodigoMatricula = ? AND CodigoMatricula != ''", (codigo,))
                existe = cursor.fetchone()
                
                # Si no existe por código, buscar por DNI
                if not existe and dni not in ['0', '', '0.0'] and len(dni) >= 5:
                    cursor.execute("SELECT AlumnoID FROM Alumnos WHERE DNI = ?", (dni,))
                    existe = cursor.fetchone()

                if existe:
                    cursor.execute("UPDATE Alumnos SET NombreCompleto=?, CodigoMatricula=?, Escuela=?, Semestre=?, Estado=1 WHERE AlumnoID=?", 
                                   (nombre, codigo, escuela, semestre, existe[0]))
                else:
                    cursor.execute("INSERT INTO Alumnos (NombreCompleto, DNI, CodigoMatricula, Escuela, Semestre, Estado) VALUES (?,?,?,?,?,1)", 
                                   (nombre, dni, codigo, escuela, semestre))
                contador += 1
                
                if contador % 500 == 0:
                    conn.commit()
            
            # Reporte cada 50 filas
            if index % 50 == 0:
                print(f"-> Procesados {index} alumnos...")
                update_task_progress(task_id, index, total=total_filas, msg=f"Guardando en BD: {index} de {total_filas}...")
                
        conn.commit()
        
        msg = f'Procesados {contador} de {total_filas} alumnos con éxito.'
        if errores:
            detalles = "<br> • ".join(errores[:5])
            if len(errores) > 5: detalles += f"<br> • ... y {len(errores)-5} más."
            msg += f'<div class="mt-2 text-xs text-rose-600 bg-rose-50 p-2 rounded border border-rose-200"><p class="font-bold mb-1">Filas omitidas ({len(errores)}):</p> • {detalles}</div>'
            if contador == 0:
                finish_task(task_id, success=False, msg=msg)
                return
                
        finish_task(task_id, success=True, msg=msg)
    except Exception as e:
        finish_task(task_id, success=False, msg=f"Error fatal: {str(e)}")
    finally:
        conn.close()
