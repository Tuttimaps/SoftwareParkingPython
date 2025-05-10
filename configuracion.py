import tkinter as tk
from tkinter import ttk, messagebox
from database import conectar, obtener_facturaciones, actualizar_facturacion, obtener_tarifas, agregar_convenio, eliminar_convenio, obtener_convenios, actualizar_tarifa

class ConfiguracionApp(tk.Frame):
    def __init__(self, master=None, usuario_actual=None):
        super().__init__(master)
        self.master = master
        self.usuario_actual = usuario_actual
        self.clave_administrador = "admin123"
        self.pack(fill=tk.BOTH, expand=True)
        self.crear_widgets()

    def crear_widgets(self):
        self.panel_principal = ttk.Frame(self)
        self.panel_principal.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Mostrar validación solo si no es Usuario 2
        if self.usuario_actual != "Usuario 2":
            self.frame_clave = ttk.Frame(self.panel_principal)
            self.frame_clave.pack(pady=20)

            ttk.Label(self.frame_clave, text="Clave de Administrador:", font=("Arial", 12)).pack(side=tk.LEFT)
            self.clave_entry = ttk.Entry(self.frame_clave, show="*", width=20, font=("Arial", 12))
            self.clave_entry.pack(side=tk.LEFT, padx=10)
            ttk.Button(self.frame_clave, text="Validar", command=self.validar_clave).pack(side=tk.LEFT)
        else:
            self.mostrar_opciones_avanzadas(mostrar_facturaciones=True)

    def validar_clave(self):
        if self.clave_entry.get() == self.clave_administrador:
            self.frame_clave.pack_forget()
            self.mostrar_opciones_avanzadas(mostrar_facturaciones=False)
        else:
            messagebox.showerror("Error", "Clave incorrecta")

    def mostrar_opciones_avanzadas(self, mostrar_facturaciones=False):
        # Notebook para organizar las pestañas
        self.notebook = ttk.Notebook(self.panel_principal)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Pestaña de Facturaciones (solo para Usuario 2)
        if mostrar_facturaciones:
            self.frame_facturaciones = ttk.Frame(self.notebook)
            self.notebook.add(self.frame_facturaciones, text="Editar Facturaciones")
            self.crear_pestana_facturaciones()

        # Pestaña de Tarifas (para todos)
        self.frame_tarifas = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_tarifas, text="Tarifas")
        self.crear_pestana_tarifas()

        # Pestaña de Convenios (para todos)
        self.frame_convenios = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_convenios, text="Convenios")
        self.crear_pestana_convenios()

    def crear_pestana_facturaciones(self):
        # Frame para filtros
        frame_filtros = ttk.Frame(self.frame_facturaciones)
        frame_filtros.pack(fill=tk.X, pady=5)

        ttk.Label(frame_filtros, text="Filtrar por:").pack(side=tk.LEFT, padx=5)
        
        # Filtro por placa
        ttk.Label(frame_filtros, text="Placa:").pack(side=tk.LEFT, padx=5)
        self.entry_filtro_placa = ttk.Entry(frame_filtros, width=15)
        self.entry_filtro_placa.pack(side=tk.LEFT, padx=5)
        
        # Filtro por fecha
        ttk.Label(frame_filtros, text="Fecha (YYYY-MM-DD):").pack(side=tk.LEFT, padx=5)
        self.entry_filtro_fecha = ttk.Entry(frame_filtros, width=12)
        self.entry_filtro_fecha.pack(side=tk.LEFT, padx=5)
        
        # Botón de búsqueda
        ttk.Button(frame_filtros, text="Buscar", command=self.buscar_facturaciones).pack(side=tk.LEFT, padx=5)
        
        # Treeview para mostrar facturaciones
        columns = ("ID", "Placa", "Fecha", "Tipo", "Tiempo", "Valor", "Convenio")
        self.tree_facturaciones = ttk.Treeview(
            self.frame_facturaciones, 
            columns=columns, 
            show="headings",
            height=15
        )
        
        # Configurar columnas
        col_widths = [50, 80, 120, 100, 80, 80, 100]
        for col, width in zip(columns, col_widths):
            self.tree_facturaciones.heading(col, text=col)
            self.tree_facturaciones.column(col, width=width, anchor=tk.CENTER)
        
        self.tree_facturaciones.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.tree_facturaciones, orient="vertical", command=self.tree_facturaciones.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_facturaciones.configure(yscrollcommand=scrollbar.set)
        
        # Frame para botones
        frame_botones = ttk.Frame(self.frame_facturaciones)
        frame_botones.pack(pady=5)
        
        ttk.Button(frame_botones, text="Editar Valor", command=self.abrir_editor_facturacion).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Actualizar Lista", command=self.buscar_facturaciones).pack(side=tk.LEFT, padx=5)
        
        # Cargar datos iniciales
        self.buscar_facturaciones()

    def buscar_facturaciones(self):
        placa = self.entry_filtro_placa.get().strip()
        fecha = self.entry_filtro_fecha.get().strip()
        
        try:
            # Limpiar treeview
            for item in self.tree_facturaciones.get_children():
                self.tree_facturaciones.delete(item)
                
            # Obtener facturaciones filtradas
            facturaciones = obtener_facturaciones(placa=placa if placa else None, 
                                                fecha=fecha if fecha else None)
            
            # Insertar datos
            for fact in facturaciones:
                self.tree_facturaciones.insert("", tk.END, values=fact)
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las facturaciones: {str(e)}")

    def abrir_editor_facturacion(self):
        seleccion = self.tree_facturaciones.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una factura para editar")
            return
            
        datos = self.tree_facturaciones.item(seleccion[0], "values")
        
        # Crear ventana de edición
        ventana_edicion = tk.Toplevel(self)
        ventana_edicion.title("Editar Facturación")
        ventana_edicion.geometry("400x250")
        ventana_edicion.resizable(False, False)
        
        # Variables
        id_factura = datos[0]
        valor_actual = float(datos[5])
        
        # Widgets
        ttk.Label(ventana_edicion, text=f"Editando factura ID: {id_factura}", font=("Arial", 10)).pack(pady=5)
        
        frame_info = ttk.Frame(ventana_edicion)
        frame_info.pack(pady=5, fill=tk.X, padx=10)
        
        ttk.Label(frame_info, text="Placa:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(frame_info, text=datos[1]).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(frame_info, text="Fecha:").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(frame_info, text=datos[2]).grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(frame_info, text="Tipo:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(frame_info, text=datos[3]).grid(row=2, column=1, sticky=tk.W)
        
        ttk.Label(frame_info, text="Valor Actual:").grid(row=3, column=0, sticky=tk.W)
        ttk.Label(frame_info, text=f"${valor_actual:,.0f}").grid(row=3, column=1, sticky=tk.W)
        
        ttk.Label(ventana_edicion, text="Nuevo Valor:").pack()
        self.entry_nuevo_valor = ttk.Entry(ventana_edicion)
        self.entry_nuevo_valor.pack(pady=5)
        self.entry_nuevo_valor.insert(0, str(valor_actual))
        
        frame_botones = ttk.Frame(ventana_edicion)
        frame_botones.pack(pady=10)
        
        ttk.Button(frame_botones, text="Guardar", 
                  command=lambda: self.guardar_cambio_facturacion(id_factura, ventana_edicion)).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Cancelar", command=ventana_edicion.destroy).pack(side=tk.LEFT, padx=5)

    def guardar_cambio_facturacion(self, id_factura, ventana):
        nuevo_valor = self.entry_nuevo_valor.get()
        
        try:
            nuevo_valor = float(nuevo_valor)
            if nuevo_valor <= 0:
                messagebox.showerror("Error", "El valor debe ser mayor que cero")
                return
                
            # Actualizar en la base de datos
            if actualizar_facturacion(id_factura, nuevo_valor):
                messagebox.showinfo("Éxito", "Valor actualizado correctamente")
                ventana.destroy()
                self.buscar_facturaciones()  # Refrescar la lista
            else:
                messagebox.showerror("Error", "No se pudo actualizar el valor")
                
        except ValueError:
            messagebox.showerror("Error", "Ingrese un valor numérico válido")

    def crear_pestana_tarifas(self):
        ttk.Label(self.frame_tarifas, text="Tarifas por Minuto", font=("Arial", 12, "bold")).pack(pady=5)
        
        self.tarifas = obtener_tarifas()
        self.entries_tarifas = {}
        
        for tipo, valor in self.tarifas:
            frame = ttk.Frame(self.frame_tarifas)
            frame.pack(fill=tk.X, pady=2, padx=10)
            
            ttk.Label(frame, text=f"{tipo}:", width=12).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, str(valor))
            entry.pack(side=tk.LEFT)
            self.entries_tarifas[tipo] = entry
            
            ttk.Label(frame, text="$/min").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(self.frame_tarifas, text="Guardar Tarifas", command=self.guardar_tarifas).pack(pady=10)

    def guardar_tarifas(self):
        try:
            for tipo, entry in self.entries_tarifas.items():
                nuevo_valor = float(entry.get())
                actualizar_tarifa(tipo, nuevo_valor)
            messagebox.showinfo("Éxito", "Tarifas actualizadas correctamente")
        except ValueError:
            messagebox.showerror("Error", "Ingrese valores numéricos válidos")

    def crear_pestana_convenios(self):
        ttk.Label(self.frame_convenios, text="Convenios Especiales", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Lista de convenios
        self.tree_convenios = ttk.Treeview(
            self.frame_convenios,
            columns=("Nombre", "Valor"),
            show="headings",
            height=10
        )
        self.tree_convenios.heading("Nombre", text="Nombre")
        self.tree_convenios.heading("Valor", text="Valor ($)")
        self.tree_convenios.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.tree_convenios, orient="vertical", command=self.tree_convenios.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_convenios.configure(yscrollcommand=scrollbar.set)
        
        # Frame para agregar nuevos
        frame_nuevo = ttk.Frame(self.frame_convenios)
        frame_nuevo.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame_nuevo, text="Nombre:").pack(side=tk.LEFT)
        self.entry_nombre_conv = ttk.Entry(frame_nuevo, width=20)
        self.entry_nombre_conv.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(frame_nuevo, text="Valor:").pack(side=tk.LEFT)
        self.entry_valor_conv = ttk.Entry(frame_nuevo, width=10)
        self.entry_valor_conv.pack(side=tk.LEFT, padx=5)
        
        # Botones
        frame_botones = ttk.Frame(self.frame_convenios)
        frame_botones.pack(pady=5)
        
        ttk.Button(frame_botones, text="Agregar", command=self.agregar_convenio).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Eliminar", command=self.eliminar_convenio).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Actualizar", command=self.actualizar_lista_convenios).pack(side=tk.LEFT, padx=5)
        
        # Cargar datos iniciales
        self.actualizar_lista_convenios()

    def actualizar_lista_convenios(self):
        self.tree_convenios.delete(*self.tree_convenios.get_children())
        convenios = obtener_convenios()
        for nombre, valor in convenios:
            self.tree_convenios.insert("", tk.END, values=(nombre, f"${valor:,.0f}"))

    def agregar_convenio(self):
        nombre = self.entry_nombre_conv.get().strip()
        valor = self.entry_valor_conv.get().strip()
        
        if not nombre or not valor:
            messagebox.showerror("Error", "Complete todos los campos")
            return
            
        try:
            valor = float(valor)
            agregar_convenio(nombre, valor)
            self.actualizar_lista_convenios()
            self.entry_nombre_conv.delete(0, tk.END)
            self.entry_valor_conv.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "Ingrese un valor numérico válido")

    def eliminar_convenio(self):
        seleccion = self.tree_convenios.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un convenio")
            return
            
        nombre = self.tree_convenios.item(seleccion[0], "values")[0]
        eliminar_convenio(nombre)
        self.actualizar_lista_convenios()