from flask import Blueprint, render_template, request, jsonify
from db import get_db_connection
from utils.queries_eventos import obtener_agenda_eventos_hoy, procesar_ingreso_evento, verificar_estado_evento

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

    if not codigo: return jsonify({'status': 'error', 'msg': 'Código vacío'})

    conn = get_db_connection()
    if not conn: return jsonify({'status': 'error', 'msg': 'Error BD'})

    try:
        cursor = conn.cursor()
        sql = """
        DECLARE @out_msg nvarchar(100);
        DECLARE @out_nombre nvarchar(250);
        DECLARE @out_escuela nvarchar(100);
        DECLARE @out_semestre varchar(20);
        
        -- Ejecutamos el procedimiento y capturamos los datos de salida
        EXEC sp_RegistrarIngreso ?, ?, ?, @out_msg OUTPUT, @out_nombre OUTPUT, @out_escuela OUTPUT, @out_semestre OUTPUT;
        
        SELECT @out_msg, @out_nombre, @out_escuela, @out_semestre;
        """
        cursor.execute(sql, (codigo, piso, sede))
        row = cursor.fetchone()
        conn.commit()
        conn.close()

        if row:
            mensaje = row[0]
            # Extraemos los datos siempre (aunque venga mensaje de error de turno)
            nombre = row[1]
            escuela = row[2]
            semestre = row[3]

            # CASO 1: ÉXITO (Entra por primera vez en el turno)
            if 'CONCEDIDO' in mensaje: 
                warning_type = None
                if 'CARNET VENCIDO' in mensaje:
                    warning_type = 'carnet_vencido'

                return jsonify({
                    'status': 'success', 
                    'msg': mensaje, 
                    'warning': warning_type,
                    'alumno': nombre, 
                    'escuela': escuela, 
                    'semestre': semestre
                })
            
            # CASO 2: YA REGISTRADO (Advertencia)
            # AQUÍ ESTÁ EL TRUCO: Enviamos 'warning' pero TAMBIÉN los datos del alumno
            elif 'YA REGISTRADO' in mensaje:
                return jsonify({
                    'status': 'warning', 
                    'msg': mensaje, 
                    'alumno': nombre, 
                    'escuela': escuela, 
                    'semestre': semestre
                })

            # CASO 3: NO ENCONTRADO O ERROR REAL
            else:
                return jsonify({'status': 'error', 'msg': mensaje})
        
        return jsonify({'status': 'error', 'msg': 'Error desconocido en BD'})

    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)})

# --- RUTAS DE EVENTOS ---
@ingreso_bp.route('/api/eventos_activos', methods=['GET'])
def api_eventos_activos():
    eventos = obtener_agenda_eventos_hoy()
    if eventos and len(eventos) > 0:
        return jsonify({'status': 'success', 'eventos_activos': True, 'eventos': eventos})
    return jsonify({'status': 'success', 'eventos_activos': False, 'eventos': []})

@ingreso_bp.route('/api/evento_estado/<int:evento_id>', methods=['GET'])
def api_evento_estado(evento_id):
    estado = verificar_estado_evento(evento_id)
    return jsonify(estado)

@ingreso_bp.route('/evento/<int:evento_id>')
def ingreso_evento(evento_id):
    # Renderizamos la misma plantilla pero pasamos el ID del evento 
    return render_template('ingreso.html', piso="EVENTO", sede="Central", evento_id=evento_id)

@ingreso_bp.route('/procesar_evento_ingreso', methods=['POST'])
def procesar_evento():
    data = request.json
    codigo = data.get('codigo')
    evento_id = data.get('evento_id')
    
    if not codigo or not evento_id: 
        return jsonify({'status': 'error', 'msg': 'Faltan datos requeridos'})
        
    res = procesar_ingreso_evento(codigo, evento_id)
    return jsonify(res)