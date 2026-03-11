import pandas as pd
import io
from db import get_db_connection
from utils.validaciones import verificar_dni_global

def buscar_personal_administrativo(query, page, limit=20):
    offset = (page - 1) * limit
    conn = get_db_connection()
    cursor = conn.cursor()
    
    params = []
    where_clause = ""
    
    if query:
        where_clause = "WHERE ApellidosNombres LIKE ? OR DNI LIKE ? OR Oficina LIKE ?"
        p = f"%{query}%"
        params = [p, p, p]
    
    count_sql = f"SELECT COUNT(*) FROM PersonalAdministrativo {where_clause}"
    cursor.execute(count_sql, params)
    total_items = cursor.fetchone()[0]
    total_pages = (total_items + limit - 1) // limit

    data_sql = f"""
    SELECT PersonalID, ApellidosNombres, DNI, Oficina, CorreoPersonal, CorreoInstitucional, Telefono
    FROM PersonalAdministrativo 
    {where_clause}
    ORDER BY ApellidosNombres
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
            'oficina': r[3],
            'correo_personal': r[4] if r[4] else '',
            'correo_inst': r[5] if r[5] else '',
            'telefono': r[6] if r[6] else ''
        })
    
    return {
        'data': resultados,
        'pagination': {
            'page': page,
            'limit': limit,
            'total_items': total_items,
            'total_pages': total_pages
        }
    }

def guardar_personal_administrativo(data):
    personal_id = data.get('id')
    nombre = data.get('nombre')
    dni = data.get('dni')
    oficina = data.get('oficina')
    correo_personal = data.get('correo_personal')
    correo_inst = data.get('correo_inst')
    telefono = data.get('telefono')

    if not all([nombre, dni]):
        return {'status': 'error', 'msg': 'Faltan campos obligatorios (DNI y Nombre)'}

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validación Global
        err_bool, err_msg = verificar_dni_global(dni, ignora_tabla='PersonalAdministrativo', ignora_id=personal_id, cursor=cursor)
        if err_bool:
            return {'status': 'error', 'msg': err_msg}

        if personal_id:
            cursor.execute("""
                UPDATE PersonalAdministrativo 
                SET ApellidosNombres=?, DNI=?, Oficina=?, CorreoPersonal=?, CorreoInstitucional=?, Telefono=?
                WHERE PersonalID=?
            """, (nombre, dni, oficina, correo_personal, correo_inst, telefono, personal_id))
        else:
            cursor.execute("""
                INSERT INTO PersonalAdministrativo (ApellidosNombres, DNI, Oficina, CorreoPersonal, CorreoInstitucional, Telefono)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nombre, dni, oficina, correo_personal, correo_inst, telefono))
            
        conn.commit()
        return {'status': 'success', 'msg': 'Personal Administrativo guardado correctamente'}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        if 'conn' in locals(): conn.close()
        
def borrar_personal_administrativo(id_per):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar registros relacionados
        cursor.execute("DELETE FROM RegistroIngresos WHERE PersonalID = ?", (id_per,))
        
        # Eliminar el personal
        cursor.execute("DELETE FROM PersonalAdministrativo WHERE PersonalID = ?", (id_per,))
        
        conn.commit()
        return {'status': 'success', 'msg': 'Personal eliminado permanentemente.'}
    except Exception as e:
        return {'status': 'error', 'msg': f"No se pudo eliminar: {str(e)}"}
    finally:
        if 'conn' in locals(): conn.close()

def procesar_excel_personal(file):
    if file.filename == '': 
        return {'status': 'error', 'msg': 'Nombre vacío'}

    try:
        df = pd.read_excel(file, dtype={'DNI': str, 'TELEFONO': str})
        df = df.fillna('')
        conn = get_db_connection()
        cursor = conn.cursor()
        errores = []
        contador = 0
        
        for idx, row in df.iterrows():
            fila_num = idx + 2 # +2 por cabecera y base 0
            dni = str(row.get('DNI', '')).strip()
            # Validar si pandas leyó como float y le puso .0
            if dni.endswith('.0'): dni = dni[:-2]

            nombre = row.get('APELLIDOS Y NOMBRES', '').strip()
            oficina = row.get('OFICINA', '').strip()
            c_inst = row.get('CORREO INSTITUCIONAL', '').strip()
            c_per = row.get('CORREO PERSONAL', '').strip()
            telefono = str(row.get('TELEFONO', '')).strip()
            if telefono.endswith('.0'): telefono = telefono[:-2]
            
            if not dni or len(dni) < 5 or not nombre: 
                errores.append(f"Fila {fila_num}: Falta DNI o Nombre.")
                continue

            err_bool, msg_error = verificar_dni_global(dni, ignora_tabla='PersonalAdministrativo', cursor=cursor)
            if err_bool: 
                errores.append(f"Fila {fila_num}: {msg_error}")
                continue 
            
            cursor.execute("SELECT PersonalID FROM PersonalAdministrativo WHERE DNI = ?", (dni,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE PersonalAdministrativo 
                    SET ApellidosNombres=?, Oficina=?, CorreoInstitucional=?, CorreoPersonal=?, Telefono=? 
                    WHERE DNI=?
                """, (nombre, oficina, c_inst, c_per, telefono, dni))
            else:
                cursor.execute("""
                    INSERT INTO PersonalAdministrativo (ApellidosNombres, DNI, Oficina, CorreoInstitucional, CorreoPersonal, Telefono) 
                    VALUES (?,?,?,?,?,?)
                """, (nombre, dni, oficina, c_inst, c_per, telefono))
            contador += 1
            
        conn.commit()
        
        msg = f'Procesados {contador} registros de personal con éxito.'
        if errores:
            detalles = "<br> • ".join(errores[:5])
            if len(errores) > 5: detalles += f"<br> • ... y {len(errores)-5} más."
            msg += f'<div class="mt-2 text-xs text-rose-600 bg-rose-50 p-2 rounded border border-rose-200"><p class="font-bold mb-1">Filas omitidas ({len(errores)}):</p> • {detalles}</div>'
            if contador == 0:
                return {'status': 'error', 'msg': msg}
                
        return {'status': 'success', 'msg': msg}
    except Exception as e:
        return {'status': 'error', 'msg': f"Error al leer archivo: {str(e)}"}
    finally:
        if 'conn' in locals(): conn.close()

