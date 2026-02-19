from flask import Flask
from routes.ingreso import ingreso_bp
from routes.admin import admin_bp
from routes.visitantes import visitantes_bp

app = Flask(__name__)

# Registrar los Blueprints (Módulos)
app.register_blueprint(ingreso_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(visitantes_bp)

if __name__ == '__main__':
    # Configura tu IP y Puerto aquí - 0.0.0.0 permite conexiones desde cualquier IP
    app.run(debug=True, host='0.0.0.0', port=5000)