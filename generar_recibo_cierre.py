import win32print
import win32ui
import win32con

def generar_recibo_cierre(datos):
    try:
        # Configuración de la impresora térmica
        printer_name = win32print.GetDefaultPrinter()
        hprinter = win32print.OpenPrinter(printer_name)
        
        # Iniciar el trabajo de impresión
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)
        hdc.StartDoc("Recibo de Cierre")
        hdc.StartPage()

        # Configuración de la fuente
        font = win32ui.CreateFont({
            "name": "Arial",
            "height": 28,
            "weight": win32con.FW_NORMAL,
        })
        hdc.SelectObject(font)

        y_position = 50
        hdc.TextOut(50, y_position, "PARQUEADERO TOBERÍN")
        y_position += 50
        hdc.TextOut(50, y_position, "FACTURA FINAL DE CIERRE")
        y_position += 50
        hdc.TextOut(50, y_position, f"Ticket ID: {datos['ticket_id']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Usuario: {datos['usuario']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Inicio: {datos['hora_inicio']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Cierre: {datos['hora_cierre']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Duración: {datos['duracion_turno']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Total Ingresos: ${datos['total_ingresos']:,}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Vehículos Ingresados: {datos['total_vehiculos_ingresados']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Vehículos Atendidos: {datos['vehiculos_atendidos']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Cortesías: {datos['cortesias']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Total Convenios: {datos['total_convenios']}")
        y_position += 50
        hdc.TextOut(50, y_position, "--------------------------------")
        y_position += 50
        hdc.TextOut(50, y_position, "Resumen por Tipo de Vehículo:")
        y_position += 50

        # Imprimir resumen por tipo
        for tipo, cantidad, total in datos['resumen_por_tipo']:
            hdc.TextOut(50, y_position, f"  {tipo}: {cantidad} - Tot: ${total:,}")
            y_position += 50

        hdc.TextOut(50, y_position, "--------------------------------")
        y_position += 50
        hdc.TextOut(50, y_position, "Gracias por su trabajo!")

        # Finalizar el trabajo de impresión
        hdc.EndPage()
        hdc.EndDoc()
        win32print.ClosePrinter(hprinter)

        return "Recibo de cierre impreso correctamente."
    except Exception as e:
        return f"Error al imprimir el recibo de cierre: {str(e)}"