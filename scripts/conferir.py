#!/usr/bin/env python3
"""Confere se o resultado saiu com o upscale de 2x e, se não, escreve um aviso do workflow.
Uso: conferir.py FOTO_ORIGINAL RESULTADO
Compara megapixels (não depende da rotação EXIF): 2x equivale a 4 vezes mais pixels."""
import sys

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

with Image.open(sys.argv[1]) as im:
    entrada = ImageOps.exif_transpose(im).size
with Image.open(sys.argv[2]) as im:
    saida = im.size

mp_entrada = entrada[0] * entrada[1] / 1e6
razao = (saida[0] * saida[1]) / (entrada[0] * entrada[1])
if razao < 3.5:
    fator = razao ** 0.5
    print(f"::warning::Aviso: a foto tem {mp_entrada:.0f} MP e em 2× passaria do limite de 100 MP; "
          f"o upscale foi reduzido e saiu em {fator:.1f}× ({saida[0]}×{saida[1]}).")
