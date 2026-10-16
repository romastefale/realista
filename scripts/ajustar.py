#!/usr/bin/env python3
"""Garante que o resultado cabe no limite de arquivo do GitHub (100 MB por arquivo).

Uso: ajustar.py CAMINHO   (imprime o caminho final; a extensão pode mudar de png para jpg)

PNG acima do limite:
  1. recompressão sem perda (PNG otimizado, compressão máxima);
  2. se ainda passar, JPG de qualidade 95 sem redução de cor (4:4:4).
Resultado em JPG não é alterado.
O limite padrão é 90 MiB (margem sobre os 100 MB do GitHub); LIMITE_BYTES muda isso.
"""
import os
import sys

limite = int(os.environ.get("LIMITE_BYTES", 90 * 1024 * 1024))
caminho = sys.argv[1]
base, ext = os.path.splitext(caminho)


def log(msg):
    print(msg, file=sys.stderr)


if ext.lower() != ".png" or os.path.getsize(caminho) <= limite:
    print(caminho)
    sys.exit(0)

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
log(f"PNG com {os.path.getsize(caminho) / 1048576:.0f} MiB passa do limite; recomprimindo sem perda.")
with Image.open(caminho) as im:
    im.load()
    otimizado = base + ".otimizado.png"
    im.save(otimizado, format="PNG", optimize=True, compress_level=9)
    if os.path.getsize(otimizado) <= limite:
        os.replace(otimizado, caminho)
        log(f"Recompressão sem perda bastou: {os.path.getsize(caminho) / 1048576:.0f} MiB.")
        print(caminho)
        sys.exit(0)
    os.remove(otimizado)
    log("Ainda passa do limite; entregando JPG de alta qualidade (95, 4:4:4).")
    destino = base + ".jpg"
    im.convert("RGB").save(destino, format="JPEG", quality=95, subsampling=0, optimize=True)
os.remove(caminho)
print(destino)
