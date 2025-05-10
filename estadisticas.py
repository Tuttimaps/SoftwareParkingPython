import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
from database import conectar

class EstadisticasApp(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.configure(bg="#1e1e1e")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Estilo para los widgets
        style = ttk.Style()
        style.configure("TLabel", background="#1e1e1e", foreground="white", font=("Arial", 10))  # Reducimos el tamaño de la fuente
        style.configure("TButton", background="#0056b3", foreground="white", padding=3, font=("Arial", 10))  # Botones más pequeños
        style.configure("TEntry", fieldbackground="#2e2e2e", foreground="white", font=("Arial", 10))

        # Frame principal
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)  # Dar más peso a la fila de los gráficos

        # Título
        ttk.Label(main_frame, text="ESTADÍSTICAS GENERALES", font=("Helvetica", 24, "bold")).grid(row=0, column=0, pady=10)

        # Frame para estadísticas generales (arriba)
        stats_frame = ttk.Frame(main_frame)
        stats_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")  # Reducimos el pady

        # Etiquetas para estadísticas generales (en una fila, con fuente más pequeña)
        self.total_ingresos_label = ttk.Label(stats_frame, text="Total Ingresos: $0", font=("Arial", 10))
        self.total_ingresos_label.grid(row=0, column=0, padx=20, pady=2)

        self.vehiculos_atendidos_label = ttk.Label(stats_frame, text="Vehículos Atendidos: 0", font=("Arial", 10))
        self.vehiculos_atendidos_label.grid(row=0, column=1, padx=20, pady=2)

        # Frame para filtro de fechas
        filter_frame = ttk.Frame(main_frame)
        filter_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        ttk.Label(filter_frame, text="Filtrar por Fecha (YYYY-MM-DD):", font=("Arial", 10)).grid(row=0, column=0, padx=5)
        self.fecha_inicio_entry = ttk.Entry(filter_frame, width=12)
        self.fecha_inicio_entry.grid(row=0, column=1, padx=5)
        self.fecha_inicio_entry.insert(0, "Inicio")

        ttk.Label(filter_frame, text="hasta", font=("Arial", 10)).grid(row=0, column=2, padx=5)
        self.fecha_fin_entry = ttk.Entry(filter_frame, width=12)
        self.fecha_fin_entry.grid(row=0, column=3, padx=5)
        self.fecha_fin_entry.insert(0, "Fin")

        # Botón para aplicar filtro
        ttk.Button(filter_frame, text="APLICAR FILTRO", style="TButton", command=self.aplicar_filtro).grid(row=0, column=4, padx=5)

        # Frame para gráficos (centro)
        graphs_frame = ttk.Frame(main_frame)
        graphs_frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        graphs_frame.grid_columnconfigure(0, weight=1)
        graphs_frame.grid_columnconfigure(1, weight=1)
        graphs_frame.grid_rowconfigure(0, weight=1)
        graphs_frame.grid_rowconfigure(1, weight=2)  # Más peso a la gráfica inferior

        # Gráfico de porcentaje por tipo de vehículo (gráfico circular)
        self.fig1, self.ax1 = plt.subplots(figsize=(6, 6))  # Aumentamos la altura
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=graphs_frame)
        self.canvas1.get_tk_widget().grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Gráfico de ingresos mensuales (gráfico de barras)
        self.fig2, self.ax2 = plt.subplots(figsize=(6, 6))  # Aumentamos la altura
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=graphs_frame)
        self.canvas2.get_tk_widget().grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Gráfico de horas de mayor afluencia (gráfico de barras)
        self.fig3, self.ax3 = plt.subplots(figsize=(12, 8))  # Aumentamos aún más la altura
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=graphs_frame)
        self.canvas3.get_tk_widget().grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        # Frame para botones (abajo)
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=4, column=0, pady=5)  # Reducimos el pady

        ttk.Button(buttons_frame, text="ACTUALIZAR", style="TButton", command=self.actualizar_estadisticas).grid(row=0, column=0, padx=5)
        ttk.Button(buttons_frame, text="EXPORTAR A CSV", style="TButton", command=self.exportar_csv).grid(row=0, column=1, padx=5)

        # Actualizar estadísticas al iniciar (sin filtro)
        self.fecha_inicio = None
        self.fecha_fin = None
        self.actualizar_estadisticas()

    def aplicar_filtro(self):
        """Aplica un filtro de fechas a las estadísticas."""
        fecha_inicio_str = self.fecha_inicio_entry.get().strip()
        fecha_fin_str = self.fecha_fin_entry.get().strip()

        if fecha_inicio_str.lower() == "inicio" and fecha_fin_str.lower() == "fin":
            self.fecha_inicio = None
            self.fecha_fin = None
            messagebox.showinfo("Filtro", "Filtro desactivado. Mostrando estadísticas generales.")
        else:
            try:
                self.fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d") if fecha_inicio_str.lower() != "inicio" else None
                self.fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d") if fecha_fin_str.lower() != "fin" else None
                messagebox.showinfo("Filtro", "Filtro aplicado correctamente.")
            except ValueError:
                messagebox.showerror("Error", "Formato de fecha inválido. Use YYYY-MM-DD.")
                return

        self.actualizar_estadisticas()

    def actualizar_estadisticas(self):
        """Actualiza las estadísticas generales del parqueadero con gráficos."""
        try:
            conn = conectar()
            cursor = conn.cursor()

            # Condiciones para el filtro de fechas
            where_clause = "WHERE evento = 'FACTURACIÓN'"
            where_clause_vehiculos = "WHERE estado = 'FUERA'"
            params = []
            params_vehiculos = []

            if self.fecha_inicio:
                where_clause += " AND fecha_hora >= ?"
                where_clause_vehiculos += " AND hora_salida >= ?"
                params.append(self.fecha_inicio.strftime("%Y-%m-%d 00:00:00"))
                params_vehiculos.append(self.fecha_inicio.strftime("%Y-%m-%d 00:00:00"))
            if self.fecha_fin:
                where_clause += " AND fecha_hora <= ?"
                where_clause_vehiculos += " AND hora_salida <= ?"
                params.append(self.fecha_fin.strftime("%Y-%m-%d 23:59:59"))
                params_vehiculos.append(self.fecha_fin.strftime("%Y-%m-%d 23:59:59"))

            # --- Estadísticas Generales ---
            query = f'''
                SELECT 
                    SUM(monto) AS total_ingresos,
                    COUNT(*) AS vehiculos_atendidos,
                    SUM(CASE WHEN convenio != 'NINGUNO' THEN 1 ELSE 0 END) AS cortesias
                FROM registros 
                {where_clause}
            '''
            cursor.execute(query, params)
            result = cursor.fetchone()

            total_ingresos = result[0] if result[0] is not None else 0
            vehiculos_atendidos = result[1] if result[1] is not None else 0
            cortesias = result[2] if result[2] is not None else 0

            # Actualizar etiquetas
            self.total_ingresos_label.config(text=f"Total Ingresos: ${total_ingresos:,.1f}")
            self.vehiculos_atendidos_label.config(text=f"Vehículos Atendidos: {vehiculos_atendidos}")

            # --- Porcentaje por Tipo de Vehículo ---
            query = f'''
                SELECT tipo, COUNT(*)
                FROM historial_vehiculos
                {where_clause_vehiculos}
                GROUP BY tipo
            '''
            cursor.execute(query, params_vehiculos)
            tipos = cursor.fetchall()
            tipo_dict = {tipo: count for tipo, count in tipos}

            labels = ['Automóviles', 'Motocicletas', 'Bicicletas']
            sizes = [
                tipo_dict.get("Automóvil", 0),
                tipo_dict.get("Motocicleta", 0),
                tipo_dict.get("Bicicleta", 0)
            ]
            total_vehiculos = sum(sizes)
            if total_vehiculos > 0:
                percentages = [(size / total_vehiculos) * 100 for size in sizes]
            else:
                percentages = [0, 0, 0]

            self.ax1.clear()
            self.ax1.pie(percentages, labels=labels, autopct='%1.1f%%', startangle=90, colors=['#ff9999', '#66b3ff', '#99ff99'])
            self.ax1.axis('equal')
            self.ax1.set_title("Porcentaje por Tipo de Vehículo")
            self.canvas1.draw()

            # --- Ingresos Mensuales ---
            query = f'''
                SELECT strftime('%Y-%m', hora_salida) AS mes, SUM(monto) AS total
                FROM historial_vehiculos
                {where_clause_vehiculos}
                GROUP BY mes
                ORDER BY mes
            '''
            cursor.execute(query, params_vehiculos)
            ingresos_mensuales = cursor.fetchall()

            if ingresos_mensuales:
                meses = [f"{mes}" for mes, _ in ingresos_mensuales]
                valores = [total if total is not None else 0 for _, total in ingresos_mensuales]
            else:
                meses = ["Sin datos"]
                valores = [0]

            self.ax2.clear()
            self.ax2.bar(meses, valores, color='#66b3ff')
            self.ax2.set_title("Ingresos Mensuales")
            self.ax2.set_xlabel("Mes")
            self.ax2.set_ylabel("Ingresos ($)")
            self.ax2.tick_params(axis='x', rotation=45)
            self.fig2.tight_layout()
            self.canvas2.draw()

            # --- Horas de Mayor Afluencia ---
            query = f'''
                SELECT strftime('%H', hora_ingreso) AS hora, COUNT(*) AS cantidad
                FROM historial_vehiculos
                {where_clause_vehiculos}
                GROUP BY hora
                ORDER BY hora
            '''
            cursor.execute(query, params_vehiculos)
            afluencia_horas = cursor.fetchall()

            if afluencia_horas:
                horas = [f"{int(hora):02d}:00" if hora is not None else "00:00" for hora, _ in afluencia_horas]
                cantidades = [cantidad if cantidad is not None else 0 for _, cantidad in afluencia_horas]
            else:
                horas = ["Sin datos"]
                cantidades = [0]

            self.ax3.clear()
            self.ax3.bar(horas, cantidades, color='#ff9999')
            self.ax3.set_title("Horas de Mayor Afluencia")
            self.ax3.set_xlabel("Hora del Día")
            self.ax3.set_ylabel("Cantidad de Vehículos")
            self.ax3.tick_params(axis='x', rotation=45)
            self.fig3.tight_layout()
            self.canvas3.draw()

            # Guardar datos para exportación
            self.datos_exportacion = {
                "total_ingresos": total_ingresos,
                "vehiculos_atendidos": vehiculos_atendidos,
                "cortesias": cortesias,
                "tipos": tipo_dict,
                "ingresos_mensuales": ingresos_mensuales,
                "afluencia_horas": afluencia_horas
            }

            conn.close()
        except Exception as e:
            print(f"Error al actualizar estadísticas: {str(e)}")
            messagebox.showerror("Error", f"Error al actualizar estadísticas: {str(e)}")

    def exportar_csv(self):
        """Exporta las estadísticas a un archivo CSV usando el módulo csv."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"estadisticas_{timestamp}.csv"

            with open(filename, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)

                # Estadísticas Generales
                writer.writerow(["Estadísticas Generales"])
                writer.writerow(["Métrica", "Valor"])
                writer.writerow(["Total Ingresos", self.datos_exportacion["total_ingresos"]])
                writer.writerow(["Vehículos Atendidos", self.datos_exportacion["vehiculos_atendidos"]])
                writer.writerow(["Cortesías", self.datos_exportacion["cortesias"]])
                writer.writerow([])

                # Porcentaje por Tipo de Vehículo
                writer.writerow(["Por Tipo de Vehículo"])
                writer.writerow(["Tipo", "Cantidad"])
                writer.writerow(["Automóviles", self.datos_exportacion["tipos"].get("Automóvil", 0)])
                writer.writerow(["Motocicletas", self.datos_exportacion["tipos"].get("Motocicleta", 0)])
                writer.writerow(["Bicicletas", self.datos_exportacion["tipos"].get("Bicicleta", 0)])
                writer.writerow([])

                # Ingresos Mensuales
                writer.writerow(["Ingresos Mensuales"])
                writer.writerow(["Mes", "Ingresos"])
                for mes, total in self.datos_exportacion["ingresos_mensuales"]:
                    writer.writerow([mes, total])
                writer.writerow([])

                # Horas de Mayor Afluencia
                writer.writerow(["Horas de Mayor Afluencia"])
                writer.writerow(["Hora", "Cantidad"])
                for hora, cantidad in self.datos_exportacion["afluencia_horas"]:
                    writer.writerow([f"{int(hora):02d}:00" if hora is not None else "00:00", cantidad])

            messagebox.showinfo("Éxito", f"Estadísticas exportadas a {filename}")
        except Exception as e:
            print(f"Error al exportar a CSV: {str(e)}")
            messagebox.showerror("Error", f"Error al exportar a CSV: {str(e)}")