import win32print
import win32ui


# Старые функции (оставляем без изменений)
def mm_to_pixels(mm):
    return int(mm * 8)  # 8 точек на мм

def get_default_printer():
    return win32print.GetDefaultPrinter()

def create_printer_dc(printer_name):
    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(printer_name)
    return hdc