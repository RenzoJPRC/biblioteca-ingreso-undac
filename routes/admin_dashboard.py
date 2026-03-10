from flask import Blueprint, render_template, request
from utils.queries_dashboard import obtener_datos_dashboard

# El Blueprint para el dashboard y la raíz de /admin
admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')

@admin_dashboard_bp.route('/')
def admin_dashboard():
    f_inicio = request.args.get('inicio')
    f_fin = request.args.get('fin')
    
    dash_data = obtener_datos_dashboard(f_inicio, f_fin)

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

@admin_dashboard_bp.route('/api/dashboard_data')
def api_dashboard_data():
    # El endpoint API siempre devuelve los datos del dia de hoy
    dash_data = obtener_datos_dashboard(None, None)
    
    return {
        'total_hoy': dash_data['total_hoy'],
        'total_alumnos': dash_data['total_alumnos'],
        'total_visitantes': dash_data['total_visitantes'],
        'total_egresados': dash_data['total_egresados'],
        'total_personal': dash_data['total_personal'],
        'pisos': dash_data['pisos'],
        'sedes': dash_data['sedes'],
        'ultimos': dash_data['ultimos']
    }
