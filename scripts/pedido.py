#!/usr/bin/env python3
"""Lê o pedido (issue aberta pelo dono, ou execução manual) e grava as saídas do passo.

Entrada (variáveis de ambiente): EVENTO, TITULO, CORPO e, no modo manual,
URL_MANUAL, VERSAO_MANUAL, ESCALA_MANUAL, PERFIL_MANUAL, PELOS_MANUAL, FORMATO_MANUAL.
Saída: linhas chave=valor em $GITHUB_OUTPUT (url, versao, escala, perfil, pelos, formato).
Tudo é validado aqui; nada do corpo da issue chega ao shell sem passar por estas regras.
"""
import os
import re
import sys


def erro(msg):
    print(f"::error::{msg}")
    sys.exit(1)


env = os.environ.get
evento = env("EVENTO", "")
if evento == "issues":
    titulo = env("TITULO", "")
    corpo = env("CORPO", "") or ""
    versao = titulo[len("processar "):].strip() if titulo.startswith("processar ") else ""
    achado = re.search(r"https?://[^\s)\"'<>\]]+", corpo)
    url = achado.group(0) if achado else ""
    opcoes = {}
    for chave, valor in re.findall(r"^\s*(escala|perfil|pelos|formato)\s*=\s*(\S+)\s*$", corpo, re.M):
        opcoes.setdefault(chave, valor)
    escala, perfil, pelos = (opcoes.get("escala", "2"), opcoes.get("perfil", "auto"), opcoes.get("pelos", "1.0"))
    formato = opcoes.get("formato", "jpg")
else:
    url, versao = env("URL_MANUAL", ""), env("VERSAO_MANUAL", "")
    escala, perfil, pelos = env("ESCALA_MANUAL") or "2", env("PERFIL_MANUAL") or "auto", env("PELOS_MANUAL") or "1.0"
    formato = env("FORMATO_MANUAL") or "jpg"

if not re.fullmatch(r"[A-Za-z0-9-]{6,64}", versao):
    erro("Versão do pedido inválida.")
if not url:
    erro("Não achei a foto no pedido. Anexe a imagem na issue ou cole o link dela.")
if not re.fullmatch(r"https?://\S+", url):
    erro("O link da foto não é válido.")
if not re.fullmatch(r"[1-4]", escala):
    erro("Escala inválida (use 1 a 4).")
if perfil not in ("auto", "dia", "noite"):
    erro("Perfil inválido.")
if not re.fullmatch(r"[0-3](\.[0-9]+)?", pelos):
    erro("Valor de pelos inválido.")
if formato not in ("jpg", "png"):
    erro("Formato inválido (use jpg ou png).")

saida = env("GITHUB_OUTPUT")
linhas = f"url={url}\nversao={versao}\nescala={escala}\nperfil={perfil}\npelos={pelos}\nformato={formato}\n"
if saida:
    with open(saida, "a", encoding="utf-8") as f:
        f.write(linhas)
else:
    print(linhas, end="")
