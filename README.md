# Sistema de Control de Acceso - Biblioteca UNDAC 📚

Sistema web para el registro y control de asistencia de estudiantes a la biblioteca, con panel administrativo avanzado.

## Características ✨

*   **Ingreso por DNI/Matrícula**: Interfaz optimizada para pantalla táctil o uso rápido.
*   **Validación de Usuarios**: Conexión con padrón de alumnos.
*   **Panel Administrativo**:
    *   Dashboard con métricas en tiempo real.
    *   Reportes gerenciales con gráficos y filtros.
    *   Gestión de alumnos y cambio de condición (Regular/Egresado).
    *   Carga masiva de padrón vía Excel.
    *   Gestión de usuarios administradores con roles.
*   **Seguridad**:
    *   Sistema de Login seguro.
    *   Backups de base de datos (descarga .zip).
    *   Bloqueo de salida de la interfaz de ingreso.

## Tecnologías 🛠️

*   **Backend**: Python (FastAPI).
*   **Base de Datos**: SQLite (Optimizado con WAL).
*   **Frontend**: HTML5, CSS3 (Vanilla), JavaScript.
*   **Gráficos**: Chart.js.

## Instalación 🚀

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/tu-usuario/biblioteca_ingreso.git
    cd biblioteca_ingreso
    ```

2.  **Crear entorno virtual**:
    ```bash
    python -m venv .venv
    # Windows
    .\.venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  **Instalar dependencias**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Ejecutar la aplicación**:
    ```bash
    python -m uvicorn app.main:app --reload
    ```

    Acceder a: `http://localhost:8000`

## Credenciales por Defecto 🔐

*   **Usuario**: `admin`
*   **Contraseña**: `admin` (Se recomienda cambiarla inmediatamente).
