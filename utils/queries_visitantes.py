import pandas as pd
import io
from db import get_db_connection
from utils.validaciones import verificar_dni_global, formatear_nombre_estetico
from utils.task_manager import update_task_progress, finish_task

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

def procesar_excel_visitantes_async(file_bytes, task_id):
    conn = get_db_connection()
    errores = []
    contador = 0
    
    try:
        update_task_progress(task_id, 0, msg="Leyendo archivo Excel de Visitantes...")
        df = pd.read_excel(io.BytesIO(file_bytes))
        df = df.fillna('')
        df.columns = df.columns.astype(str).str.strip()
        
        total_filas = len(df)
        update_task_progress(task_id, 0, total=total_filas, msg=f"Validando cabeceras y preparando {total_filas} registros...")
        
        cursor = conn.cursor()
        
        for idx, row in df.iterrows():
            fila_num = idx + 2
            
            dni = str(row.get('DNI', '')).strip()
            if dni.endswith('.0'): dni = dni[:-2]
            
            nombre_raw = str(row.get('Nombre Completo', row.get('NOMBRE COMPLETO', ''))).strip()
            nombre = formatear_nombre_estetico(nombre_raw)
            
            inst = str(row.get('Institución', row.get('INSTITUCION', 'Sin Institución'))).strip()
            if not inst: inst = 'Sin Institución'
            
            correo = str(row.get('Correo', row.get('CORREO', ''))).strip()
            
            if not nombre:
                errores.append(f"Fila {fila_num}: Celda de nombre vacía.")
                continue

            # --- VALIDACIÓN GLOBAL ---
            skip_row = False
            if dni not in ['0', '', '0.0'] and len(dni) >= 5:
                err_bool, msg_error = verificar_dni_global(dni, ignora_tabla='Visitantes', cursor=cursor)
                if err_bool: 
                    errores.append(f"Fila {fila_num}: {msg_error}")
                    skip_row = True
            else:
                errores.append(f"Fila {fila_num}: Falta DNI válido.")
                skip_row = True
                
            if not skip_row:
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
                
                if contador % 500 == 0:
                    conn.commit()
                
            if idx % 50 == 0:
                print(f"-> Procesados {idx} visitantes...")
                update_task_progress(task_id, idx, total=total_filas, msg=f"Guardando en BD: {idx} de {total_filas}...")
            
        conn.commit()
        msg = f'Procesados {contador} de {total_filas} visitantes con éxito.'
        if errores:
            detalles = "<br> • ".join(errores[:5])
            if len(errores) > 5: detalles += f"<br> • ... y {len(errores)-5} más."
            msg += f'<div class="mt-2 text-xs text-rose-600 bg-rose-50 p-2 rounded border border-rose-200"><p class="font-bold mb-1">Filas omitidas ({len(errores)}):</p> • {detalles}</div>'
            if contador == 0:
                finish_task(task_id, success=False, msg=msg)
                return
                
        finish_task(task_id, success=True, msg=msg)
        
    except Exception as e:
        finish_task(task_id, success=False, msg=f"Error fatal al procesar: {str(e)}")
    finally:
        conn.close()
