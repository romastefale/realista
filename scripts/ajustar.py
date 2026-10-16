#!/usr/bin/env python3
"""Garante que o resultado cabe no limite de arquivo do GitHub (100 MB por arquivo).

Uso: ajustar.py CAMINHO   (imprime o caminho final; a extensão pode mudar de png para jpg)

PNG acima do limite: vira JPG de qualidade 95 sem redução de cor (4:4:4), com o mesmo tamanho
em pixels. (Recomprimir o PNG sem perda não adianta: o realista.py já o grava otimizado.)
Resultado em JPG não é alterado.
O limite padrão é 90 MiB (margem sobre os 100 MB do GitHub); LIMITE_BYTES muda isso.
"""
import os
import sys

limite = int(os.environ.get("LIMITE_BYTES", 90 * 1024 * 1024))
caminho = sys.argv[1]
base, ext = os.path.splitext(caminho)

if ext.lower() != ".png" or os.path.getsize(caminho) <= limite:
    print(caminho)
    sys.exit(0)

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
print(f"PNG com {os.path.getsize(caminho) / 1048576:.0f} MiB passa do limite; entregando JPG de alta qualidade (95, 4:4:4).", file=sys.stderr)
destino = base + ".jpg"
with Image.open(caminho) as im:
    im.convert("RGB").save(destino, format="JPEG", quality=95, subsampling=0, optimize=True)
os.remove(caminho)
print(destino)
