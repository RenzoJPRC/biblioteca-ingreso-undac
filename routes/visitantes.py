from flask import Blueprint, render_template, request, jsonify
from utils.queries_visitantes import obtener_todos_visitantes, registrar_nuevo_visitante, actualizar_visitante, borrar_visitante, procesar_excel_visitantes

visitantes_bp = Blueprint('visitantes', __name__, url_prefix='/admin')

@visitantes_bp.route('/visitantes')
def admin_visitantes_page():
    lista = obtener_todos_visitantes()
    return render_template('admin_visitantes.html', visitantes=lista)

@visitantes_bp.route('/agregar_visitante', methods=['POST'])
def agregar_visitante():
    data = request.json
    resultado = registrar_nuevo_visitante(data)
    return jsonify(resultado)

@visitantes_bp.route('/editar_visitante', methods=['POST'])
def editar_visitante():
    data = request.json
    resultado = actualizar_visitante(data)
    return jsonify(resultado)

@visitantes_bp.route('/subir_excel_visitantes', methods=['POST'])
def subir_excel_visitantes():
    if 'archivo_excel_vis' not in request.files: 
        return jsonify({'status': 'error', 'msg': 'Falta archivo'})
    
    file = request.files['archivo_excel_vis']
    resultado = procesar_excel_visitantes(file)
    return jsonify(resultado)

@visitantes_bp.route('/eliminar_visitante/<int:id>', methods=['DELETE'])
def eliminar_visitante(id):
    resultado = borrar_visitante(id)
    return jsonify(resultado)