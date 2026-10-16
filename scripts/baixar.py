#!/usr/bin/env python3
"""Baixa a foto do pedido, confere que é uma imagem e salva como <pasta>/<versao>.<ext>.
Uso: baixar.py URL PASTA VERSAO   (imprime o caminho do arquivo salvo)"""
import os
import sys
import urllib.request

LIMITE = 40 * 1024 * 1024
FORMATOS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "HEIF": "heic", "BMP": "bmp", "TIFF": "tif"}


tmp = None


def erro(msg):
    print(f"::error::{msg}")
    if tmp and os.path.exists(tmp):
        os.remove(tmp)
    sys.exit(1)


url, pasta, versao = sys.argv[1:4]
os.makedirs(pasta, exist_ok=True)
tmp = os.path.join(pasta, versao + ".baixando")
try:
    req = urllib.request.Request(url, headers={"User-Agent": "realista-workflow"})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        total = 0
        while True:
            bloco = r.read(1 << 20)
            if not bloco:
                break
            total += len(bloco)
            if total > LIMITE:
                erro("A foto passa de 40 MB.")
            f.write(bloco)
except SystemExit:
    raise
except Exception as ex:
    erro(f"Não consegui baixar a foto: {ex}")

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass
try:
    from PIL import Image
    with Image.open(tmp) as im:
        formato = im.format
except Exception:
    erro("O arquivo baixado não é uma imagem que eu consiga abrir.")
ext = FORMATOS.get(formato)
if not ext:
    erro(f"Formato de imagem não aceito: {formato}.")
destino = os.path.join(pasta, f"{versao}.{ext}")
os.replace(tmp, destino)
print(destino)
