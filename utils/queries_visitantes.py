import pandas as pd
import io
from db import get_db_connection
from utils.validaciones import verificar_dni_global

def obtener_todos_visitantes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT VisitanteID, NombreCompleto, DNI, Institucion, Correo FROM Visitantes ORDER BY NombreCompleto ASC")
    lista = cursor.fetchall()
    conn.close()
    return lista

def registrar_nuevo_visitante(data):
    dni = data.get('dni')
    inst = data.get('institucion') or "Sin Institución"
    
    # Validación global
    err_bool, err_msg = verificar_dni_global(dni, ignora_tabla='Visitantes')
    if err_bool:
        return {'status': 'error', 'msg': err_msg}

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Visitantes (NombreCompleto, DNI, Correo, Institucion) VALUES (?,?,?,?)",
                       (data.get('nombre'), dni, data.get('correo'), inst))
        conn.commit()
        return {'status': 'success', 'msg': 'Guardado'}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        if 'conn' in locals():
            conn.close()

def actualizar_visitante(data):
    vis_id = data.get('id')
    dni = data.get('dni')
    
    err_bool, err_msg = verificar_dni_global(dni, ignora_tabla='Visitantes', ignora_id=vis_id)
    if err_bool: return {'status': 'error', 'msg': err_msg}

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Visitantes 
            SET NombreCompleto=?, DNI=?, Institucion=?, Correo=? 
            WHERE VisitanteID=?
        """, (data.get('nombre'), dni, data.get('institucion') or 'Sin Institución', data.get('correo'), vis_id))
        
        conn.commit()
        return {'status': 'success', 'msg': 'Visitante actualizado.'}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        if 'conn' in locals(): conn.close()

def borrar_visitante(id_vis):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 1. Eliminamos el historial de ingresos para mantener integridad relacional
        cursor.execute("DELETE FROM RegistroIngresos WHERE VisitanteID = ?", (id_vis,))
        # 2. Eliminamos visitante
        cursor.execute("DELETE FROM Visitantes WHERE VisitanteID = ?", (id_vis,))
        
        conn.commit()
        return {'status': 'success', 'msg': 'Visitante eliminado permanentemente.'}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        if 'conn' in locals(): conn.close()

def procesar_excel_visitantes(file):
    if file.filename == '': 
        return {'status': 'error', 'msg': 'Nombre vacío'}

    try:
        df = pd.read_excel(file, dtype={'DNI': str})
        df = df.fillna('')
        conn = get_db_connection()
        cursor = conn.cursor()
        contador = 0
        
        for _, row in df.iterrows():
            dni = str(row.get('DNI', '')).strip()
            nombre = row.get('NOMBRE COMPLETO', '').strip()
            inst = row.get('INSTITUCION', 'Sin Institución')
            correo = row.get('CORREO', '')
            
            if not dni or len(dni) < 5 or not nombre: continue

            err_bool, _ = verificar_dni_global(dni, cursor=cursor)
            if err_bool: continue 
            
            cursor.execute("SELECT VisitanteID FROM Visitantes WHERE DNI = ?", (dni,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE Visitantes SET NombreCompleto=?, Institucion=?, Correo=? WHERE DNI=?
                """, (nombre, inst, correo, dni))
            else:
                cursor.execute("""
                    INSERT INTO Visitantes (NombreCompleto, DNI, Institucion, Correo) VALUES (?,?,?,?)
                """, (nombre, dni, inst, correo))
            contador += 1
            
        conn.commit()
        return {'status': 'success', 'msg': f'Procesados {contador} visitantes con éxito.'}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        if 'conn' in locals(): conn.close()
