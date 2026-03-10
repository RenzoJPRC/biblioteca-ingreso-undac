import pandas as pd
from datetime import datetime
from db import get_db_connection

def buscar_eventos(query='', page=1):
    items_por_pagina = 10
    offset = (page - 1) * items_por_pagina

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql_base = "FROM Eventos WHERE NombreEvento LIKE ?"
        
        # Total
        cursor.execute(f"SELECT COUNT(*) {sql_base}", (f'%{query}%',))
        total_items = cursor.fetchone()[0]
        total_paginas = (total_items + items_por_pagina - 1) // items_por_pagina

        # Datos
        sql_datos = f"""
            SELECT EventoID, NombreEvento, FechaEvento, HoraInicio, HoraFin, Lugar, Estado,
                   PermiteAlumnos, PermiteEgresados, PermitePersonal, PermiteVisitantes
            {sql_base}
            ORDER BY FechaEvento DESC, HoraInicio DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        cursor.execute(sql_datos, (f'%{query}%', offset, items_por_pagina))
        
        eventos = []
        now = datetime.now()
        
        for row in cursor.fetchall():
            evento_id = row[0]
            fecha_evento = row[2]
            hora_fin = row[4]
            estado = row[6]
            
            # Verificar si el evento ya expiró y actualizarlo dinámicamente
            if estado == 'Activo':
                fecha_hora_fin = datetime.combine(fecha_evento, hora_fin)
                if now > fecha_hora_fin:
                    estado = 'Finalizado'
                    # Instanciar otro cursor para no interferir con la iteración principal fetchall
                    cursor_update = conn.cursor()
                    cursor_update.execute("UPDATE Eventos SET Estado = 'Finalizado' WHERE EventoID = ?", (evento_id,))
                    cursor_update.commit()
            
            # Contar asistencia
            cursor.execute("SELECT COUNT(*) FROM AsistenciaEventos WHERE EventoID = ?", (evento_id,))
            asistentes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM InvitadosEvento WHERE EventoID = ?", (evento_id,))
            invitados = cursor.fetchone()[0]
            
            eventos.append({
                'id': evento_id,
                'nombre': row[1],
                'fecha': fecha_evento.strftime('%d/%m/%Y'),
                'fecha_raw': fecha_evento.strftime('%Y-%m-%d'),
                'hora_inicio': row[3].strftime('%H:%M'),
                'hora_fin': hora_fin.strftime('%H:%M'),
                'lugar': row[5] or '',
                'estado': estado,
                'permite_alumnos': bool(row[7]),
                'permite_egresados': bool(row[8]),
                'permite_personal': bool(row[9]),
                'permite_visitantes': bool(row[10]),
                'total_asistentes': asistentes,
                'total_invitados': invitados
            })

        return {
            'status': 'success',
            'data': eventos,
            'page': page,
            'total_pages': total_paginas,
            'total_items': total_items
        }

    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        if 'conn' in locals() and conn: conn.close()

def guardar_evento(data):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        evento_id = data.get('id')
        nombre = data.get('nombre')
        fecha = data.get('fecha')
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        lugar = data.get('lugar', '')
        estado = data.get('estado', 'Activo')
        
        p_alu = 1 if data.get('permite_alumnos') else 0
        p_egr = 1 if data.get('permite_egresados') else 0
        p_per = 1 if data.get('permite_personal') else 0
        p_vis = 1 if data.get('permite_visitantes') else 0

        if evento_id: # UPDATE
            cursor.execute("""
                UPDATE Eventos 
                SET NombreEvento=?, FechaEvento=?, HoraInicio=?, HoraFin=?, Lugar=?, Estado=?,
                    PermiteAlumnos=?, PermiteEgresados=?, PermitePersonal=?, PermiteVisitantes=?
                WHERE EventoID=?
            """, (nombre, fecha, hora_inicio, hora_fin, lugar, estado, p_alu, p_egr, p_per, p_vis, evento_id))
            msg = 'Evento actualizado correctamente.'
        else: # INSERT
            cursor.execute("""
                INSERT INTO Eventos 
                (NombreEvento, FechaEvento, HoraInicio, HoraFin, Lugar, Estado, 
                 PermiteAlumnos, PermiteEgresados, PermitePersonal, PermiteVisitantes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nombre, fecha, hora_inicio, hora_fin, lugar, estado, p_alu, p_egr, p_per, p_vis))
            msg = 'Evento creado correctamente.'
            
        conn.commit()
        return {'status': 'success', 'msg': msg}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        if 'conn' in locals() and conn: conn.close()
        
def borrar_evento(evento_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Eliminar dependencias
        cursor.execute("DELETE FROM AsistenciaEventos WHERE EventoID = ?", (evento_id,))
        cursor.execute("DELETE FROM InvitadosEvento WHERE EventoID = ?", (evento_id,))
        # Eliminar evento
        cursor.execute("DELETE FROM Eventos WHERE EventoID = ?", (evento_id,))
        
        conn.commit()
        return {'status': 'success', 'msg': 'Evento eliminado.'}
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        if 'conn' in locals() and conn: conn.close()

def procesar_excel_invitados(file, evento_id):
    if file.filename == '': 
        return {'status': 'error', 'msg': 'Archivo no seleccionado'}

    try:
        df = pd.read_excel(file, dtype={'DNI': str})
        df = df.fillna('')
        conn = get_db_connection()
        cursor = conn.cursor()
        contador = 0
        
        # Solo DNI y Nombre son obligatorios
        for _, row in df.iterrows():
            dni = str(row.get('DNI', '')).strip()
            
            # Buscar variaciones de la columna nombre
            nombre = row.get('NOMBRE COMPLETO', '')
            if not nombre:
                nombre = row.get('APELLIDOS Y NOMBRES', '')
            if not nombre:
                nombre = row.get('NOMBRES', '')
            nombre = nombre.strip()
            
            inst = row.get('INSTITUCION', '').strip()
            
            if not dni or len(dni) < 5 or not nombre: continue
            
            # Check si ya está invitado al mismo evento
            cursor.execute("SELECT InvitadoID FROM InvitadosEvento WHERE DNI = ? AND EventoID = ?", (dni, evento_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO InvitadosEvento (DNI, NombreCompleto, Institucion, EventoID) 
                    VALUES (?, ?, ?, ?)
                """, (dni, nombre, inst, evento_id))
                contador += 1
                
        conn.commit()
        return {'status': 'success', 'msg': f'Se agregaron {contador} invitados al evento con éxito.'}
    except Exception as e:
        return {'status': 'error', 'msg': f'Error procesando Excel: {str(e)}'}
    finally:
        if 'conn' in locals() and conn: conn.close()
