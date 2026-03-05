from flask import Blueprint, render_template, request
from db import get_db_connection

# El Blueprint para el dashboard y la raíz de /admin
admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')

@admin_dashboard_bp.route('/')
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Recibir fechas del Query String
    f_inicio = request.args.get('inicio')
    f_fin = request.args.get('fin')

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

    # 2. Por Piso
    cursor.execute(f"SELECT Piso, COUNT(*) FROM RegistroIngresos WHERE {date_where} GROUP BY Piso", date_params)
    pisos_dict = {row[0]: row[1] for row in cursor.fetchall()}

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
        ) as T GROUP BY Origen ORDER BY Cantidad DESC
    """, date_params * 3) # Se multiplica por 3 porque hay 3 subconsultas
    datos_escuelas = cursor.fetchall()
    chart_escuelas_labels = [row[0] for row in datos_escuelas]
    chart_escuelas_values = [row[1] for row in datos_escuelas]

    # 5. Tabla Últimos
    cursor.execute(f"""
        SELECT TOP 10 
            COALESCE(A.NombreCompleto, V.NombreCompleto, E.NombreCompleto), 
            R.Piso, 
            FORMAT(R.FechaHora, 'HH:mm:ss'), 
            COALESCE(A.Escuela, V.Institucion, E.EscuelaProfesional), 
            CASE 
                WHEN R.VisitanteID IS NOT NULL THEN 'Visitante' 
                WHEN R.EgresadoID IS NOT NULL THEN 'Egresado'
                ELSE 'Alumno' 
            END,
            FORMAT(R.FechaHora, 'dd/MM/yyyy')
        FROM RegistroIngresos R
        LEFT JOIN Alumnos A ON R.AlumnoID = A.AlumnoID
        LEFT JOIN Visitantes V ON R.VisitanteID = V.VisitanteID
        LEFT JOIN Egresados E ON R.EgresadoID = E.EgresadoID
        WHERE {date_where}
        ORDER BY R.FechaHora DESC
    """, date_params)
    ultimos = cursor.fetchall()
    conn.close()

    return render_template('admin_dashboard.html', total_hoy=total_hoy, total_alumnos=total_alumnos,
                           total_visitantes=total_visitantes, total_egresados=total_egresados,
                           pisos=pisos_dict, ultimos=ultimos, labels_horas=chart_horas_labels, 
                           data_horas=chart_horas_values, labels_escuelas=chart_escuelas_labels, 
                           data_escuelas=chart_escuelas_values, filtro_label=filtro_label, params_inicio=f_inicio or '', params_fin=f_fin or '')
