from flask import Blueprint, render_template, request, jsonify
from db import get_db_connection
from utils.queries_eventos import obtener_agenda_eventos_hoy, procesar_ingreso_evento, verificar_estado_evento, obtener_sede_evento
from utils.queries_ingreso import registrar_ingreso_general

# Definimos el Blueprint
ingreso_bp = Blueprint('ingreso', __name__)

@ingreso_bp.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SalaID, NombreSala, Piso, Sede FROM Salas WHERE Activo = 1 ORDER BY Sede ASC, Piso ASC, NombreSala ASC")
    salas_db = cursor.fetchall()
    conn.close()
    
    salas_agrupadas = {}
    for s in salas_db:
        if s.Sede not in salas_agrupadas:
            salas_agrupadas[s.Sede] = {}
        if s.Piso not in salas_agrupadas[s.Sede]:
            salas_agrupadas[s.Sede][s.Piso] = []
        salas_agrupadas[s.Sede][s.Piso].append({
            'SalaID': s.SalaID,
            'NombreSala': s.NombreSala
        })
        
    return render_template('index.html', salas_agrupadas=salas_agrupadas)

@ingreso_bp.route('/sala/<int:sala_id>')
def ingreso_sala(sala_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT NombreSala, Piso, Sede FROM Salas WHERE SalaID = ? AND Activo = 1", (sala_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return "ERROR: Sala inactiva o no registrada en el sistema. Contacte Administración.", 404
        
    return render_template('ingreso.html', sala_id=sala_id, nombre_sala=row.NombreSala, piso=row.Piso, sede=row.Sede)

@ingreso_bp.route('/filial/<sede>')
def filial(sede): return render_template('ingreso.html', sala_id=1, nombre_sala="Principal", piso=1, sede=sede)

# API: PROCESAR EL ESCANEO
@ingreso_bp.route('/procesar_ingreso', methods=['POST'])
def procesar_ingreso():
    data = request.json
    codigo = data.get('codigo')
    sala_id = data.get('sala_id', 1)

    codigo_str = str(codigo).strip()
    
    # Prevenir inputs basura del escáner
    if not codigo_str or codigo_str in ['0', '0.0'] or codigo_str.replace('-', '').strip() == '' or len(codigo_str) < 4:
        return jsonify({'status': 'error', 'msg': 'Posible Lectura Errónea del Escáner'})

    res = registrar_ingreso_general(codigo_str, sala_id)
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