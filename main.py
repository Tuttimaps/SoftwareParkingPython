import tkinter as tk
from tkinter import ttk, messagebox
import os
from PIL import Image, ImageTk
import time
from database import (
    conectar, crear_tablas, insertar_vehiculo, registrar_evento_sesion,
    registrar_salida, contar_vehiculos_dentro, contar_vehiculos_por_tipo,
    obtener_estado_vehiculo, calcular_costo, obtener_hora_ingreso,
    obtener_estadisticas_cierre, obtener_facturados_por_sesion, obtener_sesion_actual,
    obtener_estadisticas_sesion, obtener_convenios,
    obtener_sesiones_cerradas, obtener_registros_facturacion_por_placa
)
import re
import sqlite3
from datetime import datetime, timedelta
from estadisticas import EstadisticasApp
from generar_ticket import generar_ticket_qr
from generar_recibo import generar_recibo_termico
from configuracion import ConfiguracionApp
from generar_recibo_cierre import generar_recibo_cierre

# Variables globales para manejar el estado de la sesión
sesion_iniciada = False
usuario_actual = None
datos_facturacion = {}
fecha_inicio_sesion = None
sesion_id_actual = None 
current_frame = None  # Para rastrear el frame actual

# Función para ocultar todas las pantallas
def ocultar_todo():
    global current_frame
    usuarios_frame.grid_forget()
    notebook.grid_forget()
    pantalla_vacia.grid_forget()
    if current_frame:
        current_frame.grid_forget()
        current_frame.destroy()
        current_frame = None

# Función para determinar el tipo de vehículo
def determinar_tipo_vehiculo(placa):
    if re.match(r"^BICI\d{2}$", placa):
        return "Bicicleta"
    elif re.match(r"^[A-Za-z]{3}\d{2}[A-Za-z]$", placa):
        return "Motocicleta"
    elif re.match(r"^[A-Za-z]{3}\d{3}$", placa):
        return "Automóvil"
    else:
        return "Desconocido"

# Función para actualizar el tipo de vehículo
def actualizar_tipo_vehiculo(event=None):
    placa = placa_codigo_text.get("1.0", "end-1c").strip().upper()
    tipo = determinar_tipo_vehiculo(placa)
    tipo_vehiculo.set(tipo)

# Función para convertir el texto en mayúsculas
def convertir_a_mayusculas(event):
    texto_actual = placa_codigo_text.get("1.0", "end-1c")
    placa_codigo_text.delete("1.0", "end")
    placa_codigo_text.insert("1.0", texto_actual.upper())
    actualizar_tipo_vehiculo()

# Función para ingresar un vehículo
def ingresar_vehiculo():
    placa = placa_codigo_text.get("1.0", "end-1c").strip().upper()
    if not placa:
        messagebox.showerror("Error", "Ingrese una placa válida.")
        return

    tipo = tipo_vehiculo.get()
    hora_ingreso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ticket_id = f"TICKET-{placa}"

    exito, mensaje = insertar_vehiculo(placa, tipo, hora_ingreso, ticket_id)

    if exito:
        messagebox.showinfo("Éxito", mensaje)
        actualizar_conteo_vehiculos()

        resultado = generar_ticket_qr(placa, tipo, hora_ingreso, ticket_id)
        if "impreso correctamente" in resultado:
            messagebox.showinfo("Éxito", "Ticket de ingreso impreso correctamente.")
        else:
            messagebox.showerror("Error", resultado)

        placa_codigo_text.delete("1.0", "end")
    else:
        messagebox.showerror("Error", mensaje)

# Función para actualizar el historial de ingresos
def actualizar_historial_ingresos(placa, tipo, hora):
    historial_ingresos_text.config(state=tk.NORMAL)
    historial_ingresos_text.insert(tk.END, f"{hora} - {tipo}: {placa}\n")
    historial_ingresos_text.config(state=tk.DISABLED)

# Función para mostrar vehículos ingresados durante la sesión actual
def mostrar_vehiculos_diarios():
    historial_ingresos_text.config(state=tk.NORMAL)
    historial_ingresos_text.delete("1.0", tk.END)
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT placa, tipo, hora_ingreso FROM vehiculos
        WHERE estado = 'DENTRO' AND hora_ingreso >= (SELECT fecha_hora FROM sesiones WHERE usuario = ? ORDER BY id DESC LIMIT 1)
    ''', (usuario_actual,))
    vehiculos = cursor.fetchall()
    for vehiculo in vehiculos:
        placa, tipo, hora_ingreso = vehiculo
        hora_ingreso = datetime.strptime(hora_ingreso, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        historial_ingresos_text.insert(tk.END, f"{hora_ingreso} - {tipo}: {placa}\n")
    historial_ingresos_text.config(state=tk.DISABLED)
    conexion.close()

# Función para mostrar todos los vehículos dentro
def mostrar_vehiculos_totales():
    historial_ingresos_text.config(state=tk.NORMAL)
    historial_ingresos_text.delete("1.0", tk.END)
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT placa, tipo, hora_ingreso FROM vehiculos WHERE estado = 'DENTRO'
    ''')
    vehiculos = cursor.fetchall()
    for vehiculo in vehiculos:
        placa, tipo, hora_ingreso = vehiculo
        hora_ingreso = datetime.strptime(hora_ingreso, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        historial_ingresos_text.insert(tk.END, f"{hora_ingreso} - {tipo}: {placa}\n")
    historial_ingresos_text.config(state=tk.DISABLED)
    conexion.close()

# Función para eliminar un registro de vehículo (historial y base de datos)
def limpiar_registro():
    placa_a_eliminar = placa_codigo_text.get("1.0", "end-1c").strip().upper()
    if not placa_a_eliminar:
        messagebox.showerror("Error", "Por favor, ingrese una placa para eliminar.")
        return

    estado = obtener_estado_vehiculo(placa_a_eliminar)
    if estado == 'DENTRO':
        hora_salida = time.strftime("%Y-%m-%d %H:%M:%S")
        convenio = opcion_seleccionada.get()
        costo = calcular_costo(placa_a_eliminar, convenio)
        exito, mensaje = registrar_salida(placa_a_eliminar, hora_salida, costo, convenio)
        if exito:
            messagebox.showinfo("Eliminación", f"Vehículo {placa_a_eliminar} eliminado.")
            actualizar_historial_ingresos(placa_a_eliminar, "Eliminado", hora_salida)
            actualizar_conteo_vehiculos()
        else:
            messagebox.showerror("Error", mensaje)
    else:
        messagebox.showerror("Error", f"El vehículo con placa {placa_a_eliminar} no está dentro.")

# Función para actualizar el conteo de vehículos en tiempo real
def actualizar_conteo_vehiculos():
    sesion_id = None
    if sesion_iniciada:
        conexion = conectar()
        cursor = conexion.cursor()
        sesion_id = cursor.execute('''SELECT id FROM sesiones ORDER BY id DESC LIMIT 1''').fetchone()[0]
        conexion.close()

    autos = contar_vehiculos_por_tipo("Automóvil", sesion_id)
    motos = contar_vehiculos_por_tipo("Motocicleta", sesion_id)
    bicis = contar_vehiculos_por_tipo("Bicicleta", sesion_id)
    capacidad_auto.set(f"Automóvil: {autos}/100")
    capacidad_moto.set(f"Motocicleta: {motos}/100")
    capacidad_bici.set(f"Bicicleta: {bicis}/100")





# Crear la ventana principal
root = tk.Tk()


# Función para manejar el cierre de la ventana
def on_closing():
    global sesion_iniciada, sesion_id_actual, usuario_actual
    if sesion_iniciada and sesion_id_actual:
        respuesta = messagebox.askyesno(
            "Confirmar Cierre",
            "¿Está seguro que desea cerrar la aplicación? Esto cerrará la sesión actual y generará el reporte final."
        )
        if respuesta:
            try:
                # Verificar que usuario_actual no sea None
                if usuario_actual is None:
                    messagebox.showerror("Error", "No se encontró un usuario activo. Cierre de sesión fallido.")
                    root.destroy()
                    return

                # Ejecutar la lógica de generar_reporte
                estadisticas = obtener_estadisticas_sesion(sesion_id_actual)
                
                conexion = conectar()
                cursor = conexion.cursor()

                # Obtener resumen por tipo de vehículo
                cursor.execute('''
                    SELECT tipo, COUNT(*) as cantidad, SUM(monto) as total
                    FROM historial_vehiculos
                    WHERE sesion_id = ? AND estado = 'FUERA'
                    GROUP BY tipo
                ''', (sesion_id_actual,))
                resumen_por_tipo = cursor.fetchall()

                # Obtener total de convenios
                cursor.execute('''
                    SELECT COUNT(*)
                    FROM historial_vehiculos
                    WHERE sesion_id = ? AND convenio != 'NINGUNO'
                ''', (sesion_id_actual,))
                total_convenios = cursor.fetchone()[0]

                # Obtener vehículos dentro
                cursor.execute('''
                    SELECT COUNT(*)
                    FROM vehiculos
                    WHERE sesion_id = ? AND estado = 'DENTRO'
                ''', (sesion_id_actual,))
                vehiculos_dentro = cursor.fetchone()[0] or 0

                # Obtener vehículos facturados
                cursor.execute('''
                    SELECT COUNT(*)
                    FROM historial_vehiculos
                    WHERE sesion_id = ?
                ''', (sesion_id_actual,))
                vehiculos_facturados = cursor.fetchone()[0] or 0

                total_vehiculos_ingresados = vehiculos_dentro + vehiculos_facturados

                # Obtener fecha de inicio de la sesión
                cursor.execute('''
                    SELECT fecha_inicio FROM sesiones WHERE id = ? AND estado = 'ACTIVA'
                ''', (sesion_id_actual,))
                resultado = cursor.fetchone()
                
                if not resultado or not resultado[0]:
                    messagebox.showerror("Error", "No se pudo obtener la fecha de inicio de la sesión")
                    conexion.close()
                    root.destroy()
                    return

                inicio = resultado[0]
                inicio_dt = datetime.strptime(inicio, "%Y-%m-%d %H:%M:%S")
                cierre_dt = datetime.now()
                duracion = cierre_dt - inicio_dt
                horas, rem = divmod(duracion.total_seconds(), 3600)
                minutos = rem // 60
                duracion_turno = f"{int(horas)}h {int(minutos)}min"

                # Preparar datos para el recibo de cierre
                datos_cierre = {
                    "ticket_id": f"TICKET-CIERRE-{sesion_id_actual}",
                    "usuario": usuario_actual,  # Ahora estamos seguros de que tiene un valor
                    "hora_inicio": inicio,
                    "hora_cierre": cierre_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "duracion_turno": duracion_turno,
                    "total_ingresos": estadisticas['total_ingresos'],
                    "vehiculos_atendidos": estadisticas['vehiculos_atendidos'],
                    "cortesias": estadisticas['cortesias'],
                    "total_convenios": total_convenios,
                    "resumen_por_tipo": resumen_por_tipo,
                    "total_vehiculos_ingresados": total_vehiculos_ingresados
                }

                # Generar recibo de cierre
                resultado = generar_recibo_cierre(datos_cierre)
                if "impreso correctamente" in resultado:
                    messagebox.showinfo("Éxito", "Recibo de cierre impreso correctamente.")
                else:
                    messagebox.showerror("Error", resultado)

                # Actualizar estado de la sesión
                cursor.execute('''
                    UPDATE sesiones 
                    SET estado = 'CERRADA', fecha_cierre = ?
                    WHERE id = ? AND estado = 'ACTIVA'
                ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sesion_id_actual))
                conexion.commit()

                # Cerrar sesión
                sesion_iniciada = False
                usuario_actual = None
                sesion_id_actual = None
                ocultar_todo()
                usuarios_frame.grid(row=0, column=0, sticky="nsew")
                messagebox.showinfo("Info", "Sesión cerrada al cerrar la aplicación")

                conexion.close()
            except Exception as e:
                messagebox.showerror("Error", f"Error al cerrar la sesión: {str(e)}")
                if 'conexion' in locals():
                    conexion.close()
        else:
            # Si el usuario cancela, no cerrar la ventana
            return
    # Si no hay sesión activa, cerrar directamente
    root.destroy()

# Vincular el manejador al evento de cierre
root.protocol("WM_DELETE_WINDOW", on_closing)


root.title("TOBERINPARKING")
root.geometry("1500x700")
root.configure(bg="#1e1e1e")

# Configurar el grid de la ventana principal
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(1, weight=1)

# Estilos para los widgets
style = ttk.Style()
style.theme_use("clam")

style.configure("TFrame", background="#1e1e1e")
style.configure("TLabel", background="#1e1e1e", foreground="white", font=("Arial", 12))
style.configure("TButton", background="#0056b3", foreground="white", padding=10, font=("Arial", 14))
style.configure("TCombobox", fieldbackground="#333333", background="#333333", foreground="white")
style.configure("TRadiobutton", background="#1e1e1e", foreground="white")
style.configure("TEntry", fieldbackground="#333333", foreground="white")

style.configure("TNotebook.Tab",
                padding=[60, 10],
                font=("Arial", 16, "bold"),
                width=40,
                background="#0056b3",
                foreground="white")

style.map("TNotebook.Tab",
          background=[("selected", "#0056b3")],
          foreground=[("selected", "white")])

style.configure("Custom.TRadiobutton", font=("Arial", 10))
style.configure("BotonGrande.TButton", font=("Arial", 16))

from utils import get_resource_path  # Asegúrate de importar esto al inicio de main.py
from PIL import Image, ImageTk  # Ya deberías tener estos importados

# Cargar la imagen (versión portable)
try:
    # Obtener la ruta relativa a Logo2.png usando get_resource_path
    imagen_path = get_resource_path("Logo2.png")
    
    # Cargar y procesar la imagen
    imagen = Image.open(imagen_path)
    imagen = imagen.resize((100, 100), Image.Resampling.LANCZOS)
    imagen_tk = ImageTk.PhotoImage(imagen)
    root.imagen_tk = imagen_tk  # Guardar referencia para evitar garbage collection
    
except Exception as e:
    print(f"Error al cargar la imagen: {str(e)}")
    imagen_tk = None
    # Opcional: Crear una imagen placeholder si falla la carga
    try:
        imagen = Image.new('RGB', (100, 100), color='gray')
        imagen_tk = ImageTk.PhotoImage(imagen)
        root.imagen_tk = imagen_tk
    except Exception as e2:
        print(f"No se pudo crear imagen placeholder: {str(e2)}")
        imagen_tk = None

# Función para actualizar el reloj
def actualizar_reloj():
    hora_actual = time.strftime("%H:%M:%S")
    reloj_label.config(text=hora_actual)
    root.after(1000, actualizar_reloj)

# Variables
tipo_vehiculo = tk.StringVar()
capacidad_auto = tk.StringVar()
capacidad_moto = tk.StringVar()
capacidad_bici = tk.StringVar()

# Marco para la fila superior
marco_superior = ttk.Frame(root, relief="solid", borderwidth=2, style="Marco.TFrame")
marco_superior.grid(row=0, column=0, columnspan=2, sticky="ew", pady=10)

# Mostrar la imagen
if imagen_tk:
    imagen_label = ttk.Label(marco_superior, image=imagen_tk)
    imagen_label.pack(side=tk.LEFT, padx=10)

# Marco para el título
marco_titulo = ttk.Frame(marco_superior, relief="solid", borderwidth=2, style="Marco.TFrame")
marco_titulo.pack(side=tk.LEFT, padx=20, expand=True)

# Título "PARQUEADERO TOBERÍN" dentro del marco
titulo_label = ttk.Label(marco_titulo, text="PARQUEADERO TOBERÍN", font=("Helvetica", 40, "bold"))
titulo_label.pack(padx=10, pady=10)

# Recuadro para el reloj
reloj_frame = ttk.Frame(marco_superior, relief="solid", borderwidth=2, style="Marco.TFrame")
reloj_frame.pack(side=tk.RIGHT, padx=40)

reloj_label = ttk.Label(reloj_frame, font=("Arial", 30, "bold"))
reloj_label.pack(padx=10, pady=5)
actualizar_reloj()

# Panel Lateral
panel_lateral = ttk.Frame(root, width=300, relief="solid", borderwidth=2, style="Marco.TFrame")
panel_lateral.grid(row=1, column=0, sticky="ns", padx=5, pady=5)

ttk.Label(panel_lateral, text="", font=("Arial", 20)).pack(pady=50)

# Contenido Principal
contenido_principal = ttk.Frame(root)
contenido_principal.grid(row=1, column=1, sticky="nsew")
contenido_principal.grid_rowconfigure(0, weight=1)
contenido_principal.grid_columnconfigure(0, weight=1)

# Crear un Notebook (pestañas) en el contenido principal
notebook = ttk.Notebook(contenido_principal)

# Crear la pantalla de usuarios
usuarios_frame = ttk.Frame(contenido_principal)

# Título de la pantalla de usuarios
titulo_usuarios = ttk.Label(usuarios_frame, text="GESTIÓN DE USUARIOS", font=("Helvetica", 24, "bold"))
titulo_usuarios.pack(pady=20)

# Combobox para seleccionar el usuario
ttk.Label(usuarios_frame, text="Seleccione el usuario:", font=("Arial", 16)).pack(pady=10)
usuarios_combobox = ttk.Combobox(usuarios_frame, values=["Usuario 1", "Usuario 2", "Usuario 3"], font=("Arial", 14))
usuarios_combobox.pack(pady=10)
usuarios_combobox.current(0)

# Campo de entrada para la clave
ttk.Label(usuarios_frame, text="Clave:", font=("Arial", 16)).pack(pady=10)
clave_entry = ttk.Entry(usuarios_frame, font=("Arial", 14), show="*")
clave_entry.pack(pady=10)

# Función para validar la sesión
def validar_sesion():
    global sesion_iniciada, usuario_actual, sesion_id_actual
    
    usuario_seleccionado = usuarios_combobox.get().strip()
    clave = clave_entry.get().strip()

    # Verificar si ya hay una sesión activa
    if sesion_iniciada:
        messagebox.showinfo("Información", "Ya hay una sesión activa")
        return

    # Diccionario de usuarios (mejor almacenado en la base de datos)
    usuarios = {
        "Usuario 1": "clave1",
        "Usuario 2": "clave2",
        "Usuario 3": "clave3"
    }

    # Validar credenciales
    if usuario_seleccionado in usuarios and usuarios[usuario_seleccionado] == clave:
        try:
            fecha_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Registrar el evento de inicio de sesión
            exito, mensaje, sesion_id = registrar_evento_sesion(usuario_seleccionado, "Inicio", fecha_inicio)
            
            if exito:
                sesion_id_actual = sesion_id
                sesion_iniciada = True
                usuario_actual = usuario_seleccionado
                messagebox.showinfo("Éxito", "Sesión iniciada correctamente")
                mostrar_modulos()  # Asegurarse de que esta función actualiza la interfaz
            else:
                messagebox.showerror("Error", mensaje)
                
        except Exception as e:
            messagebox.showerror("Error crítico", f"Falla inesperada: {str(e)}")
    else:
        messagebox.showerror("Error", "Usuario o clave incorrectos")



# Función para cerrar sesión
def cerrar_sesion():
    global sesion_iniciada, usuario_actual, sesion_id_actual, current_frame
    if sesion_iniciada:
        registrar_evento_sesion(usuario_actual, "Cierre", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        sesion_iniciada = False
        usuario_actual = None
        sesion_id_actual = None
        ocultar_todo()
        usuarios_frame.grid(row=0, column=0, sticky="nsew")
        messagebox.showinfo("Info", "Sesión cerrada")
    else:
        messagebox.showerror("Error", "No hay una sesión activa para cerrar")

# Función para mostrar módulos (pestañas)
def mostrar_modulos():
    global sesion_iniciada, current_frame
    if sesion_iniciada:
        ocultar_todo()
        notebook.grid(row=0, column=0, sticky="nsew")
    else:
        messagebox.showerror("Error", "Debes iniciar sesión para acceder a los módulos")

# Función para mostrar pantalla de usuarios
def mostrar_usuarios():
    global sesion_iniciada
    
    if sesion_iniciada:
        messagebox.showinfo("Información", "Ya hay una sesión activa. Cierre la sesión actual primero.")
        return
    
    ocultar_todo()
    usuarios_frame.grid(row=0, column=0, sticky="nsew")
    
    # Deshabilitar combobox y botón si ya hay sesión
    usuarios_combobox.config(state="normal" if not sesion_iniciada else "disabled")
    validar_button.config(state="normal" if not sesion_iniciada else "disabled")

# Función para mostrar estadísticas
def mostrar_estadisticas():
    global sesion_iniciada, current_frame
    if sesion_iniciada:
        ocultar_todo()
        current_frame = EstadisticasApp(contenido_principal)
        current_frame.grid(row=0, column=0, sticky="nsew")
    else:
        messagebox.showerror("Error", "Debes iniciar sesión para acceder a las estadísticas")

# Función para mostrar configuración
def mostrar_configuracion():
    global sesion_iniciada, usuario_actual, current_frame
    if sesion_iniciada:
        ocultar_todo()
        current_frame = ConfiguracionApp(contenido_principal, usuario_actual)  # Pasar el usuario actual
        current_frame.grid(row=0, column=0, sticky="nsew")
    else:
        messagebox.showerror("Error", "Debes iniciar sesión para acceder a la configuración")

# Botón para validar la clave
validar_button = ttk.Button(usuarios_frame, text="VALIDAR", style="TButton", command=validar_sesion)
validar_button.pack(pady=20)

# Crear la pantalla vacía (para estadísticas y configuración)
pantalla_vacia = ttk.Frame(contenido_principal)

# Título de la pantalla vacía
titulo_vacio = ttk.Label(pantalla_vacia, text="EN CONSTRUCCIÓN", font=("Helvetica", 24, "bold"))
titulo_vacio.pack(pady=20)

# Ocultar todas las pantallas al inicio
notebook.grid_forget()
usuarios_frame.grid(row=0, column=0, sticky="nsew")
pantalla_vacia.grid_forget()

# Botones del panel lateral
ttk.Button(panel_lateral, text="MÓDULOS", command=mostrar_modulos, style="TButton").pack(fill=tk.X, pady=15)
ttk.Button(panel_lateral, text="USUARIOS", command=mostrar_usuarios, style="TButton").pack(fill=tk.X, pady=15)
ttk.Button(panel_lateral, text="ESTADÍSTICAS", command=mostrar_estadisticas, style="TButton").pack(fill=tk.X, pady=15)
ttk.Button(panel_lateral, text="CONFIGURACIÓN", command=mostrar_configuracion, style="TButton").pack(fill=tk.X, pady=15)

# Pestaña de Ingresos
ingresos_frame = ttk.Frame(notebook)
notebook.add(ingresos_frame, text="INGRESOS")

# Ajustar el espaciado vertical general en el frame de ingresos
ingresos_frame.grid_rowconfigure(0, weight=1, pad=20)
ingresos_frame.grid_rowconfigure(5, weight=1, pad=20)

# Campo para "PLACA O CÓDIGO"
ttk.Label(ingresos_frame, text="PLACA O CÓDIGO:", font=("Arial", 20)).grid(row=0, column=0, sticky=tk.W, padx=10, pady=20)
placa_codigo_text = tk.Text(ingresos_frame, font=("Arial", 60, "bold"), height=1, width=10, bg="#FFFF99")
placa_codigo_text.grid(row=0, column=1, sticky=tk.W, padx=10, pady=20)

placa_codigo_text.bind("<KeyRelease>", convertir_a_mayusculas)

# Opciones para seleccionar el tipo de vehículo
ttk.Label(ingresos_frame, text="TIPO DE VEHÍCULO:", font=("Arial", 20)).grid(row=1, column=0, sticky=tk.W, padx=10, pady=20)
tipo_vehiculo_combobox = ttk.Combobox(ingresos_frame, values=["Automóvil", "Motocicleta", "Bicicleta"], font=("Arial", 16), width=20, textvariable=tipo_vehiculo)
tipo_vehiculo_combobox.grid(row=1, column=1, sticky=tk.W, padx=10, pady=20)
tipo_vehiculo_combobox.current(0)

# Capacidad de los vehículos
ttk.Label(ingresos_frame, textvariable=capacidad_auto, font=("Arial", 14)).grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
ttk.Label(ingresos_frame, textvariable=capacidad_moto, font=("Arial", 14)).grid(row=3, column=0, sticky=tk.W, padx=10, pady=10)
ttk.Label(ingresos_frame, textvariable=capacidad_bici, font=("Arial", 14)).grid(row=4, column=0, sticky=tk.W, padx=10, pady=10)

# Botones de acción en Ingresos
ingresar_button = ttk.Button(ingresos_frame, text="INGRESAR", style="TButton", command=ingresar_vehiculo)
ingresar_button.grid(row=5, column=0, pady=20, padx=10)
limpiar_button = ttk.Button(ingresos_frame, text="LIMPIAR", style="TButton", command=limpiar_registro)
limpiar_button.grid(row=5, column=1, pady=20, padx=10)

# Botones Diario/Total
btn_frame = ttk.Frame(ingresos_frame)
btn_frame.grid(row=6, column=2, pady=10)
ttk.Button(btn_frame, text="Diario", command=mostrar_vehiculos_diarios).pack(side=tk.LEFT, padx=5)
ttk.Button(btn_frame, text="Total", command=mostrar_vehiculos_totales).pack(side=tk.LEFT, padx=5)

# Panel de Historial en Ingresos
panel_historial_ingresos = ttk.Frame(ingresos_frame, relief="solid", borderwidth=2, style="Marco.TFrame")
panel_historial_ingresos.grid(row=0, column=2, rowspan=6, sticky="ns", padx=60, pady=20)

ttk.Label(panel_historial_ingresos, text="HISTORIAL DE INGRESOS", font=("Arial", 16, "bold")).pack(pady=10)
historial_ingresos_text = tk.Text(panel_historial_ingresos, font=("Arial", 12), height=20, width=40, state=tk.DISABLED)
historial_ingresos_text.pack(padx=10, pady=10)

# Pestaña de Caja
caja_frame = ttk.Frame(notebook)
notebook.add(caja_frame, text="CAJA")

# Configurar el grid para la pestaña de Caja
caja_frame.grid_columnconfigure(0, weight=1)
caja_frame.grid_columnconfigure(1, weight=1)
caja_frame.grid_columnconfigure(2, weight=1)
caja_frame.grid_columnconfigure(3, weight=1)
caja_frame.grid_rowconfigure(0, weight=1)
caja_frame.grid_rowconfigure(1, weight=1)
caja_frame.grid_rowconfigure(2, weight=1)
caja_frame.grid_rowconfigure(3, weight=1)
caja_frame.grid_rowconfigure(4, weight=1)
caja_frame.grid_rowconfigure(5, weight=1)
caja_frame.grid_rowconfigure(6, weight=1)

# Variables necesarias
pago = tk.StringVar(value="EFECTIVO")
opcion_seleccionada = tk.StringVar(value="NINGUNO")

# Función para cargar los convenios desde la base de datos
def cargar_convenios():
    global convenios_dict
    convenios = obtener_convenios()
    convenios_dict = {convenio[0]: {"valor": convenio[1]} for convenio in convenios}
    opciones = ["NINGUNO"] + [convenio[0] for convenio in convenios]
    menu_convenio['menu'].delete(0, 'end')
    for opcion in opciones:
        menu_convenio['menu'].add_command(label=opcion, command=tk._setit(opcion_seleccionada, opcion))
    opcion_seleccionada.set("NINGUNO")

# Convenio
ttk.Label(caja_frame, text="CONVENIO:", font=("Arial", 20)).grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
menu_convenio = tk.OptionMenu(caja_frame, opcion_seleccionada, "NINGUNO")
menu_convenio.config(font=("Arial", 20))
menu_convenio.grid(row=0, column=1, sticky=tk.W, padx=10, pady=10)
cargar_convenios()

# Botón para actualizar convenios manualmente
ttk.Button(caja_frame, text="Actualizar Convenios", style="TButton", command=cargar_convenios).grid(row=0, column=2, sticky=tk.W, padx=10, pady=10)

# Método de pago
ttk.Label(caja_frame, text="PAGO EN:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, padx=10, pady=10)
ttk.Radiobutton(caja_frame, text="EFECTIVO", variable=pago, value="EFECTIVO", style="Custom.TRadiobutton").grid(row=1, column=1, sticky=tk.W, padx=(10, 2), pady=10)
ttk.Radiobutton(caja_frame, text="DÉBITO", variable=pago, value="DÉBITO", style="Custom.TRadiobutton").grid(row=1, column=2, sticky=tk.W, padx=(28, 2), pady=10)
ttk.Radiobutton(caja_frame, text="CRÉDITO", variable=pago, value="CRÉDITO", style="Custom.TRadiobutton").grid(row=1, column=3, sticky=tk.W, padx=(6,2), pady=10)

# Placa o código
ttk.Label(caja_frame, text="PLACA O CÓDIGO:", font=("Arial", 16)).grid(row=2, column=0, sticky=tk.W, padx=10, pady=10)
placa_codigo_text_caja = tk.Text(caja_frame, font=("Arial", 40, "bold"), height=1, width=15, bg="#FFFF99")
placa_codigo_text_caja.grid(row=2, column=1, sticky=tk.W, padx=10, pady=10)

# Función para convertir el texto en mayúsculas
def convertir_a_mayusculas_caja(event):
    texto_actual = placa_codigo_text_caja.get("1.0", "end-1c")
    placa_codigo_text_caja.delete("1.0", "end")
    placa_codigo_text_caja.insert("1.0", texto_actual.upper())

placa_codigo_text_caja.bind("<KeyRelease>", convertir_a_mayusculas_caja)

# Función para calcular el cambio
def calcular_cambio(event=None):
    try:
        efectivo_valor = float(efectivo_entry.get().strip() or 0)
        total_valor = float(total_label.cget("text").replace("$", "").replace(",", ""))
        cambio_valor = efectivo_valor - total_valor
        cambio_label.config(text=f"${cambio_valor:,.2f}")
    except ValueError:
        cambio_label.config(text="$0.00")
        messagebox.showerror("Error", "Ingrese un valor numérico válido.")

# Actualizar historial de caja
def actualizar_historial_caja():
    historial_caja_text.config(state=tk.NORMAL)
    historial_caja_text.delete("1.0", tk.END)
    
    if sesion_id_actual:
        facturados = obtener_facturados_por_sesion(sesion_id_actual)
        for placa, hora_salida, monto in facturados:
            hora_formateada = datetime.strptime(hora_salida, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            historial_caja_text.insert(tk.END, f"{hora_formateada} - {placa}: ${monto}\n")
    
    historial_caja_text.config(state=tk.DISABLED)

def facturar():
    global datos_facturacion
    if not sesion_iniciada or sesion_id_actual is None:
        messagebox.showerror("Error", "Debe iniciar sesión para facturar.")
        return

    placa = placa_codigo_text_caja.get("1.0", "end-1c").strip().upper()
    if not placa:
        messagebox.showerror("Error", "Ingrese una placa válida.")
        return

    hora_ingreso = obtener_hora_ingreso(placa)
    if not hora_ingreso:
        messagebox.showerror("Error", "No se encontró la hora de ingreso para la placa proporcionada.")
        return

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT ticket_id FROM vehiculos WHERE placa = ? AND estado = 'DENTRO'", (placa,))
    resultado = cursor.fetchone()
    ticket_id = resultado[0] if resultado else f"TICKET-{placa}"
    conexion.close()

    convenio = opcion_seleccionada.get().strip()
    print(f"Convenio seleccionado: '{convenio}'")

    # Pasar convenios_dict a calcular_costo
    costo = calcular_costo(placa, convenio, convenios_dict)
    print(f"Costo calculado: {costo}")

    # Añadir advertencia si el costo es 0 y se seleccionó un convenio
    if costo == 0 and convenio != "NINGUNO":
        messagebox.showwarning("Advertencia", "El costo calculado es 0. Verifique el convenio seleccionado.")

    hora_salida = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    tiempo_estacionado = datetime.now() - datetime.strptime(hora_ingreso, "%Y-%m-%d %H:%M:%S")
    horas = int(tiempo_estacionado.total_seconds() // 3600)
    minutos = int((tiempo_estacionado.total_seconds() % 3600) // 60)

    hora_ingreso_formateada = datetime.strptime(hora_ingreso, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    tiempo_formateado = f"{horas}h {minutos}min"

    hora_ingreso_label.config(text=hora_ingreso_formateada)
    tiempo_transcurrido_label.config(text=tiempo_formateado)

    datos_facturacion = {
        "placa": placa,
        "hora_ingreso": hora_ingreso,
        "hora_salida": hora_salida,
        "tiempo": f"{horas}h {minutos}min",
        "costo": costo,
        "metodo_pago": pago.get(),
        "convenio": convenio,
        "ticket_id": ticket_id
    }

    exito, mensaje = registrar_salida(placa, hora_salida, costo, convenio)
    if exito:
        total_label.config(text=f"${costo:,.0f}")
        messagebox.showinfo("Facturación", f"Facturación exitosa: ${costo:,.0f}")
        actualizar_historial_caja()
        actualizar_cierre()
        opcion_seleccionada.set("NINGUNO")
    else:
        messagebox.showerror("Error", mensaje)

# Función para imprimir recibo
def imprimir_recibo():
    global datos_facturacion
    if datos_facturacion:
        resultado = generar_recibo_termico(datos_facturacion)
        if "impreso correctamente" in resultado:
            messagebox.showinfo("Éxito", "Recibo de salida impreso correctamente.")
        else:
            messagebox.showerror("Error", resultado)
    else:
        messagebox.showerror("Error", "Primero debe facturar un vehículo.")

# Función para limpiar la caja
def limpiar_caja():
    global datos_facturacion
    placa_codigo_text_caja.delete("1.0", tk.END)
    total_label.config(text="$0")
    hora_ingreso_label.config(text="")
    tiempo_transcurrido_label.config(text="")
    datos_facturacion = {}
    opcion_seleccionada.set("NINGUNO")

# Efectivo (campo de entrada)
ttk.Label(caja_frame, text="EFECTIVO:", font=("Arial", 16)).grid(row=5, column=0, sticky=tk.W, padx=10, pady=10)
efectivo_entry = ttk.Entry(caja_frame, font=("Arial", 20), width=15)
efectivo_entry.grid(row=5, column=1, sticky=tk.W, padx=10, pady=10)

# Cambio (resultado calculado)
ttk.Label(caja_frame, text="CAMBIO:", font=("Arial", 16)).grid(row=5, column=2, sticky=tk.W, padx=10, pady=10)
cambio_label = ttk.Label(caja_frame, text="$0.00", font=("Arial", 20))
cambio_label.grid(row=5, column=3, sticky=tk.W, padx=10, pady=10)

efectivo_entry.bind("<KeyRelease>", calcular_cambio)

# Total
ttk.Label(caja_frame, text="TOTAL:", font=("Arial", 16)).grid(row=3, column=0, sticky=tk.W, padx=10, pady=10)
total_label = ttk.Label(caja_frame, text="$0", font=("Arial", 30))
total_label.grid(row=3, column=1, sticky=tk.W, padx=10, pady=10)

# Botón para facturar
ttk.Button(caja_frame, text="FACTURAR", style="TButton", command=facturar).grid(row=4, column=0, columnspan=2, pady=10, padx=10)

# Botón Limpiar
ttk.Button(caja_frame, text="LIMPIAR", command=limpiar_caja).grid(row=4, column=1, pady=10, padx=(150, 1))

# Botón "IMPRIMIR"
ttk.Button(caja_frame, text="IMPRIMIR", style="TButton", command=imprimir_recibo).grid(row=4, column=2, pady=10, padx=10)

# Hora de ingreso y tiempo transcurrido
ttk.Label(caja_frame, text="H:", font=("Arial", 16)).grid(row=6, column=0, sticky=tk.W, padx=10, pady=10)
hora_ingreso_label = ttk.Label(caja_frame, text="", font=("Arial", 16))
hora_ingreso_label.grid(row=6, column=1, sticky=tk.W, padx=10, pady=10)

ttk.Label(caja_frame, text="T:", font=("Arial", 16)).grid(row=6, column=2, sticky=tk.W, padx=10, pady=10)
tiempo_transcurrido_label = ttk.Label(caja_frame, text="", font=("Arial", 16))
tiempo_transcurrido_label.grid(row=6, column=3, sticky=tk.W, padx=10, pady=10)

# Panel de Historial en Caja
panel_historial_caja = ttk.Frame(caja_frame, relief="solid", borderwidth=2, style="Marco.TFrame")
panel_historial_caja.grid(row=0, column=4, rowspan=7, sticky="ns", padx=20, pady=20)

ttk.Label(panel_historial_caja, text="HISTORIAL DE CAJA", font=("Arial", 16, "bold")).pack(pady=10)
historial_caja_text = tk.Text(panel_historial_caja, font=("Arial", 12), height=20, width=40, state=tk.DISABLED)
historial_caja_text.pack(padx=10, pady=10)

def abrir_dialogo_reimpresion():
    # Crear una ventana secundaria
    dialogo = tk.Toplevel(root)
    dialogo.title("Reimprimir Recibos")
    dialogo.geometry("800x600")
    dialogo.configure(bg="#1e1e1e")
    dialogo.transient(root)
    dialogo.grab_set()

    # Notebook para las dos opciones
    notebook_reimpresion = ttk.Notebook(dialogo)
    notebook_reimpresion.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Pestaña 1: Reimprimir recibo de facturación (se mantiene igual)
    frame_facturacion = ttk.Frame(notebook_reimpresion)
    notebook_reimpresion.add(frame_facturacion, text="Recibo de Facturación")

    # Campo para ingresar la placa
    ttk.Label(frame_facturacion, text="Ingrese la Placa:", font=("Arial", 12)).pack(pady=5)
    placa_entry = ttk.Entry(frame_facturacion, width=20, font=("Arial", 12))
    placa_entry.pack(pady=5)

    # Lista para mostrar los registros
    lista_registros = ttk.Treeview(frame_facturacion, columns=("Placa", "Fecha Salida", "Monto", "Convenio"), show="headings", height=10)
    lista_registros.heading("Placa", text="Placa")
    lista_registros.heading("Fecha Salida", text="Fecha de Salida")
    lista_registros.heading("Monto", text="Monto ($)")
    lista_registros.heading("Convenio", text="Convenio")
    lista_registros.pack(fill=tk.BOTH, expand=True, pady=10)

    # Función para buscar registros por placa
    def buscar_registros():
        placa = placa_entry.get().strip().upper()
        if not placa:
            messagebox.showerror("Error", "Por favor, ingrese una placa válida.", parent=dialogo)
            return

        # Limpiar la lista
        for item in lista_registros.get_children():
            lista_registros.delete(item)

        # Obtener registros de la base de datos
        registros = obtener_registros_facturacion_por_placa(placa)
        if not registros:
            messagebox.showinfo("Sin Resultados", f"No se encontraron registros para la placa {placa}.", parent=dialogo)
            return

        # Llenar la lista con los registros
        for registro in registros:
            placa, _, _, hora_salida, monto, convenio, _, _ = registro
            lista_registros.insert("", tk.END, values=(placa, hora_salida, f"${monto:,.0f}", convenio))

    # Botón para buscar
    ttk.Button(frame_facturacion, text="Buscar", command=buscar_registros).pack(pady=5)

    # Función para reimprimir el recibo de facturación seleccionado
    def reimprimir_facturacion():
        seleccion = lista_registros.selection()
        if not seleccion:
            messagebox.showerror("Error", "Por favor, seleccione un registro para reimprimir.", parent=dialogo)
            return

        # Obtener los datos del registro seleccionado
        item = lista_registros.item(seleccion[0])
        valores = item['values']
        placa = valores[0]
        fecha_salida = valores[1]

        conn = conectar()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    placa, tipo, hora_ingreso, hora_salida, 
                    monto, convenio, ticket_id
                FROM historial_vehiculos
                WHERE placa = ? AND hora_salida = ?
            ''', (placa, fecha_salida))
            resultado = cursor.fetchone()
            
            if resultado:
                placa, tipo, hora_ingreso, hora_salida, monto, convenio, ticket_id = resultado
                
                # Calcular tiempo estacionado
                hora_ingreso_dt = datetime.strptime(hora_ingreso, "%Y-%m-%d %H:%M:%S")
                hora_salida_dt = datetime.strptime(hora_salida, "%Y-%m-%d %H:%M:%S")
                tiempo_estacionado = hora_salida_dt - hora_ingreso_dt
                horas = int(tiempo_estacionado.total_seconds() // 3600)
                minutos = int((tiempo_estacionado.total_seconds() % 3600) // 60)
                tiempo_formateado = f"{horas}h {minutos}min"

                # Preparar datos para el recibo
                datos_recibo = {
                    "placa": placa,
                    "hora_ingreso": hora_ingreso_dt.strftime("%d/%m/%Y %H:%M"),
                    "hora_salida": hora_salida_dt.strftime("%d/%m/%Y %H:%M"),
                    "tiempo": tiempo_formateado,
                    "costo": monto,
                    "metodo_pago": "REIMPRESIÓN",
                    "convenio": convenio if convenio else "NINGUNO",
                    "ticket_id": ticket_id
                }

                # Reimprimir el recibo
                resultado_impresion = generar_recibo_termico(datos_recibo)
                if "impreso correctamente" in resultado_impresion:
                    messagebox.showinfo("Éxito", "Recibo reimpreso correctamente.", parent=dialogo)
                else:
                    messagebox.showerror("Error", resultado_impresion, parent=dialogo)
            else:
                messagebox.showerror("Error", "No se encontraron los datos completos del registro.", parent=dialogo)
        except Exception as e:
            messagebox.showerror("Error", f"Error al obtener datos del registro: {str(e)}", parent=dialogo)
        finally:
            conn.close()

    # Botón para reimprimir
    ttk.Button(frame_facturacion, text="Reimprimir Recibo", command=reimprimir_facturacion).pack(pady=5)

    # Pestaña 2: Reimprimir recibo de cierre (VERSIÓN MEJORADA)
    frame_cierre = ttk.Frame(notebook_reimpresion)
    notebook_reimpresion.add(frame_cierre, text="Recibo de Cierre")

    # Lista de sesiones cerradas con más columnas
    ttk.Label(frame_cierre, text="Sesiones Cerradas:", font=("Arial", 12)).pack(pady=5)
    
    # Añadimos columna de Usuario y mejoramos el ancho de columnas
    lista_sesiones = ttk.Treeview(frame_cierre, 
                                columns=("ID", "Usuario", "Inicio", "Cierre", "Ingresos"), 
                                show="headings", 
                                height=10)
    
    # Configurar columnas
    lista_sesiones.heading("ID", text="ID Sesión")
    lista_sesiones.heading("Usuario", text="Usuario")
    lista_sesiones.heading("Inicio", text="Fecha Inicio")
    lista_sesiones.heading("Cierre", text="Fecha Cierre")
    lista_sesiones.heading("Ingresos", text="Total Ingresos")
    
    # Ajustar anchos de columnas
    lista_sesiones.column("ID", width=80, anchor='center')
    lista_sesiones.column("Usuario", width=120, anchor='center')
    lista_sesiones.column("Inicio", width=150, anchor='center')
    lista_sesiones.column("Cierre", width=150, anchor='center')
    lista_sesiones.column("Ingresos", width=100, anchor='center')
    
    lista_sesiones.pack(fill=tk.BOTH, expand=True, pady=10)

    # Barra de desplazamiento
    scrollbar = ttk.Scrollbar(frame_cierre, orient="vertical", command=lista_sesiones.yview)
    scrollbar.pack(side="right", fill="y")
    lista_sesiones.configure(yscrollcommand=scrollbar.set)

    # Función mejorada para cargar sesiones
    def cargar_sesiones():
        # Limpiar lista actual
        for item in lista_sesiones.get_children():
            lista_sesiones.delete(item)
        
        try:
            # Obtener sesiones cerradas con información de ingresos
            sesiones = obtener_sesiones_cerradas_completas()
            
            if not sesiones:
                messagebox.showinfo("Info", "No hay sesiones cerradas registradas.", parent=dialogo)
                return
            
            # Llenar la lista con los registros
            for sesion in sesiones:
                sesion_id, usuario, inicio, cierre, total_ingresos = sesion
                lista_sesiones.insert("", tk.END, 
                                    values=(sesion_id, usuario, inicio, cierre, f"${total_ingresos:,.0f}"))
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las sesiones: {str(e)}", parent=dialogo)

    

    # Función mejorada para reimprimir recibo de cierre
    def reimprimir_cierre():
        seleccion = lista_sesiones.selection()
        if not seleccion:
            messagebox.showerror("Error", "Seleccione una sesión", parent=dialogo)
            return

        item = lista_sesiones.item(seleccion[0])
        datos_sesion = {
            'id': item['values'][0],
            'usuario': item['values'][1],
            'inicio': item['values'][2],
            'cierre': item['values'][3],
            'ingresos': item['values'][4],
            'vehiculos': item['values'][5],
            'cortesias': item['values'][6],
            'resumen_tipos': item['values'][7]  # Asegurar que esta columna existe
        }

        try:
            # Calcular duración usando los datos que YA TENEMOS
            inicio_dt = datetime.strptime(datos_sesion['inicio'], "%Y-%m-%d %H:%M:%S")
            cierre_dt = datetime.strptime(datos_sesion['cierre'], "%Y-%m-%d %H:%M:%S")
            duracion = cierre_dt - inicio_dt
            horas = int(duracion.total_seconds() // 3600)
            minutos = int((duracion.total_seconds() % 3600) // 60)

            # Construir estructura con datos EXISTENTES
            datos_cierre = {
                "ticket_id": f"CIERRE-{datos_sesion['id']}",
                "usuario": datos_sesion['usuario'],
                "hora_inicio": datos_sesion['inicio'],
                "hora_cierre": datos_sesion['cierre'],
                "duracion_turno": f"{horas}h {minutos}min",
                "total_ingresos": datos_sesion['ingresos'],
                "vehiculos_atendidos": datos_sesion['vehiculos'],
                "cortesias": datos_sesion['cortesias'],
                "resumen_por_tipo": eval(datos_sesion['resumen_tipos'])  # Convertir string a lista
            }

            # Solo para debug - Verificar datos
            print("Datos enviados a generar_recibo_cierre:", datos_cierre)

            resultado = generar_recibo_cierre(datos_cierre)
            if "impreso correctamente" in resultado:
                messagebox.showinfo("Éxito", "Recibo reimpreso correctamente", parent=dialogo)
            else:
                messagebox.showerror("Error", resultado, parent=dialogo)
            
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al reimprimir: {str(e)}", parent=dialogo)

    # Botones en un frame para mejor disposición
    btn_frame = ttk.Frame(frame_cierre)
    btn_frame.pack(pady=10)
    
    ttk.Button(btn_frame, text="Actualizar Lista", command=cargar_sesiones).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Reimprimir Recibo", command=reimprimir_cierre).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Ver Detalles", command=lambda: mostrar_detalles_sesion(lista_sesiones)).pack(side=tk.LEFT, padx=5)

    # Cargar sesiones al abrir el diálogo
    cargar_sesiones()

    # Botón para cerrar el diálogo
    ttk.Button(dialogo, text="Cerrar", command=dialogo.destroy).pack(pady=10)

# Funciones auxiliares que deben agregarse a database.py
def obtener_sesiones_cerradas_completas():
    """Obtiene sesiones cerradas con información de ingresos"""
    try:
        conn = conectar()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.usuario, s.fecha_inicio, s.fecha_cierre, 
                   COALESCE(SUM(r.monto), 0) as total_ingresos
            FROM sesiones s
            LEFT JOIN registros r ON s.id = r.sesion_id AND r.evento = 'FACTURACIÓN'
            WHERE s.estado = 'CERRADA'
            GROUP BY s.id, s.usuario, s.fecha_inicio, s.fecha_cierre
            ORDER BY s.fecha_cierre DESC
        ''')
        
        sesiones = cursor.fetchall()
        conn.close()
        return sesiones
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error al obtener sesiones cerradas completas: {str(e)}")
        return []

def obtener_datos_completos_sesion(sesion_id):
    """Obtiene TODOS los datos necesarios para reimprimir recibo de cierre"""
    try:
        conn = conectar()
        cursor = conn.cursor()
        
        # 1. Datos básicos de la sesión
        cursor.execute('''
            SELECT usuario, fecha_inicio, fecha_cierre
            FROM sesiones
            WHERE id = ?
        ''', (sesion_id,))
        sesion = cursor.fetchone()
        
        if not sesion:
            return None
            
        usuario, hora_inicio, hora_cierre = sesion
        
        # 2. Estadísticas principales
        cursor.execute('''
            SELECT 
                SUM(monto) as total_ingresos,
                COUNT(*) as vehiculos_atendidos,
                SUM(CASE WHEN convenio != 'NINGUNO' THEN 1 ELSE 0 END) as cortesias
            FROM registros
            WHERE sesion_id = ? AND evento = 'FACTURACIÓN'
        ''', (sesion_id,))
        stats = cursor.fetchone()
        
        # 3. Total convenios (NUEVO)
        cursor.execute('''
            SELECT COUNT(*)
            FROM registros
            WHERE sesion_id = ? AND convenio != 'NINGUNO'
        ''', (sesion_id,))
        total_convenios = cursor.fetchone()[0] or 0
        
        # 4. Total vehículos ingresados
        cursor.execute('''
            SELECT COUNT(*) 
            FROM historial_vehiculos 
            WHERE sesion_id = ?
        ''', (sesion_id,))
        total_vehiculos_ingresados = cursor.fetchone()[0] or 0
        
        # 5. Resumen por tipo de vehículo
        cursor.execute('''
            SELECT tipo, COUNT(*) as cantidad, SUM(monto) as total
            FROM historial_vehiculos
            WHERE sesion_id = ? AND estado = 'FUERA'
            GROUP BY tipo
        ''', (sesion_id,))
        resumen_por_tipo = cursor.fetchall()
        
        conn.close()
        
        return {
            'usuario': usuario,
            'hora_inicio': hora_inicio,
            'hora_cierre': hora_cierre,
            'total_ingresos': stats[0] or 0,
            'vehiculos_atendidos': stats[1] or 0,
            'cortesias': stats[2] or 0,
            'total_convenios': total_convenios,  # Asegurar este campo
            'total_vehiculos_ingresados': total_vehiculos_ingresados,
            'resumen_por_tipo': resumen_por_tipo
        }
        
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error al obtener datos de sesión: {str(e)}")
        return None

def mostrar_detalles_sesion(lista_sesiones):
    """Muestra detalles adicionales de la sesión seleccionada"""
    seleccion = lista_sesiones.selection()
    if not seleccion:
        messagebox.showerror("Error", "Seleccione una sesión para ver detalles")
        return
        
    item = lista_sesiones.item(seleccion[0])
    sesion_id = item['values'][0]
    
    detalles = obtener_datos_completos_sesion(sesion_id)
    if not detalles:
        messagebox.showerror("Error", "No se pudieron obtener los detalles")
        return
    
    # Crear ventana de detalles
    detalle_win = tk.Toplevel()
    detalle_win.title(f"Detalles de Sesión {sesion_id}")
    
    # Mostrar información básica
    ttk.Label(detalle_win, text=f"Usuario: {detalles['usuario']}").pack(pady=5)
    ttk.Label(detalle_win, text=f"Inicio: {detalles['hora_inicio']}").pack(pady=5)
    ttk.Label(detalle_win, text=f"Cierre: {detalles['hora_cierre']}").pack(pady=5)
    ttk.Label(detalle_win, text=f"Total Ingresos: ${detalles['total_ingresos']:,.0f}").pack(pady=5)
    ttk.Label(detalle_win, text=f"Vehículos Atendidos: {detalles['vehiculos_atendidos']}").pack(pady=5)
    ttk.Label(detalle_win, text=f"Cortesías: {detalles['cortesias']}").pack(pady=5)
    
    # Mostrar resumen por tipo
    ttk.Label(detalle_win, text="Resumen por Tipo:").pack(pady=5)
    
    tree = ttk.Treeview(detalle_win, columns=("Tipo", "Cantidad", "Total"), show="headings", height=5)
    tree.heading("Tipo", text="Tipo de Vehículo")
    tree.heading("Cantidad", text="Cantidad")
    tree.heading("Total", text="Total Recaudado")
    tree.pack(pady=10)
    
    for tipo, cantidad, total in detalles['resumen_por_tipo']:
        tree.insert("", tk.END, values=(tipo, cantidad, f"${total:,.0f}"))
    
    ttk.Button(detalle_win, text="Cerrar", command=detalle_win.destroy).pack(pady=10)

# Funciones auxiliares que deben agregarse a database.py
def obtener_sesiones_cerradas_completas():
    """Obtiene sesiones cerradas con información de ingresos"""
    try:
        conn = conectar()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.id, s.usuario, s.fecha_inicio, s.fecha_cierre, 
                   COALESCE(SUM(r.monto), 0) as total_ingresos
            FROM sesiones s
            LEFT JOIN registros r ON s.id = r.sesion_id AND r.evento = 'FACTURACIÓN'
            WHERE s.estado = 'CERRADA'
            GROUP BY s.id, s.usuario, s.fecha_inicio, s.fecha_cierre
            ORDER BY s.fecha_cierre DESC
        ''')
        
        sesiones = cursor.fetchall()
        conn.close()
        return sesiones
    except Exception as e:
        if conn:
            conn.close()
        print(f"Error al obtener sesiones cerradas completas: {str(e)}")
        return []

def obtener_datos_completos_sesion(sesion_id):
    """Obtiene todos los datos para reimprimir recibo de cierre"""
    conn = conectar()
    try:
        cursor = conn.cursor()
        
        # 1. Datos básicos de la sesión
        cursor.execute('''
            SELECT usuario, fecha_inicio, fecha_cierre 
            FROM sesiones 
            WHERE id = ?
        ''', (sesion_id,))
        sesion = cursor.fetchone()
        if not sesion:
            return None
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM historial_vehiculos 
            WHERE sesion_id = ?
        ''', (sesion_id,))
        total_vehiculos_ingresados = cursor.fetchone()[0] or 0

        # 2. Estadísticas principales
        cursor.execute('''
            SELECT 
                SUM(monto) as total,
                COUNT(*) as vehiculos,
                SUM(CASE WHEN convenio != 'NINGUNO' THEN 1 ELSE 0 END) as cortesias
            FROM registros
            WHERE sesion_id = ? AND evento = 'FACTURACIÓN'
        ''', (sesion_id,))
        stats = cursor.fetchone()
        
        # 3. Total de convenios (NUEVO)
        cursor.execute('''
            SELECT COUNT(*) 
            FROM registros 
            WHERE sesion_id = ? AND convenio != 'NINGUNO'
        ''', (sesion_id,))
        total_convenios = cursor.fetchone()[0] or 0
        
        # 4. Resumen por tipo
        cursor.execute('''
            SELECT tipo, COUNT(*), SUM(monto)
            FROM historial_vehiculos
            WHERE sesion_id = ?
            GROUP BY tipo
        ''', (sesion_id,))
        resumen_tipos = cursor.fetchall()
        
        return {
            'usuario': sesion[0],
            'hora_inicio': sesion[1],
            'hora_cierre': sesion[2],
            'total_ingresos': stats[0] or 0,
            'vehiculos_atendidos': stats[1] or 0,
            'cortesias': stats[2] or 0,
            'total_vehiculos_ingresados': total_vehiculos_ingresados,
            'total_convenios': total_convenios,  # Campo crítico
            'resumen_por_tipo': resumen_tipos
        }
    finally:
        conn.close()

def calcular_duracion(inicio_str, fin_str):
    """Calcula horas y minutos entre dos fechas"""
    inicio = datetime.strptime(inicio_str, "%Y-%m-%d %H:%M:%S")
    fin = datetime.strptime(fin_str, "%Y-%m-%d %H:%M:%S")
    segundos = (fin - inicio).total_seconds()
    return int(segundos // 3600), int((segundos % 3600) // 60)

def mostrar_detalles_sesion(lista_sesiones):
    """Muestra detalles adicionales de la sesión seleccionada"""
    seleccion = lista_sesiones.selection()
    if not seleccion:
        messagebox.showerror("Error", "Seleccione una sesión para ver detalles")
        return
        
    item = lista_sesiones.item(seleccion[0])
    sesion_id = item['values'][0]
    
    detalles = obtener_datos_completos_sesion(sesion_id)
    if not detalles:
        messagebox.showerror("Error", "No se pudieron obtener los detalles")
        return
    
    # Crear ventana de detalles
    detalle_win = tk.Toplevel()
    detalle_win.title(f"Detalles de Sesión {sesion_id}")
    
    # Mostrar información básica
    ttk.Label(detalle_win, text=f"Usuario: {detalles['usuario']}").pack(pady=5)
    ttk.Label(detalle_win, text=f"Inicio: {detalles['hora_inicio']}").pack(pady=5)
    ttk.Label(detalle_win, text=f"Cierre: {detalles['hora_cierre']}").pack(pady=5)
    ttk.Label(detalle_win, text=f"Total Ingresos: ${detalles['total_ingresos']:,.0f}").pack(pady=5)
    ttk.Label(detalle_win, text=f"Vehículos Atendidos: {detalles['vehiculos_atendidos']}").pack(pady=5)
    ttk.Label(detalle_win, text=f"Cortesías: {detalles['cortesias']}").pack(pady=5)
    
    # Mostrar resumen por tipo
    ttk.Label(detalle_win, text="Resumen por Tipo:").pack(pady=5)
    
    tree = ttk.Treeview(detalle_win, columns=("Tipo", "Cantidad", "Total"), show="headings", height=5)
    tree.heading("Tipo", text="Tipo de Vehículo")
    tree.heading("Cantidad", text="Cantidad")
    tree.heading("Total", text="Total Recaudado")
    tree.pack(pady=10)
    
    for tipo, cantidad, total in detalles['resumen_por_tipo']:
        tree.insert("", tk.END, values=(tipo, cantidad, f"${total:,.0f}"))
    
    ttk.Button(detalle_win, text="Cerrar", command=detalle_win.destroy).pack(pady=10)

# Pestaña de Cierre
cierre_frame = ttk.Frame(notebook)
notebook.add(cierre_frame, text="CIERRE")

# Configurar el grid para un mejor centrado
cierre_frame.grid_columnconfigure(0, weight=1)
cierre_frame.grid_columnconfigure(1, weight=0)
cierre_frame.grid_columnconfigure(2, weight=0)
cierre_frame.grid_columnconfigure(3, weight=1)
cierre_frame.grid_rowconfigure(0, weight=1)
cierre_frame.grid_rowconfigure(4, weight=1)

fecha_button = ttk.Button(
    cierre_frame,
    text="FECHA",
    style="TButton",
    command=abrir_dialogo_reimpresion  # ¡Aquí se vincula la función!
)
fecha_button.grid(row=0, column=3, padx=20, pady=10, sticky="ne")

# Campos para el módulo de Cierre
ttk.Label(cierre_frame, text="TOTAL DE INGRESOS:", font=("Arial", 30)).grid(row=1, column=1, sticky=tk.E, padx=20, pady=10)
total_ingresos_label = ttk.Label(cierre_frame, text="$0", font=("Arial", 35))
total_ingresos_label.grid(row=1, column=2, sticky=tk.W, padx=20, pady=10)

ttk.Label(cierre_frame, text="VEHÍCULOS ATENDIDOS:", font=("Arial", 20)).grid(row=2, column=1, sticky=tk.E, padx=20, pady=10)
vehiculos_atendidos_label = ttk.Label(cierre_frame, text="0", font=("Arial", 20))
vehiculos_atendidos_label.grid(row=2, column=2, sticky=tk.W, padx=20, pady=10)

ttk.Label(cierre_frame, text="CORTESÍAS:", font=("Arial", 20)).grid(row=3, column=1, sticky=tk.E, padx=20, pady=10)
cortesias_label = ttk.Label(cierre_frame, text="0", font=("Arial", 20))
cortesias_label.grid(row=3, column=2, sticky=tk.W, padx=20, pady=10)

# Función para actualizar la pestaña CIERRE
def actualizar_cierre():
    if not sesion_iniciada:
        return

    estadisticas = obtener_estadisticas_sesion(sesion_id_actual)
    total_ingresos_label.config(text=f"${estadisticas['total_ingresos']:,}")
    vehiculos_atendidos_label.config(text=f"{estadisticas['vehiculos_atendidos']}")
    cortesias_label.config(text=f"{estadisticas['cortesias']}")

# Función para generar reporte
def generar_reporte():
    global sesion_iniciada, usuario_actual, fecha_inicio_sesion, sesion_id_actual
    print("Botón GENERAR REPORTE presionado")
    print(f"Estado actual - sesion_iniciada: {sesion_iniciada}, sesion_id_actual: {sesion_id_actual}, fecha_inicio_sesion: {fecha_inicio_sesion}")
    
    if not sesion_iniciada or sesion_id_actual is None:
        print("No hay sesión activa")
        messagebox.showerror("Error", "No hay una sesión activa para generar el reporte.")
        return

    confirmacion = messagebox.askyesno(
        "Confirmar Cierre de Sesión",
        "¿Está seguro que desea cerrar la sesión y generar el reporte final?"
    )
    
    if not confirmacion:
        print("Cierre de sesión y generación de reporte cancelados por el usuario")
        return

    try:
        print("Generando reporte...")
        estadisticas = obtener_estadisticas_sesion(sesion_id_actual)
        print(f"Estadísticas obtenidas: {estadisticas}")

        conexion = conectar()
        cursor = conexion.cursor()

        cursor.execute('''
            SELECT tipo, COUNT(*) as cantidad, SUM(monto) as total
            FROM historial_vehiculos
            WHERE sesion_id = ? AND estado = 'FUERA'
            GROUP BY tipo
        ''', (sesion_id_actual,))
        resumen_por_tipo = cursor.fetchall()
        print(f"Resumen por tipo (sesión actual): {resumen_por_tipo}")

        cursor.execute('''
            SELECT COUNT(*)
            FROM historial_vehiculos
            WHERE sesion_id = ? AND convenio != 'NINGUNO'
        ''', (sesion_id_actual,))
        total_convenios = cursor.fetchone()[0]

        cursor.execute('''
            SELECT COUNT(*)
            FROM vehiculos
            WHERE sesion_id = ? AND estado = 'DENTRO'
        ''', (sesion_id_actual,))
        vehiculos_dentro = cursor.fetchone()[0] or 0

        cursor.execute('''
            SELECT COUNT(*)
            FROM historial_vehiculos
            WHERE sesion_id = ?
        ''', (sesion_id_actual,))
        vehiculos_facturados = cursor.fetchone()[0] or 0

        total_vehiculos_ingresados = vehiculos_dentro + vehiculos_facturados
        print(f"Total vehículos ingresados (sesión actual): {total_vehiculos_ingresados}")

        # --- CONSULTA CORREGIDA (REEMPLAZO DE LA VERSIÓN INCORRECTA) ---
        cursor.execute('''
            SELECT fecha_inicio FROM sesiones WHERE id = ? AND estado = 'ACTIVA'
        ''', (sesion_id_actual,))
        resultado = cursor.fetchone()
        
        if not resultado or not resultado[0]:
            messagebox.showerror("Error", "No se pudo obtener la fecha de inicio de la sesión")
            conexion.close()
            return
            
        inicio = resultado[0]
        # ---------------------------------------------------------------

        inicio_dt = datetime.strptime(inicio, "%Y-%m-%d %H:%M:%S")
        cierre_dt = datetime.now()
        duracion = cierre_dt - inicio_dt
        horas, rem = divmod(duracion.total_seconds(), 3600)
        minutos = rem // 60
        duracion_turno = f"{int(horas)}h {int(minutos)}min"

        datos_cierre = {
            "ticket_id": f"TICKET-CIERRE-{sesion_id_actual}",
            "usuario": usuario_actual,
            "hora_inicio": inicio,
            "hora_cierre": cierre_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "duracion_turno": duracion_turno,
            "total_ingresos": estadisticas['total_ingresos'],
            "vehiculos_atendidos": estadisticas['vehiculos_atendidos'],
            "cortesias": estadisticas['cortesias'],
            "total_convenios": total_convenios,
            "resumen_por_tipo": resumen_por_tipo,
            "total_vehiculos_ingresados": total_vehiculos_ingresados
        }

        resultado = generar_recibo_cierre(datos_cierre)
        if "impreso correctamente" in resultado:
            messagebox.showinfo("Éxito", "Recibo de cierre impreso correctamente.")

            cursor.execute('''
                UPDATE sesiones 
                SET estado = 'CERRADA', fecha_cierre = ?
                WHERE id = ? AND estado = 'ACTIVA'
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), sesion_id_actual))
            conexion.commit()  # ¡No olvidar el commit!

        else:
            messagebox.showerror("Error", resultado)

        cerrar_sesion()
        print("Reporte generado y sesión cerrada")
        conexion.close()

    except Exception as e:
        print(f"Error en generar_reporte: {str(e)}")
        messagebox.showerror("Error", f"Error al generar reporte: {str(e)}")
    finally:
        if 'conexion' in locals():
            conexion.close()

# Botón para generar reporte
ttk.Button(
    cierre_frame,
    text="GENERAR REPORTE",
    style="BotonGrande.TButton",
    command=generar_reporte
).grid(row=4, column=1, columnspan=2, pady=20, padx=20, sticky="ew")

# Definir la función on_tab_change para manejar el cambio de pestañas
def on_tab_change(event):
    selected_tab = notebook.tab(notebook.select(), "text")
    if selected_tab == "CAJA":
        cargar_convenios()
    elif selected_tab == "CIERRE":
        actualizar_cierre()

# Vincular el evento de cambio de pestaña
notebook.bind("<<NotebookTabChanged>>", on_tab_change)

# Ejecutar la Aplicación
root.mainloop()

