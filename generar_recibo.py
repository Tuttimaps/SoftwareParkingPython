import win32print
import win32ui
import win32con

def generar_recibo_termico(datos):
    try:
        # Configuración de la impresora térmica
        printer_name = win32print.GetDefaultPrinter()
        hprinter = win32print.OpenPrinter(printer_name)
        
        # Iniciar el trabajo de impresión
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)
        hdc.StartDoc("Recibo de Facturación")
        hdc.StartPage()

        # Configuración de la fuente con tamaño reducido
        font = win32ui.CreateFont({
            "name": "Arial",
            "height": 28,  # Tamaño de fuente
            "weight": win32con.FW_NORMAL,
        })
        hdc.SelectObject(font)

        # Recibo de facturación (salida de vehículo)
        y_position = 50
        hdc.TextOut(50, y_position, "PARQUEADERO TOBERÍN")
        y_position += 50
        hdc.TextOut(50, y_position, "RECIBO DE SALIDA")
        y_position += 50
        hdc.TextOut(50, y_position, "--------------------------------")
        y_position += 50
        hdc.TextOut(50, y_position, f"Placa: {datos['placa']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Entrada: {datos['hora_ingreso']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Salida: {datos['hora_salida']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Tiempo: {datos['tiempo']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Total Pagar: ${datos['costo']:,}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Método Pago: {datos['metodo_pago']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"Convenio: {datos['convenio']}")
        y_position += 50
        hdc.TextOut(50, y_position, f"NIT: 51969090-8")
        y_position += 50
        hdc.TextOut(50, y_position, "--------------------------------")
        y_position += 50
        hdc.TextOut(50, y_position, "¡Gracias por su visita!")
        y_position += 50
        hdc.TextOut(50, y_position, "Conserve este recibo.")

        # Finalizar el trabajo de impresión
        hdc.EndPage()
        hdc.EndDoc()
        win32print.ClosePrinter(hprinter)

        return "Recibo impreso correctamente."
    except Exception as e:
        return f"Error al imprimir el recibo: {str(e)}"