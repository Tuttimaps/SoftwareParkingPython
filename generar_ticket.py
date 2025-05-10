# generar_ticket.py
import win32print

def generar_ticket_qr(placa, tipo_vehiculo, hora_ingreso, ticket_id=None):
    """
    Genera un ticket de ingreso con un código de barras y lo imprime en la impresora térmica.

    Parámetros:
        placa (str): La placa del vehículo.
        tipo_vehiculo (str): El tipo de vehículo (Automovil, Motocicleta, Bicicleta).
        hora_ingreso (str): La hora de ingreso en formato 'YYYY-MM-DD HH:MM:SS'.
        ticket_id (str, opcional): Identificador único del ticket. Si no se proporciona, se usa la placa.
    """
    try:
        # Usar la placa directamente para el código de barras
        barcode_data = placa

        # Nombre de la impresora configurada en Windows
        printer_name = "XP-58"

        # Abrir la impresora
        hprinter = win32print.OpenPrinter(printer_name)
        try:
            # Iniciar un trabajo de impresión
            hjob = win32print.StartDocPrinter(hprinter, 1, ("Ticket Ingreso", None, "RAW"))
            try:
                win32print.StartPagePrinter(hprinter)

                # Crear el contenido del ticket (ancho 58 mm ~ 384 puntos)
                ticket = (
                    "\x1B\x40"  # Inicializar impresora
                    "\x1B\x61\x01"  # Alineación al centro
                    "PARQUEADERO TOBERIN\n"
                    "--------------------------\n"
                    "Direccion:Cr 19B #166-28\n"
                    "Tel:3208176476 - 3108154470\n"
                    "--------------------------\n"
                    f"Placa: {placa}\n"
                    f"Tipo: {tipo_vehiculo}\n"
                    f"Ingreso: {hora_ingreso}\n"
                    f"NIT: 51969090-8 \n"  # Mostrar la placa como ID en el ticket
                    "--------------------------\n"
                    # Configurar el código de barras (Code 128)
                    "\x1D\x48\x02"  # Seleccionar modo de código de barras (Code 128)
                    "\x1D\x77\x02"  # Ancho del código de barras
                    "\x1D\x68\x50"  # Altura del código de barras (80 puntos)
                    "\x1D\x6B\x49"  # Imprimir código de barras (Code 128)
                    f"{chr(len(barcode_data))}"  # Longitud del dato
                    f"{barcode_data}"  # Dato del código de barras (solo la placa)
                    "\n"
                    "--------------------------\n"
                    "Gracias por su visita\n"
                    "Conserve este ticket.\n"
                    "\x1B\x69"  # Cortar papel
                    "\n\n\n"
                )

                # Enviar el ticket a la impresora
                win32print.WritePrinter(hprinter, ticket.encode('latin1'))
                win32print.EndPagePrinter(hprinter)
            finally:
                win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)

        return "Ticket de ingreso impreso correctamente"
    except Exception as e:
        return f"Error al imprimir: {str(e)}"

# Ejemplo de uso
if __name__ == "__main__":
    # Datos de prueba
    placa = "ABC123"
    tipo_vehiculo = "Automovil"
    hora_ingreso = "2025-03-15 10:30:00"
    resultado = generar_ticket_qr(placa, tipo_vehiculo, hora_ingreso)
    print(resultado)