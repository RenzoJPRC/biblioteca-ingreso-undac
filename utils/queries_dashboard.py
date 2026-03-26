from db import get_db_connection

def obtener_datos_dashboard(f_inicio, f_fin, sede_filtro=None):
    conn = get_db_connection()
    if not conn: return {}
    cursor = conn.cursor()

    if f_inicio and f_fin:
        date_where = "CAST(FechaHora AS DATE) >= ? AND CAST(FechaHora AS DATE) <= ?"
        base_params = [f_inicio, f_fin]
        filtro_label = f"Desde {f_inicio} hasta {f_fin}"
    else:
        date_where = "CAST(FechaHora AS DATE) = CAST(GETDATE() AS DATE)"
        base_params = []
        filtro_label = "Datos de Hoy"

    date_where_g = date_where
    date_where_r = date_where
    params_g = list(base_params)
    params_r = list(base_params)

    if sede_filtro and sede_filtro != 'Todas':
        if sede_filtro == 'Central':
            date_where_g += " AND ISNULL(Sede, 'Central') = 'Central'"
            date_where_r += " AND ISNULL(R.Sede, 'Central') = 'Central'"
        else:
            date_where_g += " AND ISNULL(Sede, 'Central') = ?"
            date_where_r += " AND ISNULL(R.Sede, 'Central') = ?"
            params_g.append(sede_filtro)
            params_r.append(sede_filtro)

    params_g = tuple(params_g)
    params_r = tuple(params_r)

    # 1. Totales
    cursor.execute(f"SELECT COUNT(*) FROM RegistroIngresos WHERE {date_where_g}", params_g)
    total_hoy = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM RegistroIngresos WHERE AlumnoID IS NOT NULL AND {date_where_g}", params_g)
    total_alumnos = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM RegistroIngresos WHERE VisitanteID IS NOT NULL AND {date_where_g}", params_g)
    total_visitantes = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM RegistroIngresos WHERE EgresadoID IS NOT NULL AND {date_where_g}", params_g)
    total_egresados = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM RegistroIngresos WHERE PersonalID IS NOT NULL AND {date_where_g}", params_g)
    total_personal = cursor.fetchone()[0]

    # 2. Por Piso y Sede
    cursor.execute(f"SELECT Piso, COUNT(*) FROM RegistroIngresos WHERE ISNULL(Sede, 'Central')='Central' AND {date_where_g} GROUP BY Piso", params_g)
    pisos_dict = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute(f"SELECT Sede, COUNT(*) FROM RegistroIngresos WHERE ISNULL(Sede, 'Central')!='Central' AND {date_where_g} GROUP BY Sede", params_g)
    sedes_dict = {row[0]: row[1] for row in cursor.fetchall()}

    # 3. Gráfico Horas
    cursor.execute(f"""
        SELECT DATEPART(HOUR, FechaHora) as Hora, COUNT(*) 
        FROM RegistroIngresos WHERE {date_where_g} 
        GROUP BY DATEPART(HOUR, FechaHora) ORDER BY Hora
    """, params_g)
    datos_horas = cursor.fetchall()
    chart_horas_labels = [f"{row[0]}:00" for row in datos_horas]
    chart_horas_values = [row[1] for row in datos_horas]

    # 4. Top Orígenes (Unificado) - usa alias R
    # Multiplicamos los params_r por 4
    params_origenes = params_r * 4
    cursor.execute(f"""
        SELECT TOP 5 Origen, COUNT(*) as Cantidad FROM (
            SELECT A.Escuela as Origen FROM RegistroIngresos R JOIN Alumnos A ON R.AlumnoID = A.AlumnoID 
            WHERE {date_where_r}
            UNION ALL
            SELECT V.Institucion as Origen FROM RegistroIngresos R JOIN Visitantes V ON R.VisitanteID = V.VisitanteID 
            WHERE {date_where_r}
            UNION ALL
            SELECT E.EscuelaProfesional as Origen FROM RegistroIngresos R JOIN Egresados E ON R.EgresadoID = E.EgresadoID 
            WHERE {date_where_r}
            UNION ALL
            SELECT P.Oficina as Origen FROM RegistroIngresos R JOIN PersonalAdministrativo P ON R.PersonalID = P.PersonalID
            WHERE {date_where_r}
        ) as T GROUP BY Origen ORDER BY Cantidad DESC
    """, params_origenes)
    datos_escuelas = cursor.fetchall()
    chart_escuelas_labels = [row[0] for row in datos_escuelas]
    chart_escuelas_values = [row[1] for row in datos_escuelas]

    # 5. Tabla Últimos - usa alias R
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
        WHERE {date_where_r}
        ORDER BY R.FechaHora DESC
    """, params_r)
    
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

def obtener_registros_csv(f_inicio, f_fin, sede_filtro=None):
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        date_where = ""
        base_params = []
        if f_inicio and f_fin:
            date_where = "CAST(R.FechaHora AS DATE) >= ? AND CAST(R.FechaHora AS DATE) <= ?"
            base_params = [f_inicio, f_fin]
        else:
            date_where = "CAST(R.FechaHora AS DATE) = CAST(GETDATE() AS DATE)"
            
        if sede_filtro and sede_filtro != 'Todas':
            if sede_filtro == 'Central':
                date_where += " AND ISNULL(R.Sede, 'Central') = 'Central'"
            else:
                date_where += " AND ISNULL(R.Sede, 'Central') = ?"
                base_params.append(sede_filtro)
                
        cursor.execute(f"""
            SELECT 
                R.RegistroID,
                COALESCE(A.NombreCompleto, V.NombreCompleto, E.NombreCompleto, P.ApellidosNombres),
                ISNULL(R.Sede, 'Central'),
                R.Piso,
                FORMAT(R.FechaHora, 'yyyy-MM-dd HH:mm:ss'),
                R.Turno,
                CASE 
                    WHEN R.VisitanteID IS NOT NULL THEN 'Visitante' 
                    WHEN R.EgresadoID IS NOT NULL THEN 'Egresado'
                    WHEN R.PersonalID IS NOT NULL THEN 'Administrativo'
                    ELSE 'Alumno' 
                END,
                COALESCE(A.Escuela, V.Institucion, E.EscuelaProfesional, P.Oficina)
            FROM RegistroIngresos R
            LEFT JOIN Alumnos A ON R.AlumnoID = A.AlumnoID
            LEFT JOIN Visitantes V ON R.VisitanteID = V.VisitanteID
            LEFT JOIN Egresados E ON R.EgresadoID = E.EgresadoID
            LEFT JOIN PersonalAdministrativo P ON R.PersonalID = P.PersonalID
            WHERE {date_where}
            ORDER BY R.FechaHora ASC
        """, tuple(base_params))
        
        return cursor.fetchall()
    finally:
        conn.close()
