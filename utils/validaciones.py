import pyodbc
from db import get_db_connection

def verificar_dni_global(dni, ignora_tabla=None, ignora_id=None, cursor=None):
    """
    Verifica si un DNI ya existe en cualquier tabla de registro (Alumnos, Egresados, Visitantes).
    Retorna (True, 'mensaje de error') si el DNI ya está en uso.
    Retorna (False, None) si el DNI está libre.
    
    Permite ignorar la búsqueda en un registro específico (útil para la edición).
    - ignora_tabla: 'Alumnos', 'Egresados' o 'Visitantes'
    - ignora_id: ID del registro que se está editando
    - cursor: Cursor de BD opcional para reusar transacciones abiertas.
    """
    if not dni:
        return False, None
        
    local_cursor = False
    if cursor is None:
        conn = get_db_connection()
        cursor = conn.cursor()
        local_cursor = True
        
    try:
        # 1. Verificar en Alumnos
        if ignora_tabla == 'Alumnos' and ignora_id:
            cursor.execute("SELECT 1 FROM Alumnos WHERE DNI = ? AND AlumnoID != ?", (dni, ignora_id))
        else:
            cursor.execute("SELECT 1 FROM Alumnos WHERE DNI = ?", (dni,))
        if cursor.fetchone():
            return True, "Este DNI ya está registrado como Alumno."

        # 2. Verificar en Egresados
        if ignora_tabla == 'Egresados' and ignora_id:
            cursor.execute("SELECT 1 FROM Egresados WHERE DNI = ? AND EgresadoID != ?", (dni, ignora_id))
        else:
            cursor.execute("SELECT 1 FROM Egresados WHERE DNI = ?", (dni,))
        if cursor.fetchone():
            return True, "Este DNI ya está registrado como Egresado."

        # 3. Verificar en Visitantes
        if ignora_tabla == 'Visitantes' and ignora_id:
            cursor.execute("SELECT 1 FROM Visitantes WHERE DNI = ? AND VisitanteID != ?", (dni, ignora_id))
        else:
            cursor.execute("SELECT 1 FROM Visitantes WHERE DNI = ?", (dni,))
        if cursor.fetchone():
            return True, "Este DNI ya está registrado como Visitante / Externo."

        # 4. Verificar en Personal Administrativo
        if ignora_tabla == 'PersonalAdministrativo' and ignora_id:
            cursor.execute("SELECT 1 FROM PersonalAdministrativo WHERE DNI = ? AND PersonalID != ?", (dni, ignora_id))
        else:
            cursor.execute("SELECT 1 FROM PersonalAdministrativo WHERE DNI = ?", (dni,))
        if cursor.fetchone():
            return True, "Este DNI ya está registrado como Personal Administrativo."

        return False, None
        
    except Exception as e:
        print(f"Error comprobando DNI: {e}")
        return True, "Error interno validando el DNI."
    finally:
        if local_cursor and 'conn' in locals():
            conn.close()
