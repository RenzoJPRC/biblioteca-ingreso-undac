from flask import Blueprint, render_template, request, jsonify
from utils.queries_admin_eventos import buscar_eventos, guardar_evento, borrar_evento, procesar_excel_invitados
from utils.queries_admin_eventos_detalle import obtener_asistentes_evento

admin_eventos_bp = Blueprint('admin_eventos', __name__, url_prefix='/admin')

@admin_eventos_bp.route('/eventos')
def gestion_eventos():
    return render_template('admin_eventos.html')

@admin_eventos_bp.route('/buscar_eventos')
def buscar_evts():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    
    resultado = buscar_eventos(query, page)
    return jsonify(resultado)

@admin_eventos_bp.route('/guardar_evento', methods=['POST'])
def guardar_evt():
    data = request.json
    resultado = guardar_evento(data)
    return jsonify(resultado)

@admin_eventos_bp.route('/eliminar_evento/<int:id>', methods=['DELETE'])
def eliminar_evt(id):
    resultado = borrar_evento(id)
    return jsonify(resultado)

@admin_eventos_bp.route('/importar_invitados_evento', methods=['POST'])
def importar_invitados():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'msg': 'No se envió ningún archivo'})
    
    file = request.files['file']
    evento_id = request.form.get('evento_id')
    
    if not evento_id:
        return jsonify({'status': 'error', 'msg': 'Falta el ID del evento'})
        
    resultado = procesar_excel_invitados(file, evento_id)
    return jsonify(resultado)

@admin_eventos_bp.route('/evento_detalle/<int:id>')
def evento_detalle_view(id):
    resultado = obtener_asistentes_evento(id)
    if resultado.get('status') == 'error':
        return "Evento no encontrado o error", 404
    
    return render_template('admin_evento_detalle.html', 
                          evento=resultado['evento'], 
                          asistentes=resultado['data'],
                          stats=resultado['stats'])
