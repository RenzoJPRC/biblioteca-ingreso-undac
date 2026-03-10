from flask import Flask
from routes.ingreso import ingreso_bp
from routes.visitantes import visitantes_bp

# Módulos Administrador segregados
from routes.admin_dashboard import admin_dashboard_bp
from routes.admin_reportes import admin_reportes_bp
from routes.admin_carnets import admin_carnets_bp
from routes.admin_egresados import admin_egresados_bp
from routes.admin_personal import admin_personal_bp
from routes.admin_eventos import admin_eventos_bp

app = Flask(__name__)

# Registrar los Blueprints (Módulos)
app.register_blueprint(ingreso_bp)
app.register_blueprint(visitantes_bp)

app.register_blueprint(admin_dashboard_bp)
app.register_blueprint(admin_reportes_bp)
app.register_blueprint(admin_carnets_bp)
app.register_blueprint(admin_egresados_bp)
app.register_blueprint(admin_personal_bp)
app.register_blueprint(admin_eventos_bp)

if __name__ == '__main__':
    # Configura tu IP y Puerto aquí - 0.0.0.0 permite conexiones desde cualquier IP
    app.run(debug=True, host='0.0.0.0', port=5000)