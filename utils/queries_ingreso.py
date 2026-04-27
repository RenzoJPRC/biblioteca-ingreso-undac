from db import get_db_connection

def registrar_ingreso_general(codigo, piso, sede):
    """
    Ejecuta el stored procedure sp_RegistrarIngreso y retorna el resultado
    en un formato de diccionario que el endpoint espera.
    """
    conn = get_db_connection()
    if not conn: 
        return {'status': 'error', 'msg': 'Error BD'}

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
        
        if row:
            mensaje = row[0]
            nombre = row[1]
            escuela = row[2]
            semestre = row[3]

            if 'CONCEDIDO' in mensaje or 'NUEVO INGRESO' in mensaje: 
                warning_type = None
                if 'VENCIDO' in mensaje or 'CARNET VENCIDO' in mensaje:
                    warning_type = 'carnet_vencido'

                return {
                    'status': 'success', 
                    'msg': mensaje, 
                    'warning': warning_type,
                    'alumno': nombre, 
                    'escuela': escuela, 
                    'semestre': semestre
                }
            
            elif 'YA REGISTRADO' in mensaje or 'YA ESTÁS REGISTRADO' in mensaje:
                return {
                    'status': 'warning', 
                    'msg': mensaje, 
                    'alumno': nombre, 
                    'escuela': escuela, 
                    'semestre': semestre
                }

            else:
                return {'status': 'error', 'msg': mensaje}
        
        return {'status': 'error', 'msg': 'Error desconocido en BD'}

    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    finally:
        if 'conn' in locals() and conn:
            conn.close()
