from flask import Blueprint, render_template, request, jsonify
import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.queries_carnets import (
    buscar_alumnos_paginados,
    actualizar_vencimiento_individual,
    actualizar_vencimiento_masivo,
    procesar_excel_alumnos
)

admin_carnets_bp = Blueprint('admin_carnets', __name__, url_prefix='/admin')

@admin_carnets_bp.route('/carnets')
def gestion_carnets():
    return render_template('admin_carnets.html')

@admin_carnets_bp.route('/buscar_alumno')
def buscar_alumno():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    limit = 20 # Elementos por página
    
    resultados, total_items, total_pages = buscar_alumnos_paginados(query, page, limit)
    
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

    success, msg = actualizar_vencimiento_individual(alumno_id, nueva_fecha)
    if success:
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'msg': msg})

@admin_carnets_bp.route('/actualizar_carnet_masivo', methods=['POST'])
def actualizar_carnet_masivo():
    data = request.json
    ids = data.get('ids', [])
    accion = data.get('accion') # 'activar' | 'desactivar' | 'auto'

    if not ids: return jsonify({'status': 'error', 'msg': 'No seleccionaste ningun alumno'})

    success, msg = actualizar_vencimiento_masivo(ids, accion)
    if success:
        return jsonify({'status': 'success', 'msg': msg})
    else:
        return jsonify({'status': 'error', 'msg': msg})

@admin_carnets_bp.route('/subir_excel', methods=['POST'])
def subir_excel():
    if 'archivo_excel' not in request.files: return jsonify({'status': 'error', 'msg': 'Falta archivo'})
    file = request.files['archivo_excel']
    if file.filename == '': return jsonify({'status': 'error', 'msg': 'Nombre vacío'})

    try:
        df = pd.read_excel(file, dtype={'DNI': str})
        success, msg = procesar_excel_alumnos(df)
        if success:
            return jsonify({'status': 'success', 'msg': msg})
        else:
            return jsonify({'status': 'error', 'msg': msg})
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})
