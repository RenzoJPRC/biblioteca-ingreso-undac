import pyodbc
import re
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
        # 1. Verificar en Alumnos (Nadie puede duplicarse con un Alumno existente)
        if ignora_tabla == 'Alumnos' and ignora_id:
            cursor.execute("SELECT 1 FROM Alumnos WHERE DNI = ? AND AlumnoID != ?", (dni, ignora_id))
        else:
            cursor.execute("SELECT 1 FROM Alumnos WHERE DNI = ?", (dni,))
        if cursor.fetchone():
            return True, "Este DNI ya está registrado como Alumno."

        # 2. Verificar en Egresados (Permitir si se está registrando PersonalAdministrativo)
        if ignora_tabla != 'PersonalAdministrativo':
            if ignora_tabla == 'Egresados' and ignora_id:
                cursor.execute("SELECT 1 FROM Egresados WHERE DNI = ? AND EgresadoID != ?", (dni, ignora_id))
            else:
                cursor.execute("SELECT 1 FROM Egresados WHERE DNI = ?", (dni,))
            if cursor.fetchone():
                return True, "Este DNI ya está registrado como Egresado."

        # 3. Verificar en Visitantes (Nadie puede duplicarse como visitante)
        if ignora_tabla == 'Visitantes' and ignora_id:
            cursor.execute("SELECT 1 FROM Visitantes WHERE DNI = ? AND VisitanteID != ?", (dni, ignora_id))
        else:
            cursor.execute("SELECT 1 FROM Visitantes WHERE DNI = ?", (dni,))
        if cursor.fetchone():
            return True, "Este DNI ya está registrado como Visitante / Externo."

        # 4. Verificar en Personal Administrativo (Permitir si se está registrando Egresado)
        if ignora_tabla != 'Egresados':
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

def formatear_nombre_estetico(nombre_completo):
    """
    Formatea un nombre al estilo 'APELLIDOS, Nombres'.
    Si el nombre contiene coma, separa apellidos y nombres adecuadamente.
    Si no contiene coma, lo convierte a Title Case inteligentemente.
    """
    if not nombre_completo:
        return ""
        
    nombre = str(nombre_completo).strip()
    
    # Remover dobles espacios
    nombre = re.sub(r'\s+', ' ', nombre)
    
    if ',' in nombre:
        partes = nombre.split(',', 1)
        apellidos = partes[0].strip().upper()
        # Nombres en Title Case, manteniendo preposiciones o usando capitalize general
        nombres = ' '.join(word.capitalize() for word in partes[1].strip().split())
        return f"{apellidos}, {nombres}"
    else:
        # Si no hay coma, preferimos Title Case en lugar del confuso bloque en mayúsculas
        # Ejemplo: "ROJAS CASTILLO RENZO" -> "Rojas Castillo Renzo"
        return ' '.join(word.capitalize() for word in nombre.split())
