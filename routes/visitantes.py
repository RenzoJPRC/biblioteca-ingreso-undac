from flask import Blueprint, render_template, request, jsonify, send_file
import pandas as pd
import io
import sys
import os
from db import get_db_connection

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.validaciones import verificar_dni_global

visitantes_bp = Blueprint('visitantes', __name__, url_prefix='/admin')

@visitantes_bp.route('/visitantes')
def admin_visitantes_page():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT VisitanteID, NombreCompleto, DNI, Institucion, Correo FROM Visitantes ORDER BY NombreCompleto ASC")
    lista = cursor.fetchall()
    conn.close()
    return render_template('admin_visitantes.html', visitantes=lista)

@visitantes_bp.route('/agregar_visitante', methods=['POST'])
def agregar_visitante():
    data = request.json
    dni = data.get('dni')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        inst = data.get('institucion') or "Sin Institución"
        
        # --- VALIDACION GLOBAL DE DNI ---
        err_bool, err_msg = verificar_dni_global(dni, ignora_tabla='Visitantes')
        if err_bool:
            return jsonify({'status': 'error', 'msg': err_msg})
        # --------------------------------

        cursor.execute("INSERT INTO Visitantes (NombreCompleto, DNI, Correo, Institucion) VALUES (?,?,?,?)",
                       (data.get('nombre'), dni, data.get('correo'), inst))
        conn.commit()
        return jsonify({'status': 'success', 'msg': 'Guardado'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})
    finally:
        if 'conn' in locals():
            conn.close()

@visitantes_bp.route('/editar_visitante', methods=['POST'])
def editar_visitante():
    data = request.json
    vis_id = data.get('id')
    dni = data.get('dni')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validación Global
        err_bool, err_msg = verificar_dni_global(dni, ignora_tabla='Visitantes', ignora_id=vis_id)
        if err_bool: return jsonify({'status': 'error', 'msg': err_msg})
        
        cursor.execute("""
            UPDATE Visitantes 
            SET NombreCompleto=?, DNI=?, Institucion=?, Correo=? 
            WHERE VisitanteID=?
        """, (data.get('nombre'), dni, data.get('institucion') or 'Sin Institución', data.get('correo'), vis_id))
        
        conn.commit()
        return jsonify({'status': 'success', 'msg': 'Visitante actualizado.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})
    finally:
        if 'conn' in locals(): conn.close()

@visitantes_bp.route('/subir_excel_visitantes', methods=['POST'])
def subir_excel_visitantes():
    if 'archivo_excel_vis' not in request.files: return jsonify({'status': 'error', 'msg': 'Falta archivo'})
    file = request.files['archivo_excel_vis']
    if file.filename == '': return jsonify({'status': 'error', 'msg': 'Nombre vacío'})

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

            # Aqui podríamos saltarnos registrar duplicados
            err_bool, _ = verificar_dni_global(dni)
            if err_bool: continue # Saltamos este registro si colisiona globalmente
            
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
        return jsonify({'status': 'success', 'msg': f'Procesados {contador} visitantes con éxito.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})
    finally:
        if 'conn' in locals(): conn.close()

@visitantes_bp.route('/eliminar_visitante/<int:id>', methods=['DELETE'])
def eliminar_visitante(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Eliminamos el historial de ingresos para mantener integridad relacional
        cursor.execute("DELETE FROM RegistroIngresos WHERE VisitanteID = ?", (id,))
        # 2. Eliminamos visitante
        cursor.execute("DELETE FROM Visitantes WHERE VisitanteID = ?", (id,))
        
        conn.commit()
        return jsonify({'status': 'success', 'msg': 'Visitante eliminado permanentemente.'})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})
    finally:
        if 'conn' in locals(): conn.close()