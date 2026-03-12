from flask import Blueprint, render_template, request, jsonify
from utils.queries_admin_eventos import buscar_eventos, guardar_evento, borrar_evento, procesar_excel_invitados_async
from utils.queries_admin_eventos_detalle import obtener_asistentes_evento
import threading
from utils.task_manager import create_task

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
    
    if file.filename == '':
        return jsonify({'status': 'error', 'msg': 'Archivo no seleccionado'})
        
    if not evento_id:
        return jsonify({'status': 'error', 'msg': 'Falta el ID del evento'})
        
    try:
        print("1. Recibiendo archivo Excel de Invitados VIP y delegando a segundo plano...")
        file_bytes = file.read()
        task_id = create_task()
        
        thread = threading.Thread(target=procesar_excel_invitados_async, args=(file_bytes, evento_id, task_id))
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'processing', 'task_id': task_id})
    except Exception as e:
        print("ERROR CRÍTICO AL LEER EXCEL VIP:", str(e))
        return jsonify({'status': 'error', 'msg': str(e)})

@admin_eventos_bp.route('/evento_detalle/<int:id>')
def evento_detalle_view(id):
    resultado = obtener_asistentes_evento(id)
    if resultado.get('status') == 'error':
        return "Evento no encontrado o error", 404
    
    return render_template('admin_evento_detalle.html', 
                          evento=resultado['evento'], 
                          asistentes=resultado['data'],
                          stats=resultado['stats'])
