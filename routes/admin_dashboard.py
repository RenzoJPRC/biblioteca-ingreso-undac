from flask import Blueprint, render_template, request, Response, session, send_file
from utils.queries_dashboard import obtener_datos_dashboard, obtener_registros_csv
import json
import time
import io
import pandas as pd

# El Blueprint para el dashboard y la raíz de /admin
admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')

@admin_dashboard_bp.route('/')
def admin_dashboard():
    f_inicio = request.args.get('inicio')
    f_fin = request.args.get('fin')
    
    sede_filtro = session.get('admin_sede') if session.get('admin_rol') == 'Supervisor' else None
    dash_data = obtener_datos_dashboard(f_inicio, f_fin, sede_filtro)

    return render_template('admin_dashboard.html', 
                           total_hoy=dash_data['total_hoy'], 
                           total_alumnos=dash_data['total_alumnos'],
                           total_visitantes=dash_data['total_visitantes'], 
                           total_egresados=dash_data['total_egresados'], 
                           total_personal=dash_data['total_personal'],
                           pisos=dash_data['pisos'], 
                           sedes=dash_data['sedes'],
                           ultimos=dash_data['ultimos_crudos'], 
                           labels_horas=dash_data['chart_horas_labels'], 
                           data_horas=dash_data['chart_horas_values'], 
                           labels_escuelas=dash_data['chart_escuelas_labels'], 
                           data_escuelas=dash_data['chart_escuelas_values'], 
                           filtro_label=dash_data['filtro_label'], 
                           params_inicio=f_inicio or '', 
                           params_fin=f_fin or '')

@admin_dashboard_bp.route('/api/dashboard_stream')
def api_dashboard_stream():
    sede_filtro = session.get('admin_sede') if session.get('admin_rol') == 'Supervisor' else None
    
    def generate():
        while True:
            try:
                dash_data = obtener_datos_dashboard(None, None, sede_filtro)
                payload = {
                    'total_hoy': dash_data['total_hoy'],
                    'total_alumnos': dash_data['total_alumnos'],
                    'total_visitantes': dash_data['total_visitantes'],
                    'total_egresados': dash_data['total_egresados'],
                    'total_personal': dash_data['total_personal'],
                    'pisos': dash_data['pisos'],
                    'sedes': dash_data['sedes'],
                    'ultimos': dash_data['ultimos']
                }
                yield f"data: {json.dumps(payload)}\n\n"
            except Exception as e:
                print("SSE Error:", e)
            time.sleep(5)
            
    return Response(generate(), mimetype='text/event-stream')

@admin_dashboard_bp.route('/exportar_ingresos_excel')
def exportar_ingresos_excel():
    f_inicio = request.args.get('inicio')
    f_fin = request.args.get('fin')
    sede_filtro = session.get('admin_sede') if session.get('admin_rol') == 'Supervisor' else None
    registros = obtener_registros_csv(f_inicio, f_fin, sede_filtro)
    
    # Crear DataFrame (desempaquetando pyodbc.Row para evitar index mismatches)
    datos_limpios = [tuple(r) for r in registros]
    df = pd.DataFrame(datos_limpios, columns=['ID', 'Usuario', 'Sede', 'Piso', 'Fecha Hora', 'Turno', 'Perfil', 'Lugar Origen'])
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte Ingresos')
    output.seek(0)

    filename = "Reporte_Ingresos_Global.xlsx"
    if f_inicio or f_fin:
        filename = f"Reporte_Ingresos_{f_inicio or 'Inicio'}_al_{f_fin or 'Fin'}.xlsx"

    return send_file(
        output, 
        download_name=filename, 
        as_attachment=True, 
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
