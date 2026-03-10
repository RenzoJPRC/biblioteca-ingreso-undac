from db import get_db_connection

def obtener_datos_dashboard(f_inicio, f_fin):
    conn = get_db_connection()
    cursor = conn.cursor()

    if f_inicio and f_fin:
        date_where = "CAST(FechaHora AS DATE) >= ? AND CAST(FechaHora AS DATE) <= ?"
        date_params = (f_inicio, f_fin)
        filtro_label = f"Desde {f_inicio} hasta {f_fin}"
    else:
        date_where = "CAST(FechaHora AS DATE) = CAST(GETDATE() AS DATE)"
        date_params = ()
        filtro_label = "Datos de Hoy"

    # 1. Totales
    cursor.execute(f"SELECT COUNT(*) FROM RegistroIngresos WHERE {date_where}", date_params)
    total_hoy = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM RegistroIngresos WHERE AlumnoID IS NOT NULL AND {date_where}", date_params)
    total_alumnos = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM RegistroIngresos WHERE VisitanteID IS NOT NULL AND {date_where}", date_params)
    total_visitantes = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM RegistroIngresos WHERE EgresadoID IS NOT NULL AND {date_where}", date_params)
    total_egresados = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM RegistroIngresos WHERE PersonalID IS NOT NULL AND {date_where}", date_params)
    total_personal = cursor.fetchone()[0]

    # 2. Por Piso y Sede
    cursor.execute(f"SELECT Piso, COUNT(*) FROM RegistroIngresos WHERE Sede='Central' AND {date_where} GROUP BY Piso", date_params)
    pisos_dict = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute(f"SELECT Sede, COUNT(*) FROM RegistroIngresos WHERE Sede!='Central' AND {date_where} GROUP BY Sede", date_params)
    sedes_dict = {row[0]: row[1] for row in cursor.fetchall()}

    # 3. Gráfico Horas
    cursor.execute(f"""
        SELECT DATEPART(HOUR, FechaHora) as Hora, COUNT(*) 
        FROM RegistroIngresos WHERE {date_where} 
        GROUP BY DATEPART(HOUR, FechaHora) ORDER BY Hora
    """, date_params)
    datos_horas = cursor.fetchall()
    chart_horas_labels = [f"{row[0]}:00" for row in datos_horas]
    chart_horas_values = [row[1] for row in datos_horas]

    # 4. Top Orígenes (Unificado)
    cursor.execute(f"""
        SELECT TOP 5 Origen, COUNT(*) as Cantidad FROM (
            SELECT A.Escuela as Origen FROM RegistroIngresos R JOIN Alumnos A ON R.AlumnoID = A.AlumnoID 
            WHERE {date_where}
            UNION ALL
            SELECT V.Institucion as Origen FROM RegistroIngresos R JOIN Visitantes V ON R.VisitanteID = V.VisitanteID 
            WHERE {date_where}
            UNION ALL
            SELECT E.EscuelaProfesional as Origen FROM RegistroIngresos R JOIN Egresados E ON R.EgresadoID = E.EgresadoID 
            WHERE {date_where}
            UNION ALL
            SELECT P.Oficina as Origen FROM RegistroIngresos R JOIN PersonalAdministrativo P ON R.PersonalID = P.PersonalID
            WHERE {date_where}
        ) as T GROUP BY Origen ORDER BY Cantidad DESC
    """, date_params * 4) # Se multiplica por 4 porque hay 4 subconsultas
    datos_escuelas = cursor.fetchall()
    chart_escuelas_labels = [row[0] for row in datos_escuelas]
    chart_escuelas_values = [row[1] for row in datos_escuelas]

    # 5. Tabla Últimos
    cursor.execute(f"""
        SELECT TOP 10 
            COALESCE(A.NombreCompleto, V.NombreCompleto, E.NombreCompleto, P.ApellidosNombres), 
            R.Piso, 
            FORMAT(R.FechaHora, 'HH:mm:ss'), 
            COALESCE(A.Escuela, V.Institucion, E.EscuelaProfesional, P.Oficina), 
            CASE 
                WHEN R.VisitanteID IS NOT NULL THEN 'Visitante' 
                WHEN R.EgresadoID IS NOT NULL THEN 'Egresado'
                WHEN R.PersonalID IS NOT NULL THEN 'Administrativo'
                ELSE 'Alumno' 
            END,
            FORMAT(R.FechaHora, 'dd/MM/yyyy'),
            ISNULL(R.Sede, 'Central')
        FROM RegistroIngresos R
        LEFT JOIN Alumnos A ON R.AlumnoID = A.AlumnoID
        LEFT JOIN Visitantes V ON R.VisitanteID = V.VisitanteID
        LEFT JOIN Egresados E ON R.EgresadoID = E.EgresadoID
        LEFT JOIN PersonalAdministrativo P ON R.PersonalID = P.PersonalID
        WHERE {date_where}
        ORDER BY R.FechaHora DESC
    """, date_params)
    
    ultimos_crudos = cursor.fetchall()
    ultimos = []
    for row in ultimos_crudos:
        ultimos.append({
            'nombre': row[0],
            'piso': row[1],
            'hora': row[2],
            'origen': row[3],
            'tipo': row[4],
            'fecha': row[5],
            'sede': row[6]
        })
        
    conn.close()

    return {
        'total_hoy': total_hoy,
        'total_alumnos': total_alumnos,
        'total_visitantes': total_visitantes,
        'total_egresados': total_egresados,
        'total_personal': total_personal,
        'pisos': pisos_dict,
        'sedes': sedes_dict,
        'chart_horas_labels': chart_horas_labels,
        'chart_horas_values': chart_horas_values,
        'chart_escuelas_labels': chart_escuelas_labels,
        'chart_escuelas_values': chart_escuelas_values,
        'ultimos': ultimos,
        'ultimos_crudos': ultimos_crudos,
        'filtro_label': filtro_label
    }
