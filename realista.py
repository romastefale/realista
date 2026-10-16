#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
realista.py - deixa fotos com aspecto de foto de iPhone recente (so codigo, sem IA generativa).

O que faz:
  * upscale opcional (Lanczos) de 1x a 4x
  * tone mapping local (estilo Smart HDR), pretos profundos, pele levemente suavizada
  * deteccao e reforco de pelos faciais (barba, bigode, sobrancelha)
  * nitidez com halo leve, cor, vinheta e aberracao cromatica minimas
  * perfil "dia": grao residual quase imperceptivel
  * perfil "noite": bloom nas luzes + ruido de sensor (Poisson-Gaussian em mosaico Bayer)

Uso rapido:
  python realista.py                      -> menu interativo
  python realista.py foto.jpg             -> processa a foto (upscale 2x, perfil automatico)
  python realista.py foto.jpg -e 3        -> upscale 3x
  python realista.py pasta/ -p noite      -> todas as fotos da pasta, perfil noite
  python realista.py --ajuda              -> todas as opcoes

Na primeira execucao ele instala sozinho: numpy, opencv e pillow.
"""
import sys
import os
import time
import glob
import argparse
import subprocess
import importlib

VERSAO = "1.0"

# --------------------------------------------------------------------------------------
# 1) Instalacao automatica das bibliotecas (primeira execucao)
# --------------------------------------------------------------------------------------
# modulo -> (pacote pip, [pacotes pkg do Termux em ordem de preferencia])
PACOTES = {
    "numpy": ("numpy", ["python-numpy"]),
    "cv2": ("opencv-python-headless", ["opencv-python", "opencv"]),
    "PIL": ("pillow", ["python-pillow", "pillow"]),
}


def _tem(modulo):
    try:
        importlib.import_module(modulo)
        return True
    except Exception:
        return False


def _rodar(cmd):
    try:
        return subprocess.call(cmd) == 0
    except Exception:
        return False


def _no_termux():
    return "com.termux" in os.environ.get("PREFIX", "") or "TERMUX_VERSION" in os.environ


def garantir_bibliotecas():
    faltando = [m for m in PACOTES if not _tem(m)]
    if not faltando:
        return
    print("Primeira execucao: instalando bibliotecas que faltam ->", ", ".join(faltando))
    print("(precisa de internet; pode demorar alguns minutos)\n")

    if _no_termux():
        # No Termux o pip costuma falhar ao compilar numpy/opencv; os pacotes do pkg ja vem prontos.
        _rodar(["pkg", "install", "-y", "python"])
        for m in list(faltando):
            for nome in PACOTES[m][1]:
                if _rodar(["pkg", "install", "-y", nome]):
                    importlib.invalidate_caches()
                    if _tem(m):
                        break
        faltando = [m for m in PACOTES if not _tem(m)]

    for m in faltando:
        pip_nome = PACOTES[m][0]
        base = [sys.executable, "-m", "pip", "install", pip_nome]
        ok = _rodar(base) or _rodar(base + ["--break-system-packages"]) or _rodar(base + ["--user"])
        importlib.invalidate_caches()
        if not ok and m == "cv2":
            # alternativa: versao completa do opencv
            _rodar([sys.executable, "-m", "pip", "install", "opencv-python"])
            importlib.invalidate_caches()

    ainda = [m for m in PACOTES if not _tem(m)]
    if ainda:
        print("\nNao consegui instalar: " + ", ".join(ainda))
        print("Instale manualmente e rode de novo:")
        if _no_termux():
            print("  pkg install python-numpy opencv-python python-pillow")
        else:
            print("  pip install numpy opencv-python-headless pillow")
        print("No Pydroid: menu (tres barras) > Pip > digite o nome do pacote > Install.")
        sys.exit(1)
    print("\nBibliotecas instaladas.\n")


garantir_bibliotecas()

import numpy as np  # noqa: E402
import cv2  # noqa: E402
from PIL import Image  # noqa: E402

try:
    cv2.setNumThreads(max(1, (os.cpu_count() or 2)))
except Exception:
    pass

# --------------------------------------------------------------------------------------
# 2) Perfis de parametros (calibrados com fotos reais de iPhone 17 que voce enviou)
# --------------------------------------------------------------------------------------
BASE = dict(
    compress=0.95, hl_pull=0.05, detail=0.95, skin_smooth=0.55, bp_frac=0.9, shadow_gamma=1.08,
    sharp=0.28, halo=0.12, sat=1.05, a_shift=0.8, b_shift=0.8, ca=0.0003, vig=0.05, jpeg=93,
    hair_thr=0.035, hair_dark=0.10, hair_light=0.07, hair_micro=0.55,
    grain=0.003,          # grao residual (perfil dia)
    sensor_noise=False,   # ruido Bayer Poisson-Gaussian (perfil noite)
    bloom=0.0, glint=0.0, shot=0.0016, read=0.00008, chroma_blur=2.0, luma_blur=0.55,
)
PERFIS = {
    "dia": dict(BASE),
    "noite": dict(
        BASE, sensor_noise=True, grain=0.0, bloom=0.16, glint=0.08, vig=0.09, ca=0.0005,
        sharp=0.34, shot=0.0016, read=0.00008,
    ),
}

EXTENSOES = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif")


# --------------------------------------------------------------------------------------
# 3) Leitura / escrita de imagem
# --------------------------------------------------------------------------------------
def carregar(caminho):
    ext = os.path.splitext(caminho)[1].lower()
    if ext in (".heic", ".heif"):
        try:
            import pillow_heif  # noqa
        except Exception:
            _rodar([sys.executable, "-m", "pip", "install", "pillow-heif"])
            importlib.invalidate_caches()
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except Exception:
            raise RuntimeError("Arquivo HEIC: nao consegui instalar 'pillow-heif'. "
                               "Converta para JPG antes (ou exporte como 'Mais compativel').")
        from PIL import ImageOps
        im = ImageOps.exif_transpose(Image.open(caminho)).convert("RGB")
        return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    dados = np.fromfile(caminho, dtype=np.uint8)           # funciona com acentos no caminho
    img = cv2.imdecode(dados, cv2.IMREAD_COLOR)            # ja respeita a orientacao EXIF
    if img is None:
        raise RuntimeError("Nao consegui abrir a imagem: " + caminho)
    return img


def salvar(bgr_f32, destino, qualidade, png=False):
    rgb = cv2.cvtColor((np.clip(bgr_f32, 0, 1) * 255 + 0.5).astype(np.uint8), cv2.COLOR_BGR2RGB)
    im = Image.fromarray(rgb)
    if png:
        im.save(destino, optimize=True)
    else:
        im.save(destino, quality=int(qualidade), subsampling=2, optimize=True)


# --------------------------------------------------------------------------------------
# 4) Funcoes do pipeline
# --------------------------------------------------------------------------------------
def filtro_guiado(I, r, eps):
    """Guided filter (He et al.) auto-guiado, so com cv2.boxFilter (nao precisa do opencv-contrib)."""
    k = (2 * r + 1, 2 * r + 1)
    mI = cv2.boxFilter(I, -1, k)
    cov = cv2.boxFilter(I * I, -1, k) - mI * mI
    a = cov / (cov + eps)
    b = mI - a * mI
    return cv2.boxFilter(a, -1, k) * I + cv2.boxFilter(b, -1, k)


def detectar_pelos(L, limiar):
    """Acha estruturas finas e compridas (fios) e ignora pontos redondos (poros).
    Devolve (fios escuros, fios claros, regiao de pelos), todos float32 0..1 no tamanho de L."""
    h, w = L.shape
    f = min(1.0, 1800.0 / w)
    Lw = cv2.resize(L, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else L
    sw = min(w, 1800) / 1800.0
    g8 = (np.clip(Lw, 0, 1) * 255).astype(np.uint8)
    ln = max(7, int(11 * sw) | 1)
    n_or = 12
    bh_max = bh_min = th_max = th_min = None
    for i in range(n_or):
        k = np.zeros((ln, ln), np.uint8)
        ang = np.pi * i / n_or
        c = ln // 2
        cv2.line(k, (int(c - np.cos(ang) * c), int(c - np.sin(ang) * c)),
                 (int(c + np.cos(ang) * c), int(c + np.sin(ang) * c)), 1, 1)
        bh = cv2.morphologyEx(g8, cv2.MORPH_BLACKHAT, k)
        th = cv2.morphologyEx(g8, cv2.MORPH_TOPHAT, k)
        if bh_max is None:
            bh_max, bh_min, th_max, th_min = bh, bh.copy(), th, th.copy()
        else:
            bh_max = np.maximum(bh_max, bh); bh_min = np.minimum(bh_min, bh)
            th_max = np.maximum(th_max, th); th_min = np.minimum(th_min, th)
    dark_line = (bh_max - bh_min).astype(np.float32) / 255.0
    light_line = (th_max - th_min).astype(np.float32) / 255.0
    dark = np.clip((dark_line - limiar) / 0.10, 0, 1)
    light = np.clip((light_line - limiar * 1.6) / 0.12, 0, 1)
    dens = cv2.GaussianBlur(dark, (0, 0), 10 * sw)
    regiao = np.clip(dens * 5.0, 0, 1)
    dark = cv2.GaussianBlur(dark, (0, 0), 0.6)
    light = cv2.GaussianBlur(light, (0, 0), 0.6) * regiao
    if f < 1:
        dsize = (w, h)
        dark = cv2.resize(dark, dsize, interpolation=cv2.INTER_LINEAR)
        light = cv2.resize(light, dsize, interpolation=cv2.INTER_LINEAR)
        regiao = cv2.resize(regiao, dsize, interpolation=cv2.INTER_LINEAR)
    return dark, light, regiao


def escala_centro(canal, k):
    """Amplia/reduz um canal em torno do centro (aberracao cromatica lateral)."""
    h, w = canal.shape
    cx, cy = w / 2.0, h / 2.0
    inv = 1.0 / k
    M = np.array([[inv, 0, cx * (1 - inv)], [0, inv, cy * (1 - inv)]], np.float32)
    return cv2.warpAffine(canal, M, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REFLECT)


def processar(bgr, perfil, escala, pelos_k, rng, log):
    P = dict(PERFIS[perfil])
    P["hair_dark"] *= pelos_k
    P["hair_light"] *= pelos_k
    P["hair_micro"] *= pelos_k

    if escala != 1:
        log("upscale %dx (Lanczos)" % escala)
        bgr = cv2.resize(bgr, None, fx=escala, fy=escala, interpolation=cv2.INTER_LANCZOS4)
    h, w = bgr.shape[:2]
    s = w / 1800.0

    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    del bgr
    L = lab[:, :, 0] / 255.0
    a0 = lab[:, :, 1].copy()
    b0 = lab[:, :, 2].copy()

    log("detectando pelos faciais")
    dark_hair, light_hair, regiao = detectar_pelos(L, P["hair_thr"])

    log("mascara de pele e tone mapping local")
    skin = ((a0 > 133) & (a0 < 162) & (b0 > 134) & (b0 < 170) & (L > 0.25) & (L < 0.95)).astype(np.float32)
    kk = max(3, int(5 * s) | 1)
    skin = cv2.morphologyEx(skin, cv2.MORPH_OPEN, np.ones((kk, kk), np.uint8))
    skin = cv2.GaussianBlur(skin, (0, 0), 6 * s)

    r = max(8, int(24 * s))
    base = filtro_guiado(L, r, 0.01)
    detail = L - base
    mean = float(base.mean())
    b2 = mean + P["compress"] * (base - mean)
    b2 -= P["hl_pull"] * np.clip(base - 0.72, 0, 1) ** 1.5
    L2 = b2 + detail * P["detail"]
    del base, detail, b2

    # suavizacao de pele que preserva contornos (em resolucao reduzida quando a imagem e grande)
    fdown = max(1, int(round(w / 1800.0)))
    sig_sp = (2.2 * s + 1) / fdown
    if fdown > 1:
        Lp = cv2.resize(L2, None, fx=1.0 / fdown, fy=1.0 / fdown, interpolation=cv2.INTER_AREA)
        Ls = cv2.bilateralFilter(Lp, 0, 0.045, sig_sp)
        Ls = cv2.resize(Ls, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
        Ls = cv2.bilateralFilter(L2, 0, 0.045, sig_sp)
    L2 += skin * (1 - regiao) * P["skin_smooth"] * (Ls - L2)
    del Ls

    # ponto preto profundo (como nas fotos do iPhone 17)
    bp = np.percentile(L2[::4, ::4], 0.7) * P["bp_frac"]
    L2 = np.clip((L2 - bp) / (1 - bp), 0, 1)
    L2 = np.where(L2 < 0.25, 0.25 * (L2 / 0.25) ** P["shadow_gamma"], L2).astype(np.float32)

    log("nitidez e reforco dos fios")
    blur1 = cv2.GaussianBlur(L2, (0, 0), 1.0 * s + 0.3)
    blur2 = cv2.GaussianBlur(L2, (0, 0), 2.8 * s)
    L2 = L2 + P["sharp"] * (L2 - blur1) + P["halo"] * (blur1 - blur2)
    del blur1, blur2
    L2 = L2 - P["hair_dark"] * dark_hair * (0.4 + 0.6 * regiao) + P["hair_light"] * light_hair
    blur_h = cv2.GaussianBlur(L2, (0, 0), 0.7 * s + 0.2)
    L2 = L2 + P["hair_micro"] * regiao * (L2 - blur_h)
    del blur_h, dark_hair, light_hair

    log("cor")
    lab[:, :, 0] = np.clip(L2, 0, 1) * 255
    lab[:, :, 1] = np.clip(128 + (a0 - 128) * P["sat"] + P["a_shift"] * (0.4 + 0.6 * skin), 0, 255)
    lab[:, :, 2] = np.clip(128 + (b0 - 128) * P["sat"] + P["b_shift"] * (0.4 + 0.6 * skin), 0, 255)
    del a0, b0, L2, skin, regiao
    img = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32) / 255
    del lab

    if P["bloom"] > 0:
        log("bloom e brilhos nas luzes")
        lum = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hl = np.clip((lum - 0.80) / 0.20, 0, 1)[:, :, None] * img
        img = np.clip(img + P["bloom"] * cv2.GaussianBlur(hl, (0, 0), 12 * s)
                      + 0.5 * P["bloom"] * cv2.GaussianBlur(hl, (0, 0), 3.5 * s), 0, 1)
        del hl
        if P["glint"] > 0:
            ponto = (lum > 0.97).astype(np.uint8)
            n, lbl, stats, cent = cv2.connectedComponentsWithStats(ponto)
            ordem = np.argsort(-stats[1:, cv2.CC_STAT_AREA]) + 1
            glint = np.zeros((h, w), np.float32)
            comp = 22 * s
            for i in ordem[:40]:
                if stats[i, cv2.CC_STAT_AREA] < 6 * s * s:
                    continue
                cx, cy = cent[i]
                for ang in (0.4, 0.4 + np.pi / 2):
                    dx, dy = np.cos(ang) * comp, np.sin(ang) * comp
                    cv2.line(glint, (int(cx - dx), int(cy - dy)), (int(cx + dx), int(cy + dy)),
                             1.0, 1, cv2.LINE_AA)
            glint = cv2.GaussianBlur(glint, (0, 0), 1.1 * s)
            img = np.clip(img + P["glint"] * glint[:, :, None]
                          * np.array([1.0, 0.97, 0.92], np.float32), 0, 1)
            del glint

    log("lente (aberracao cromatica e vinheta)")
    img[:, :, 2] = escala_centro(img[:, :, 2], 1 + P["ca"])
    img[:, :, 0] = escala_centro(img[:, :, 0], 1 - P["ca"])
    xs = ((np.arange(w, dtype=np.float32) - w / 2) / (w / 2)) ** 2
    ys = ((np.arange(h, dtype=np.float32) - h / 2) / (h / 2)) ** 2
    rr = np.sqrt(ys[:, None] + xs[None, :]) / np.sqrt(2)
    img *= (1 - P["vig"] * rr ** 2.4)[:, :, None].astype(np.float32)
    del rr, xs, ys
    img = np.clip(img, 0, 1).astype(np.float32)

    if P["sensor_noise"]:
        log("ruido de sensor (mosaico Bayer, Poisson-Gaussian)")
        lin = img ** 2.2
        B, G, R = lin[:, :, 0], lin[:, :, 1], lin[:, :, 2]
        mos = np.zeros((h, w), np.float32)
        mos[0::2, 0::2] = R[0::2, 0::2]; mos[0::2, 1::2] = G[0::2, 1::2]
        mos[1::2, 0::2] = G[1::2, 0::2]; mos[1::2, 1::2] = B[1::2, 1::2]
        del lin, B, G, R
        ruido = rng.standard_normal(mos.shape, dtype=np.float32)
        noisy = mos + ruido * np.sqrt(P["shot"] * np.clip(mos, 0, 1) + P["read"])
        del ruido
        noisy += rng.normal(0, 0.0004, (h, 1)).astype(np.float32) + rng.normal(0, 0.0003, (1, w)).astype(np.float32)
        m16 = (np.clip(noisy, 0, 1) ** (1 / 2.2) * 65535).astype(np.uint16)
        del noisy, mos
        ref = (img[::8, ::8] * 65535).astype(np.float32)
        melhor = None
        for code in (cv2.COLOR_BAYER_BG2BGR, cv2.COLOR_BAYER_RG2BGR,
                     cv2.COLOR_BAYER_GB2BGR, cv2.COLOR_BAYER_GR2BGR):
            d = cv2.cvtColor(m16, code)
            e = float(np.abs(d[::8, ::8].astype(np.float32) - ref).mean())
            if melhor is None or e < melhor[0]:
                melhor = (e, d)
        del m16
        dem = melhor[1].astype(np.float32) / 65535
        y = cv2.cvtColor(dem, cv2.COLOR_BGR2YCrCb)
        y[:, :, 1:] = cv2.GaussianBlur(y[:, :, 1:], (0, 0), P["chroma_blur"] * s)
        y[:, :, 0] = cv2.GaussianBlur(y[:, :, 0], (0, 0), P["luma_blur"] * max(1.0, s))
        img = np.clip(cv2.cvtColor(y, cv2.COLOR_YCrCb2BGR), 0, 1).astype(np.float32)
    elif P["grain"] > 0:
        log("grao residual")
        lum = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        def g(sig):
            n = cv2.GaussianBlur(rng.standard_normal((h, w), dtype=np.float32), (0, 0), sig)
            return n / n.std()
        grao = 0.65 * g(0.7 * max(1.0, s)) + 0.35 * g(1.5 * max(1.0, s))
        img += (grao * P["grain"] * (0.5 + 0.8 * (1 - lum) ** 1.5))[:, :, None].astype(np.float32)
        img = np.clip(img, 0, 1)
    return img, P["jpeg"]


# --------------------------------------------------------------------------------------
# 5) Interface (linha de comando + menu)
# --------------------------------------------------------------------------------------
def escolher_perfil(bgr):
    cinza = cv2.cvtColor(bgr[::4, ::4], cv2.COLOR_BGR2GRAY)
    return "noite" if float(cinza.mean()) < 75 else "dia"


def limitar_escala(shape, escala, max_mp):
    h, w = shape[:2]
    e = escala
    while e > 1 and (h * e) * (w * e) / 1e6 > max_mp:
        e -= 1
    return e


def nome_saida(caminho, pasta_saida, escala, png):
    pasta, nome = os.path.split(caminho)
    base, _ = os.path.splitext(nome)
    sufixo = "_realista" + ("_%dx" % escala if escala > 1 else "")
    ext = ".png" if png else ".jpg"
    destino_dir = pasta_saida or pasta or "."
    os.makedirs(destino_dir, exist_ok=True)
    destino = os.path.join(destino_dir, base + sufixo + ext)
    n = 2
    while os.path.exists(destino):
        destino = os.path.join(destino_dir, "%s%s_%d%s" % (base, sufixo, n, ext))
        n += 1
    return destino


def listar_imagens(caminho):
    if os.path.isdir(caminho):
        achados = []
        for ext in EXTENSOES:
            achados += glob.glob(os.path.join(caminho, "*" + ext))
            achados += glob.glob(os.path.join(caminho, "*" + ext.upper()))
        achados = sorted(set(achados))
        return [a for a in achados if "_realista" not in os.path.basename(a)]
    return [caminho]


def pastas_comuns():
    home = os.path.expanduser("~")
    cand = ["/sdcard/DCIM/Camera", "/sdcard/DCIM", "/sdcard/Download", "/sdcard/Pictures",
            "/storage/emulated/0/DCIM/Camera", "/storage/emulated/0/Download",
            os.path.join(home, "storage", "dcim", "Camera"),
            os.path.join(home, "storage", "downloads"),
            os.path.join(home, "Downloads"), os.path.join(home, "Pictures"), os.getcwd()]
    vistos, res = set(), []
    for c in cand:
        try:
            real = os.path.realpath(c)
            if os.path.isdir(c) and real not in vistos:
                vistos.add(real)
                res.append(c)
        except Exception:
            pass
    return res


def perguntar(texto, padrao=None):
    try:
        r = input(texto).strip().strip('"').strip("'")
    except EOFError:
        r = ""
    return r if r else padrao


def menu():
    print("=" * 56)
    print(" REALISTA %s - fotos com aspecto de iPhone (so codigo)" % VERSAO)
    print("=" * 56)
    entrada = perguntar("\nCaminho da foto ou da pasta\n(Enter = listar fotos das pastas comuns): ")
    arquivos = []
    if entrada:
        entrada = os.path.expanduser(entrada)
        if not os.path.exists(entrada):
            print("Nao encontrei:", entrada)
            sys.exit(1)
        arquivos = listar_imagens(entrada)
    else:
        todas = []
        for p in pastas_comuns():
            todas += [f for f in listar_imagens(p) if os.path.isfile(f)]
        todas = sorted(set(todas), key=lambda f: os.path.getmtime(f), reverse=True)[:20]
        if not todas:
            print("Nao achei fotos. No Termux rode antes: termux-setup-storage")
            print("Ou digite o caminho completo da foto.")
            sys.exit(1)
        print("\nFotos mais recentes:")
        for i, f in enumerate(todas, 1):
            print("  %2d) %s" % (i, f))
        esc = perguntar("\nNumero(s) separados por virgula, ou 'todas' [1]: ", "1")
        if esc.lower().startswith("t"):
            arquivos = todas
        else:
            for parte in esc.replace(" ", "").split(","):
                if parte.isdigit() and 1 <= int(parte) <= len(todas):
                    arquivos.append(todas[int(parte) - 1])
    if not arquivos:
        print("Nenhuma imagem selecionada.")
        sys.exit(1)
    e = perguntar("Upscale (1, 2, 3 ou 4) [2]: ", "2")
    escala = int(e) if e.isdigit() and 1 <= int(e) <= 4 else 2
    p = perguntar("Perfil: auto / dia / noite [auto]: ", "auto").lower()
    perfil = p if p in ("dia", "noite") else "auto"
    return arquivos, escala, perfil


def main():
    ap = argparse.ArgumentParser(
        prog="realista.py", add_help=False,
        description="Deixa fotos com aspecto de foto de iPhone recente (so codigo).")
    ap.add_argument("caminhos", nargs="*", help="foto(s) ou pasta(s)")
    ap.add_argument("-e", "--escala", type=int, choices=[1, 2, 3, 4], default=None, help="upscale (padrao 2)")
    ap.add_argument("-p", "--perfil", choices=["auto", "dia", "noite"], default="auto")
    ap.add_argument("--pelos", type=float, default=1.0, help="intensidade do realce dos pelos (0 desliga, padrao 1)")
    ap.add_argument("-o", "--saida", default=None, help="pasta de saida (padrao: ao lado da foto)")
    ap.add_argument("--max-mp", type=float, default=16.0,
                    help="limite de megapixels da saida; reduz o upscale se passar (padrao 16)")
    ap.add_argument("--png", action="store_true", help="salvar em PNG")
    ap.add_argument("--semente", type=int, default=None, help="semente do ruido (resultado repetivel)")
    ap.add_argument("-h", "--ajuda", "--help", action="help", help="mostra esta ajuda")
    args = ap.parse_args()

    if args.caminhos:
        arquivos = []
        for c in args.caminhos:
            c = os.path.expanduser(c)
            if not os.path.exists(c):
                print("Nao encontrei:", c)
                continue
            arquivos += listar_imagens(c)
        escala = args.escala or 2
        perfil = args.perfil
    else:
        arquivos, escala, perfil = menu()
        if args.escala:
            escala = args.escala
    if not arquivos:
        print("Nada para processar.")
        sys.exit(1)

    rng = np.random.default_rng(args.semente)
    print("\n%d foto(s) para processar.\n" % len(arquivos))
    ok = 0
    for idx, caminho in enumerate(arquivos, 1):
        t0 = time.time()
        print("[%d/%d] %s" % (idx, len(arquivos), caminho))

        def log(msg):
            print("   - %s (%.0fs)" % (msg, time.time() - t0))
            sys.stdout.flush()
        try:
            bgr = carregar(caminho)
            e = limitar_escala(bgr.shape, escala, args.max_mp)
            if e != escala:
                print("   ! %dx passaria de %.0f MP; usando %dx (mude com --max-mp)" % (escala, args.max_mp, e))
            pf = perfil if perfil != "auto" else escolher_perfil(bgr)
            print("   perfil: %s | upscale: %dx | %dx%d -> %dx%d" % (
                pf, e, bgr.shape[1], bgr.shape[0], bgr.shape[1] * e, bgr.shape[0] * e))
            img, q = processar(bgr, pf, e, max(0.0, args.pelos), rng, log)
            destino = nome_saida(caminho, args.saida, e, args.png)
            salvar(img, destino, q, args.png)
            print("   salvo em: %s  (%.0fs)\n" % (destino, time.time() - t0))
            ok += 1
        except MemoryError:
            print("   ERRO: sem memoria. Tente upscale menor (-e 1) ou --max-mp 8.\n")
        except Exception as ex:
            print("   ERRO: %s\n" % ex)
    print("Pronto: %d de %d foto(s) processada(s)." % (ok, len(arquivos)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido.")
