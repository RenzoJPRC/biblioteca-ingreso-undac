import datetime
from db import get_db_connection

def obtener_evento_activo_actual():
    """
    Retorna el evento que está activo o por iniciar en los próximos 10 minutos.
    Si hay un evento activo, devuelve un dict con los datos. Si no, None.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Consulta: Eventos de hoy, donde la hora actual está entre (HoraInicio - 10 min) y HoraFin
        # Y estado sea 'Activo'
        sql = """
            SELECT EventoID, NombreEvento, HoraInicio, HoraFin 
            FROM Eventos 
            WHERE FechaEvento = CAST(GETDATE() AS DATE)
            AND Estado = 'Activo'
            AND CAST(GETDATE() AS TIME) >= DATEADD(minute, -10, HoraInicio)
            AND CAST(GETDATE() AS TIME) <= HoraFin
        """
        cursor.execute(sql)
        row = cursor.fetchone()
        
        if row:
            return {
                'id': row[0],
                'nombre': row[1]
            }
        return None
        
    except Exception as e:
        print(f"Error consultando evento activo: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def verificar_estado_evento(evento_id):
    """
    Verifica si un evento específico sigue en curso (estado Activo y dentro de la hora).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT Estado, HoraFin, FechaEvento 
            FROM Eventos 
            WHERE EventoID = ?
        """
        cursor.execute(sql, (evento_id,))
        row = cursor.fetchone()
        
        if not row:
            return {'status': 'error', 'msg': 'No existe'}
            
        estado, hora_fin, fecha_evento = row
        
        # Verificar expiración de tiempo
        now = datetime.datetime.now()
        fecha_hora_fin = datetime.datetime.combine(fecha_evento, hora_fin)
        
        if estado != 'Activo' or now > fecha_hora_fin:
            return {'status': 'success', 'activo': False}
            
        return {'status': 'success', 'activo': True}
        
    except Exception as e:
        print(f"Error verificando estado de evento: {e}")
        return {'status': 'error', 'msg': str(e)}
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def procesar_ingreso_evento(codigo, evento_id):
    """
    Procesa un código escaneado (DNI o Carnet) comprobando reglas de acceso del evento
    y registrando en AsistenciaEventos.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Obtener reglas del evento
        cursor.execute("SELECT PermiteAlumnos, PermiteEgresados, PermitePersonal, PermiteVisitantes, NombreEvento FROM Eventos WHERE EventoID = ?", (evento_id,))
        evento = cursor.fetchone()
        
        if not evento:
            return {'status': 'error', 'msg': 'Evento no encontrado o finalizado.'}
            
        p_alum, p_egre, p_pers, p_vis, nombre_evento = evento
        
        # 2. Variable para almacenar el tipo encontrado
        tipo_persona = None
        nombre_persona = "Desconocido"
        escuela_persona = "Exterior"
        semestre_persona = ""
        identificadores_a_verificar = [codigo]
        
        # A) ES INVITADO VIP DEL EVENTO (Lista Blanca en InvitadosEvento)?
        cursor.execute("SELECT NombreCompleto, Institucion FROM InvitadosEvento WHERE DNI = ? AND EventoID = ?", (codigo, evento_id))
        invitado = cursor.fetchone()
        if invitado:
            tipo_persona = 'InvitadoEvento'
            nombre_persona = invitado[0]
            escuela_persona = invitado[1] or 'Invitado Especial'
            semestre_persona = 'INVITADO'
        else:
            # B) ES ALUMNO (Por Código Matrícula o DNI)?
            cursor.execute("""
                SELECT a.NombreCompleto, e.NombreEscuela, s.NombreSemestre, a.DNI, a.CodigoMatricula
                FROM Alumnos a
                LEFT JOIN Escuelas e ON a.EscuelaID = e.EscuelaID
                LEFT JOIN Semestres s ON a.SemestreID = s.SemestreID
                WHERE a.CodigoMatricula = ? OR a.DNI = ?
            """, (codigo, codigo))
            alum = cursor.fetchone()
            if alum:
                if p_alum:
                    tipo_persona = 'Alumno'
                    nombre_persona = alum[0]
                    escuela_persona = alum[1] if alum[1] else 'Sin Escuela'
                    semestre_persona = alum[2] if alum[2] else ''
                    # IMPORTANTE: Validamos ambos códigos para evitar doble ingreso
                    identificadores_a_verificar = [x for x in [alum[3], alum[4]] if x]
                else:
                    return {'status': 'error', 'msg': 'Acceso denegado: Evento no habilitado para Alumnos.'}
            else:
                # C) ES EGRESADO?
                cursor.execute("""
                    SELECT eg.NombreCompleto, es.NombreEscuela 
                    FROM Egresados eg
                    LEFT JOIN Escuelas es ON eg.EscuelaID = es.EscuelaID
                    WHERE eg.DNI = ?
                """, (codigo,))
                egre = cursor.fetchone()
                if egre:
                    if p_egre:
                        tipo_persona = 'Egresado'
                        nombre_persona = egre[0]
                        escuela_persona = egre[1] if egre[1] else 'Egresado'
                        semestre_persona = 'EGRESADO'
                    else:
                        return {'status': 'error', 'msg': 'Acceso denegado: Evento no habilitado para Egresados.'}
                else:
                    # D) ES PERSONAL?
                    cursor.execute("SELECT ApellidosNombres, Oficina FROM PersonalAdministrativo WHERE DNI = ?", (codigo,))
                    pers = cursor.fetchone()
                    if pers:
                        if p_pers:
                            tipo_persona = 'Personal'
                            nombre_persona = pers[0]
                            escuela_persona = pers[1] if pers[1] else 'Administrativo'
                            semestre_persona = 'ADMINISTRATIVO'
                        else:
                            return {'status': 'error', 'msg': 'Acceso denegado: Evento no habilitado para Personal.'}
                    else:
                        # E) ES VISITANTE?
                        cursor.execute("SELECT NombreCompleto, Institucion FROM Visitantes WHERE DNI = ?", (codigo,))
                        vis = cursor.fetchone()
                        if vis:
                            if p_vis:
                                tipo_persona = 'Visitante'
                                nombre_persona = vis[0]
                                escuela_persona = vis[1] if vis[1] else 'Visitante Externo'
                                semestre_persona = 'VISITANTE'
                            else:
                                return {'status': 'error', 'msg': 'Acceso denegado: Evento no habilitado para Visitantes.'}
        
        # SI NO ENCONTRÓ NADA
        if not tipo_persona:
            return {'status': 'error', 'msg': 'Persona no registrada o sin invitación para este evento.'}
            
        # 3. YA REGISTRÓ ASISTENCIA?
        placeholders = ','.join(['?'] * len(identificadores_a_verificar))
        query_check = f"SELECT AsistenciaID FROM AsistenciaEventos WHERE EventoID = ? AND CodigoEscaneado IN ({placeholders})"
        params_check = [evento_id] + identificadores_a_verificar
        cursor.execute(query_check, params_check)
        ya_asistio = cursor.fetchone()
        
        if ya_asistio:
            return {
                'status': 'warning',
                'msg': 'YA REGISTRADO EN EVENTO',
                'alumno': nombre_persona,
                'escuela': escuela_persona,
                'semestre': semestre_persona
            }
            
        # 4. REGISTRAR ASISTENCIA
        cursor.execute("INSERT INTO AsistenciaEventos (EventoID, CodigoEscaneado, TipoPersona) VALUES (?, ?, ?)", 
                       (evento_id, codigo, tipo_persona))
        conn.commit()
        
        return {
            'status': 'success',
            'msg': 'ACCESO EVENTO CONCEDIDO',
            'alumno': nombre_persona,
            'escuela': escuela_persona,
            'semestre': semestre_persona
        }

    except Exception as e:
        print(f"Error procesando ingreso evento: {e}")
        return {'status': 'error', 'msg': f'Error interno: {str(e)}'}
    finally:
        if 'conn' in locals() and conn:
            conn.close()
