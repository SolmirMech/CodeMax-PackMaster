import qrcode
print(qrcode.__file__)   # посмотрите, откуда загружается
print(hasattr(qrcode, 'QRCode'))  # должно быть True