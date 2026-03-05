import pandas as pd
import pyodbc
import os
from db import get_db_connection

def cargar_excel_egresados():
    archivo = 'lista_egresados.xlsx'
    if not os.path.exists(archivo):
        print(f"❌ No encuentro '{archivo}'.")
        print("💡 TIP: Debes colocar un archivo llamado 'lista_egresados.xlsx' al lado de este script.")
        return

    print("📂 Leyendo Excel de Egresados...")
    try:
        df = pd.read_excel(archivo, dtype={'DNI': str, 'CODIGO DE MATRICULA': str, 'CELULAR': str})
        df = df.fillna('')
    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return

    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()
    
    total = 0
    print(f"🚀 Procesando {len(df)} egresados...")

    for _, row in df.iterrows():
        try:
            nombre = row.get('APELLIDOS Y NOMBRE', '').strip()
            dni = str(row.get('DNI', '')).strip()
            codigo = str(row.get('CODIGO DE MATRICULA', '')).strip()
            facultad_txt = row.get('FACULTAD', '').strip()
            escuela_txt = row.get('ESCUELA', '').strip()
            correo_per = row.get('CORREO PERSONAL', '').strip()
            correo_inst = row.get('CORREO INSTITUCIONAL', '').strip()
            celular = row.get('CELULAR', '').strip()
            
            if not dni or len(dni) < 5 or not nombre: 
                continue

            # Verificamos si existe el DNI
            cursor.execute("SELECT EgresadoID FROM Egresados WHERE DNI = ?", (dni,))
            existe = cursor.fetchone()

            if existe:
                # Actualizar manteniendo activo
                cursor.execute("""
                    UPDATE Egresados 
                    SET NombreCompleto=?, CodigoMatricula=?, Facultad=?, EscuelaProfesional=?, CorreoPersonal=?, CorreoInstitucional=?, Celular=?
                    WHERE DNI=?
                """, (nombre, codigo, facultad_txt, escuela_txt, correo_per, correo_inst, celular, dni))
            else:
                # Insertar
                cursor.execute("""
                    INSERT INTO Egresados (NombreCompleto, DNI, CodigoMatricula, Facultad, EscuelaProfesional, CorreoPersonal, CorreoInstitucional, Celular, Estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (nombre, dni, codigo, facultad_txt, escuela_txt, correo_per, correo_inst, celular))
            
            total += 1
            if total % 50 == 0: print(f"   ✅ {total} procesados...")

        except Exception as e:
            print(f"⚠️ Error en DNI {dni}: {e}")

    conn.commit()
    conn.close()
    print(f"🏁 Carga de Egresados completada. Procesados en total: {total}")

if __name__ == '__main__':
    cargar_excel_egresados()
