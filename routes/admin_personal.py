from flask import Blueprint, render_template, request, jsonify
from utils.queries_personal import buscar_personal_administrativo, guardar_personal_administrativo, borrar_personal_administrativo

admin_personal_bp = Blueprint('admin_personal', __name__, url_prefix='/admin')

@admin_personal_bp.route('/personal')
def gestion_personal():
    return render_template('admin_personal.html')

@admin_personal_bp.route('/buscar_personal')
def buscar_personal():
    query = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    
    resultado = buscar_personal_administrativo(query, page)
    return jsonify(resultado)

@admin_personal_bp.route('/guardar_personal', methods=['POST'])
def guardar_personal():
    data = request.json
    resultado = guardar_personal_administrativo(data)
    return jsonify(resultado)

@admin_personal_bp.route('/eliminar_personal/<int:id>', methods=['DELETE'])
def eliminar_personal(id):
    resultado = borrar_personal_administrativo(id)
    return jsonify(resultado)
