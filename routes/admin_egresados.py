from flask import Blueprint, render_template, request, jsonify
import pandas as pd
import sys
import os

import threading
from utils.task_manager import create_task

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.queries_egresados import (
    buscar_egresados_paginados,
    guardar_egresado_individual,
    procesar_excel_egresados_async,
    eliminar_egresado_permanente,
    eliminar_egresados_masivo,
    vaciar_egresados_db
)

admin_egresados_bp = Blueprint('admin_egresados', __name__, url_prefix='/admin')

@admin_egresados_bp.route('/egresados')
def gestion_egresados():
    return render_template('admin_egresados.html')

@admin_egresados_bp.route('/buscar_egresado')
def buscar_egresado():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    limit = 20
    
    resultados, total_items, total_pages = buscar_egresados_paginados(query, page, limit)
    
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

    success, msg = guardar_egresado_individual(data)
    if success:
        return jsonify({'status': 'success', 'msg': msg})
    else:
        return jsonify({'status': 'error', 'msg': msg})

@admin_egresados_bp.route('/subir_excel_egresados', methods=['POST'])
def subir_excel_egresados():
    if 'archivo_excel' not in request.files: return jsonify({'status': 'error', 'msg': 'Falta archivo'})
    file = request.files['archivo_excel']
    if file.filename == '': return jsonify({'status': 'error', 'msg': 'Nombre vacío'})

    try:
        print("1. Recibiendo archivo Excel de Egresados y delegando a segundo plano...")
        
        file_bytes = file.read()
        task_id = create_task()
        
        # Iniciar hilo en segundo plano
        thread = threading.Thread(target=procesar_excel_egresados_async, args=(file_bytes, task_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'processing', 'task_id': task_id})
    except Exception as e:
        print("ERROR CRÍTICO AL LEER EXCEL:", str(e))
        return jsonify({'status': 'error', 'msg': str(e)})

@admin_egresados_bp.route('/eliminar_egresado/<int:id>', methods=['DELETE'])
def eliminar_egresado(id):
    success, msg = eliminar_egresado_permanente(id)
    if success:
        return jsonify({'status': 'success', 'msg': msg})
    else:
        return jsonify({'status': 'error', 'msg': msg})

@admin_egresados_bp.route('/eliminar_egresados_masivo', methods=['POST'])
def eliminar_egresados_masivos_route():
    data = request.json
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'status': 'error', 'msg': 'No se enviaron IDs para eliminar.'})
        
    success, msg = eliminar_egresados_masivo(ids)
    if success:
        return jsonify({'status': 'success', 'msg': msg})
    else:
        return jsonify({'status': 'error', 'msg': msg})

@admin_egresados_bp.route('/vaciar_egresados', methods=['DELETE'])
def vaciar_egresados_route():
    success, msg = vaciar_egresados_db()
    if success:
        return jsonify({'status': 'success', 'msg': msg})
    else:
        return jsonify({'status': 'error', 'msg': msg})
