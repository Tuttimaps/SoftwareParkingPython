import os
import sys
import shutil

def get_resource_path(relative_path):
    """Obtiene la ruta absoluta para un recurso, compatible con desarrollo y ejecutables empaquetados."""
    try:
        # PyInstaller usa una carpeta temporal en _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # En modo desarrollo, usa la ruta del script
        base_path = os.path.abspath(os.path.dirname(__file__))

    # Manejo especial para la base de datos
    if "parqueadero.db" in relative_path:
        # Ubicación persistente: directorio del ejecutable
        exe_dir = os.path.dirname(sys.executable)
        persistent_db_path = os.path.join(exe_dir, relative_path)
        # Si no existe en la ubicación persistente, copiar desde el temporal si está disponible
        if not os.path.exists(persistent_db_path):
            temp_db_path = os.path.join(base_path, relative_path)
            os.makedirs(os.path.dirname(persistent_db_path), exist_ok=True)
            if os.path.exists(temp_db_path):
                shutil.copy2(temp_db_path, persistent_db_path)
            else:
                # Si no hay base de datos inicial, crear una vacía
                open(persistent_db_path, 'a').close()  # Crear archivo vacío
        return persistent_db_path
    else:
        # Para otros recursos, usar la ruta temporal o base
        return os.path.join(base_path, relative_path)