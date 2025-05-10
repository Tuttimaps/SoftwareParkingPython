import sqlite3
import os
from datetime import datetime
from utils import get_resource_path  # Importar desde utils.py

import sqlite3
import os
from datetime import datetime
from utils import get_resource_path  # Importar desde utils.py

def conectar():
    """Conectar a la base de datos con verificación de errores."""
    conn = None
    try:
        db_path = get_resource_path("data/parqueadero.db")  # Ruta relativa
        conn = sqlite3.connect(db_path)
        print(f"Conexión exitosa a la base de datos en {db_path}")  # Depuración
        return conn
    except sqlite3.Error as e:
        print(f"Error al conectar a la base de datos '{db_path}': {str(e)}")  # Depuración
        return None
    except Exception as e:
        print(f"Error inesperado al conectar: {str(e)}")  # Depuración
        return None

# Resto del código de database.py permanece igual

def crear_tablas():
    """Crea las tablas necesarias en la base de datos si no existen."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            raise Exception("No se pudo establecer conexión con la base de datos")
        
        cursor = conn.cursor()

        # Tabla de sesiones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sesiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                fecha_inicio TEXT NOT NULL,
                fecha_cierre TEXT,
                estado TEXT NOT NULL CHECK(estado IN ('ACTIVA', 'CERRADA'))
            )
        ''')

        # Tabla de vehículos (solo vehículos actualmente DENTRO)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehiculos (
                placa TEXT PRIMARY KEY,
                tipo TEXT NOT NULL,
                hora_ingreso TEXT NOT NULL,
                hora_salida TEXT,
                estado TEXT NOT NULL,
                ticket_id TEXT NOT NULL,
                sesion_id INTEGER,
                convenio TEXT,
                FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
            )
        ''')

        # Tabla de historial de vehículos (ingresos y salidas completados)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial_vehiculos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placa TEXT NOT NULL,
                tipo TEXT NOT NULL,
                hora_ingreso TEXT NOT NULL,
                hora_salida TEXT NOT NULL,
                estado TEXT NOT NULL,
                ticket_id TEXT NOT NULL,
                sesion_id INTEGER,
                convenio TEXT,
                monto REAL,
                FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
            )
        ''')

        # Tabla de registros (eventos de facturación)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placa TEXT NOT NULL,
                evento TEXT NOT NULL,
                fecha_hora TEXT NOT NULL,
                monto REAL,
                sesion_id INTEGER,
                convenio TEXT,
                FOREIGN KEY (placa) REFERENCES vehiculos(placa),
                FOREIGN KEY (sesion_id) REFERENCES sesiones(id)
            )
        ''')

        # Tabla de tarifas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tarifas (
                tipo TEXT PRIMARY KEY,
                valor_minuto REAL NOT NULL
            )
        ''')

        # Tabla de convenios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS convenios (
                nombre TEXT PRIMARY KEY,
                valor REAL NOT NULL
            )
        ''')

        # Insertar tarifas iniciales si no existen
        cursor.execute('''
            INSERT OR IGNORE INTO tarifas (tipo, valor_minuto) VALUES
            ('Automovil', 81),
            ('Motocicleta', 60),
            ('Bicicleta', 10)
        ''')

        # Insertar convenios iniciales si no existen
        cursor.execute('''
            INSERT OR IGNORE INTO convenios (nombre, valor) VALUES
            ('CONVENIO 12,000', 12000),
            ('CONVENIO 14,000', 14000),
            ('CONVENIO 16,000', 16000),
            ('CONVENIO 19,000', 19000),
            ('CONVENIO 23,000', 23000),
            ('CONVENIO 26,000', 26000),
            ('CONVENIO 30,000', 30000),
            ('CONVENIO 40,000', 40000),
            ('CONVENIO 50,000', 50000),
            ('CONVENIO 100,000', 100000),
            ('CONVENIO CARRO 100', 100000)
        ''')

        conn.commit()
        print("Tablas creadas o verificadas correctamente.")
    except Exception as e:
        print(f"Error al crear tablas: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def insertar_vehiculo(placa, tipo, hora_ingreso, ticket_id):
    """Inserta un vehículo en la base de datos con su ticket_id y sesion_id."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return False, "No se pudo conectar a la base de datos"
        
        cursor = conn.cursor()

        sesion_id = obtener_sesion_actual()
        print(f"DEBUG - Sesión ID al insertar vehículo: {sesion_id}")  # Depuración
        
        if not sesion_id:
            return False, "No hay sesión activa"

        # Verificar si la placa ya existe
        cursor.execute("SELECT estado FROM vehiculos WHERE placa = ?", (placa,))
        resultado = cursor.fetchone()

        if resultado:
            estado = resultado[0]
            if estado == 'DENTRO':
                return False, f"La placa {placa} ya está registrada y aún está dentro."
            elif estado == 'FUERA':
                cursor.execute("DELETE FROM vehiculos WHERE placa = ?", (placa,))
                print(f"Registro anterior de la placa {placa} eliminado (estado: FUERA).")

        # Insertar el nuevo registro
        cursor.execute('''
            INSERT INTO vehiculos (placa, tipo, hora_ingreso, estado, ticket_id, sesion_id)
            VALUES (?, ?, ?, 'DENTRO', ?, ?)
        ''', (placa, tipo, hora_ingreso, ticket_id, sesion_id))
        conn.commit()
        return True, f"Vehículo {placa} ingresado correctamente."
    except Exception as e:
        print(f"Error al insertar vehículo: {str(e)}")
        return False, f"Error al insertar vehículo: {str(e)}"
    finally:
        if conn:
            conn.close()

def obtener_sesion_actual():
    """Obtiene el ID de la sesión activa para el usuario actual."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM sesiones 
            WHERE estado = 'ACTIVA' 
            ORDER BY id DESC 
            LIMIT 1
        ''')
        sesion_id = cursor.fetchone()
        return sesion_id[0] if sesion_id else None
    except Exception as e:
        print(f"Error al obtener sesión actual: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def registrar_evento_sesion(usuario, accion, fecha_hora):
    """Registra eventos de sesión y siempre devuelve 3 valores."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return False, "No se pudo conectar a la base de datos", None
        cursor = conn.cursor()
        
        if accion == "Inicio":
            cursor.execute('''
                INSERT INTO sesiones (usuario, fecha_inicio, estado)
                VALUES (?, ?, 'ACTIVA')
            ''', (usuario, fecha_hora))
            conn.commit()
            sesion_id = cursor.lastrowid
            return True, "Sesión iniciada", sesion_id
        elif accion == "Cierre":
            return True, "Sesión cerrada", None
        else:
            return False, "Acción no válida", None
    except sqlite3.Error as e:
        return False, f"Error de base de datos: {str(e)}", None
    except Exception as e:
        return False, f"Error inesperado: {str(e)}", None
    finally:
        if conn:
            conn.close()

def registrar_salida(placa, hora_salida, costo, convenio):
    """Registra la salida de un vehículo, mueve su registro a historial_vehiculos y actualiza registros."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return False, "No se pudo conectar a la base de datos"
        cursor = conn.cursor()

        cursor.execute('''
            SELECT placa, tipo, hora_ingreso, hora_salida, estado, ticket_id, sesion_id, convenio
            FROM vehiculos
            WHERE placa = ? AND estado = 'DENTRO'
        ''', (placa,))
        vehiculo = cursor.fetchone()

        if not vehiculo:
            print(f"No se encontró el vehículo con placa {placa} o no está dentro.")
            return False, f"No se encontró el vehículo con placa {placa} o no está dentro."

        placa, tipo, hora_ingreso, _, estado, ticket_id, sesion_id_original, _ = vehiculo
        print(f"Registrando salida de {placa}: tipo={tipo}, hora_ingreso={hora_ingreso}, sesion_id_original={sesion_id_original}")

        sesion_id_actual = obtener_sesion_actual()
        if sesion_id_actual is None:
            return False, "No hay una sesión activa para registrar la salida."

        cursor.execute('''
            INSERT INTO historial_vehiculos (placa, tipo, hora_ingreso, hora_salida, estado, ticket_id, sesion_id, convenio, monto)
            VALUES (?, ?, ?, ?, 'FUERA', ?, ?, ?, ?)
        ''', (placa, tipo, hora_ingreso, hora_salida, ticket_id, sesion_id_actual, convenio, costo))
        print(f"Registro de {placa} movido a historial_vehiculos con monto={costo}, sesion_id={sesion_id_actual}")

        cursor.execute('''
            DELETE FROM vehiculos
            WHERE placa = ?
        ''', (placa,))
        print(f"Registro de {placa} eliminado de vehiculos")

        cursor.execute('''
            INSERT INTO registros (placa, evento, fecha_hora, monto, sesion_id, convenio)
            VALUES (?, 'FACTURACIÓN', ?, ?, ?, ?)
        ''', (placa, hora_salida, costo, sesion_id_actual, convenio))
        print(f"Evento de facturación registrado para {placa} en registros con sesion_id={sesion_id_actual}")

        conn.commit()
        return True, "Salida registrada correctamente."
    except Exception as e:
        print(f"Error al registrar salida: {str(e)}")
        return False, f"Error al registrar salida: {str(e)}"
    finally:
        if conn:
            conn.close()

def contar_vehiculos_dentro():
    """Cuenta el número total de vehículos dentro."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return 0
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM vehiculos WHERE estado = 'DENTRO'
        ''')
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        print(f"Error al contar vehículos: {str(e)}")
        return 0
    finally:
        if conn:
            conn.close()

def contar_vehiculos_por_tipo(tipo, sesion_id=None):
    """Cuenta el número de vehículos de un tipo específico dentro."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return 0
        cursor = conn.cursor()
        if sesion_id:
            cursor.execute('''
                SELECT COUNT(*) FROM vehiculos
                WHERE tipo = ? AND estado = 'DENTRO' AND placa NOT IN (
                    SELECT placa FROM registros WHERE evento = 'FACTURACIÓN' AND sesion_id = ?
                )
            ''', (tipo, sesion_id))
        else:
            cursor.execute('''
                SELECT COUNT(*) FROM vehiculos WHERE tipo = ? AND estado = 'DENTRO'
            ''', (tipo,))
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        print(f"Error al contar vehículos por tipo: {str(e)}")
        return 0
    finally:
        if conn:
            conn.close()

def obtener_estado_vehiculo(placa):
    """Obtiene el estado de un vehículo."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute('''
            SELECT estado FROM vehiculos WHERE placa = ? ORDER BY id DESC LIMIT 1
        ''', (placa,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error al obtener estado: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def obtener_hora_ingreso(placa):
    """Obtiene la hora de ingreso de un vehículo."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return None
        cursor = conn.cursor()
        cursor.execute('''
            SELECT hora_ingreso FROM vehiculos WHERE placa = ? AND estado = 'DENTRO'
        ''', (placa,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error al obtener hora de ingreso: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def calcular_costo(placa, convenio, convenios_dict=None):
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return 0
        cursor = conn.cursor()
        cursor.execute("SELECT hora_ingreso, tipo FROM vehiculos WHERE placa = ? AND estado = 'DENTRO'", (placa,))
        resultado = cursor.fetchone()

        if not resultado:
            print(f"No se encontró el vehículo {placa} o no está dentro para calcular el costo.")
            return 0

        hora_ingreso, tipo = resultado
        hora_ingreso_dt = datetime.strptime(hora_ingreso, "%Y-%m-%d %H:%M:%S")
        hora_salida_dt = datetime.now()

        tiempo_transcurrido = (hora_salida_dt - hora_ingreso_dt).total_seconds() / 60
        print(f"Tiempo transcurrido para {placa}: {tiempo_transcurrido} minutos")

        cursor.execute("SELECT valor_minuto FROM tarifas WHERE tipo = ?", (tipo,))
        tarifa_resultado = cursor.fetchone()
        if not tarifa_resultado:
            print(f"No se encontró tarifa para el tipo {tipo}.")
            return 0
        tarifa = tarifa_resultado[0]
        print(f"Tarifa obtenida para {tipo}: {tarifa} por minuto")

        costo_base = round(tarifa * tiempo_transcurrido)
        print(f"Costo base para {placa} ({tipo}): {costo_base}")

        costo_final = costo_base
        print(f"Convenio recibido: '{convenio}'")
        if convenio != "NINGUNO" and convenios_dict and convenio in convenios_dict:
            valor_convenio = convenios_dict[convenio]["valor"]
            costo_final = valor_convenio
            print(f"Aplicado {convenio} con valor fijo: costo final = {costo_final}")
        else:
            print(f"Sin convenio activo o no encontrado en convenios_dict. Usando costo base: {costo_final}")

        costo_final = max(0, costo_final)
        print(f"Costo final devuelto para {placa}: {costo_final}")
        return costo_final
    except Exception as e:
        print(f"Error al calcular costo para {placa}: {str(e)}")
        return 0
    finally:
        if conn:
            conn.close()

def obtener_estadisticas_cierre():
    """Obtiene las estadísticas generales del parqueadero desde el inicio de los registros."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            raise Exception("No se pudo conectar a la base de datos")
        cursor = conn.cursor()
        print("Ejecutando consulta en obtener_estadisticas_cierre para estadísticas generales")
        cursor.execute('''
            SELECT 
                SUM(monto) AS total_ingresos,
                COUNT(*) AS vehiculos_atendidos,
                SUM(CASE WHEN convenio != 'NINGUNO' THEN 1 ELSE 0 END) AS cortesias
            FROM registros 
            WHERE evento = 'FACTURACIÓN'
        ''')
        result = cursor.fetchone()

        estadisticas = {
            "total_ingresos": result[0] or 0,
            "vehiculos_atendidos": result[1] or 0,
            "cortesias": result[2] or 0
        }
        return estadisticas
    except Exception as e:
        print(f"Error en obtener_estadisticas_cierre: {str(e)}")
        raise Exception(f"Error al obtener estadísticas generales: {str(e)}")
    finally:
        if conn:
            conn.close()

def obtener_estadisticas_sesion(sesion_id):
    """Obtiene las estadísticas de una sesión específica."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return {"total_ingresos": 0, "vehiculos_atendidos": 0, "cortesias": 0}
        cursor = conn.cursor()
        print(f"Ejecutando consulta en obtener_estadisticas_sesion para sesion_id: {sesion_id}")
        cursor.execute('''
            SELECT 
                SUM(monto) AS total_ingresos,
                COUNT(*) AS vehiculos_atendidos,
                SUM(CASE WHEN convenio != 'NINGUNO' THEN 1 ELSE 0 END) AS cortesias
            FROM registros 
            WHERE evento = 'FACTURACIÓN' AND sesion_id = ?
        ''', (sesion_id,))
        result = cursor.fetchone()

        estadisticas = {
            "total_ingresos": result[0] or 0,
            "vehiculos_atendidos": result[1] or 0,
            "cortesias": result[2] or 0
        }
        return estadisticas
    except Exception as e:
        print(f"Error en obtener_estadisticas_sesion: {str(e)}")
        return {"total_ingresos": 0, "vehiculos_atendidos": 0, "cortesias": 0}
    finally:
        if conn:
            conn.close()

def obtener_facturados_por_sesion(sesion_id):
    """Obtiene los vehículos facturados en una sesión específica."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            raise Exception("No se pudo conectar a la base de datos")
        cursor = conn.cursor()
        print(f"Ejecutando consulta en obtener_facturados_por_sesion con sesion_id: {sesion_id}")
        cursor.execute('''
            SELECT placa, fecha_hora, monto
            FROM registros
            WHERE sesion_id = ? AND evento = 'FACTURACIÓN'
        ''', (sesion_id,))
        facturados = cursor.fetchall()
        return facturados
    except Exception as e:
        print(f"Error en obtener_facturados_por_sesion: {str(e)}")
        raise Exception(f"Error al obtener facturados: {str(e)}")
    finally:
        if conn:
            conn.close()

def actualizar_tarifa(tipo, nuevo_valor):
    """Actualiza el valor de la tarifa para un tipo de vehículo."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return
        cursor = conn.cursor()
        cursor.execute("UPDATE tarifas SET valor_minuto = ? WHERE tipo = ?", (nuevo_valor, tipo))
        conn.commit()
    except Exception as e:
        print(f"Error al actualizar tarifa: {str(e)}")
    finally:
        if conn:
            conn.close()

def obtener_tarifas():
    """Obtiene todas las tarifas registradas."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute("SELECT tipo, valor_minuto FROM tarifas")
        tarifas = cursor.fetchall()
        return tarifas
    except Exception as e:
        print(f"Error al obtener tarifas: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def agregar_convenio(nombre, valor):
    """Agrega un nuevo convenio a la base de datos."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return
        cursor = conn.cursor()
        cursor.execute("INSERT INTO convenios (nombre, valor) VALUES (?, ?)", (nombre, valor))
        conn.commit()
    except Exception as e:
        print(f"Error al agregar convenio: {str(e)}")
    finally:
        if conn:
            conn.close()

def eliminar_convenio(nombre):
    """Elimina un convenio de la base de datos."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return
        cursor = conn.cursor()
        cursor.execute("DELETE FROM convenios WHERE nombre = ?", (nombre,))
        conn.commit()
    except Exception as e:
        print(f"Error al eliminar convenio: {str(e)}")
    finally:
        if conn:
            conn.close()

def obtener_convenios():
    """Obtiene todos los convenios registrados."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, valor FROM convenios")
        convenios = cursor.fetchall()
        return convenios
    except Exception as e:
        print(f"Error al obtener convenios: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def verificar_base_de_datos():
    """Verifica si la base de datos existe."""
    db_path = get_resource_path("data/parqueadero.db")
    if os.path.exists(db_path):
        print(f"La base de datos '{db_path}' existe.")
    else:
        print(f"Advertencia: La base de datos '{db_path}' no existe todavía.")

def obtener_registros_facturacion_por_placa(placa):
    """Obtiene los registros de facturación para una placa específica."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT placa, tipo, hora_ingreso, hora_salida, monto, convenio, sesion_id, ticket_id
            FROM historial_vehiculos
            WHERE placa = ? AND estado = 'FUERA'
            ORDER BY hora_salida DESC
        ''', (placa,))
        registros = cursor.fetchall()
        print(f"Registros encontrados para placa {placa}: {registros}")  # Depuración
        return registros
    except Exception as e:
        print(f"Error en obtener_registros_facturacion_por_placa: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def obtener_sesiones_cerradas():
    """Obtiene todas las sesiones cerradas con su información completa."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return []
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, usuario, fecha_inicio, fecha_cierre
            FROM sesiones
            WHERE estado = 'CERRADA'
            ORDER BY fecha_cierre DESC
        ''')
        sesiones = cursor.fetchall()
        return sesiones
    except Exception as e:
        print(f"Error al obtener sesiones cerradas: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def obtener_facturaciones(placa=None, fecha=None):
    """Obtiene las facturaciones con opción de filtrado."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return []
        cursor = conn.cursor()
        
        query = '''
            SELECT r.id, v.placa, r.fecha_hora, v.tipo, 
                   (strftime('%s', v.hora_salida) - strftime('%s', v.hora_ingreso))/60 as minutos,
                   r.monto, r.convenio
            FROM registros r
            JOIN historial_vehiculos v ON r.placa = v.placa AND r.fecha_hora = v.hora_salida
            WHERE r.evento = 'FACTURACIÓN'
        '''
        
        params = []
        
        if placa:
            query += " AND v.placa LIKE ?"
            params.append(f"%{placa}%")
            
        if fecha:
            query += " AND date(r.fecha_hora) = ?"
            params.append(fecha)
            
        query += " ORDER BY r.fecha_hora DESC"
        
        cursor.execute(query, params)
        facturaciones = cursor.fetchall()
        return facturaciones
    except Exception as e:
        print(f"Error al obtener facturaciones: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def actualizar_facturacion(id_factura, nuevo_valor):
    """Actualiza el valor de una facturación en todas las tablas relevantes."""
    conn = None
    try:
        conn = conectar()
        if conn is None:
            return False
        cursor = conn.cursor()
        
        # Obtener información de la factura
        cursor.execute('''
            SELECT placa, fecha_hora FROM registros WHERE id = ? AND evento = 'FACTURACIÓN'
        ''', (id_factura,))
        factura = cursor.fetchone()
        
        if not factura:
            return False
            
        placa, fecha_hora = factura
        
        # Actualizar en registros
        cursor.execute('''
            UPDATE registros SET monto = ? 
            WHERE id = ? AND evento = 'FACTURACIÓN'
        ''', (nuevo_valor, id_factura))
        
        # Actualizar en historial_vehiculos
        cursor.execute('''
            UPDATE historial_vehiculos SET monto = ?
            WHERE placa = ? AND hora_salida = ?
        ''', (nuevo_valor, placa, fecha_hora))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al actualizar facturación: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

# Ejecutar la creación de tablas y verificar (opcional para pruebas)
if __name__ == "__main__":
    import os
    db_path = get_resource_path("data/parqueadero.db")
    if os.path.exists(db_path):
        os.remove(db_path)  # Elimina la base de datos antigua para pruebas
    crear_tablas()
    verificar_base_de_datos()