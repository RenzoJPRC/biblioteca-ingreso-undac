from flask import Blueprint, render_template, request, jsonify
from db import get_db_connection
from utils.queries_eventos import obtener_agenda_eventos_hoy, procesar_ingreso_evento, verificar_estado_evento, obtener_sede_evento
from utils.queries_ingreso import registrar_ingreso_general

# Definimos el Blueprint
ingreso_bp = Blueprint('ingreso', __name__)

@ingreso_bp.route('/')
def index():
    return render_template('index.html')

@ingreso_bp.route('/piso1')
def piso1(): return render_template('ingreso.html', piso=1, sede='Central')

@ingreso_bp.route('/piso2')
def piso2(): return render_template('ingreso.html', piso=2, sede='Central')

@ingreso_bp.route('/piso3')
def piso3(): return render_template('ingreso.html', piso=3, sede='Central')

@ingreso_bp.route('/filial/<sede>')
def filial(sede): return render_template('ingreso.html', piso=1, sede=sede)

# API: PROCESAR EL ESCANEO
@ingreso_bp.route('/procesar_ingreso', methods=['POST'])
def procesar_ingreso():
    data = request.json
    codigo = data.get('codigo')
    piso = data.get('piso')
    sede = data.get('sede', 'Central')

    codigo_str = str(codigo).strip()
    
    # Prevenir inputs basura del escáner (E.g: "-", " - ", "--", "0", vacíos, o muy cortos)
    if not codigo_str or codigo_str in ['0', '0.0'] or codigo_str.replace('-', '').strip() == '' or len(codigo_str) < 4:
        return jsonify({'status': 'error', 'msg': 'Posible Lectura Errónea del Escáner'})

    res = registrar_ingreso_general(codigo_str, piso, sede)
    return jsonify(res)

# --- RUTAS DE EVENTOS ---
@ingreso_bp.route('/api/eventos_activos', methods=['GET'])
def api_eventos_activos():
    sede = request.args.get('sede', 'Central')
    eventos = obtener_agenda_eventos_hoy(sede)
    if eventos and len(eventos) > 0:
        return jsonify({'status': 'success', 'eventos_activos': True, 'eventos': eventos})
    return jsonify({'status': 'success', 'eventos_activos': False, 'eventos': []})

@ingreso_bp.route('/api/evento_estado/<int:evento_id>', methods=['GET'])
def api_evento_estado(evento_id):
    estado = verificar_estado_evento(evento_id)
    return jsonify(estado)

@ingreso_bp.route('/evento/<int:evento_id>')
def ingreso_evento(evento_id):
    sede_evento = obtener_sede_evento(evento_id)
        
    return render_template('ingreso.html', piso="EVENTO", sede=sede_evento, evento_id=evento_id)

@ingreso_bp.route('/procesar_evento_ingreso', methods=['POST'])
def procesar_evento():
    data = request.json
    codigo = data.get('codigo')
    evento_id = data.get('evento_id')
    
    if not codigo or str(codigo).strip() in ['0', '0.0', ''] or not evento_id: 
        return jsonify({'status': 'error', 'msg': 'Datos inválidos o faltantes'})
        
    res = procesar_ingreso_evento(str(codigo).strip(), evento_id)
    return jsonify(res)