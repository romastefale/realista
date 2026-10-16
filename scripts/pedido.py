#!/usr/bin/env python3
"""Lê o pedido (issue aberta pelo dono, ou execução manual) e grava as saídas do passo.

Entrada (variáveis de ambiente): EVENTO, TITULO, CORPO e, no modo manual,
URL_MANUAL, VERSAO_MANUAL, PERFIL_MANUAL, PELOS_MANUAL.
Saída: linhas chave=valor em $GITHUB_OUTPUT (url, versao, perfil, pelos).
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
    for chave, valor in re.findall(r"^\s*(perfil|pelos)\s*=\s*(\S+)\s*$", corpo, re.M):
        opcoes.setdefault(chave, valor)
    perfil, pelos = opcoes.get("perfil", "dia"), opcoes.get("pelos", "1.0")
else:
    url, versao = env("URL_MANUAL", ""), env("VERSAO_MANUAL", "")
    perfil, pelos = env("PERFIL_MANUAL") or "dia", env("PELOS_MANUAL") or "1.0"

if not re.fullmatch(r"[A-Za-z0-9-]{6,64}", versao):
    erro("Versão do pedido inválida.")
if not url:
    erro("Não achei a foto no pedido. Anexe a imagem na issue ou cole o link dela.")
if not re.fullmatch(r"https?://\S+", url):
    erro("O link da foto não é válido.")
if perfil not in ("dia", "noite"):
    erro("Perfil inválido (use dia ou noite).")
if not re.fullmatch(r"[0-3](\.[0-9]+)?", pelos):
    erro("Valor de pelos inválido.")

saida = env("GITHUB_OUTPUT")
linhas = f"url={url}\nversao={versao}\nperfil={perfil}\npelos={pelos}\n"
if saida:
    with open(saida, "a", encoding="utf-8") as f:
        f.write(linhas)
else:
    print(linhas, end="")
