#!/usr/bin/env bash
# Esconde as fotos antigas: reescreve a branch "tmp" sem os commits com mais de LIMITE
# segundos, mantendo só os arquivos mais novos (com a data original de cada um).
# Isto ESCONDE do histórico do repositório; não é apagar de verdade (ver README).
#
# Roda dentro de um clone do repositório (origin = o repositório no GitHub).
# Cria a branch "tmp" se ela ainda não existir.
set -euo pipefail

LIMITE="${LIMITE:-3600}"
RAMO="${RAMO:-tmp}"
agora="$(date +%s)"
trabalho="$(mktemp -d)"
trap 'rm -rf "$trabalho"' EXIT

git config user.name "github-actions[bot]"
git config user.email "41898283+github-actions[bot]@users.noreply.github.com"

existe=0
if git ls-remote --exit-code --heads origin "$RAMO" >/dev/null 2>&1; then
  existe=1
  git fetch -q origin "+refs/heads/$RAMO:refs/remotes/origin/$RAMO"
fi

# commit de marcação (a branch órfã precisa de pelo menos um commit)
nova_branch() { # $1 = data (epoch) do commit raiz
  git checkout -q --orphan "$RAMO-novo"
  git rm -rfq . 2>/dev/null || true
  git clean -fdxq
  printf 'Arquivos temporários do realista. Tudo aqui é reescrito em até ~1h.\n' > LEIA-ME.txt
  git add LEIA-ME.txt
  GIT_AUTHOR_DATE="@$1" GIT_COMMITTER_DATE="@$1" git commit -q -m "marcador"
}

if [ "$existe" = 0 ]; then
  nova_branch "$agora"
  git push -q origin "$RAMO-novo:refs/heads/$RAMO"
  echo "Branch $RAMO criada."
  exit 0
fi

ref="refs/remotes/origin/$RAMO"
sha_atual="$(git rev-parse "$ref")"
raiz="$(git rev-list --max-parents=0 "$ref" | tail -n 1)"
data_raiz="$(git log -1 --format=%ct "$raiz")"
n_commits="$(git rev-list --count "$ref")"

# arquivos de fotos no topo da branch
mapfile -t arquivos < <(git ls-tree -r --name-only "$ref" | grep -E '^(entrada|saida)/' || true)

if [ "${#arquivos[@]}" -eq 0 ] && [ "$n_commits" -eq 1 ]; then
  echo "Nada a fazer: a branch só tem o marcador."
  exit 0
fi
if [ $(( agora - data_raiz )) -lt "$LIMITE" ]; then
  echo "Nada a fazer: o commit mais antigo tem menos de $LIMITE s."
  exit 0
fi

# guarda só o que é novo, junto com a data original
lista="$trabalho/lista"
: > "$lista"
for f in "${arquivos[@]}"; do
  t="$(git log -1 --format=%ct "$ref" -- "$f")"
  if [ $(( agora - t )) -lt "$LIMITE" ]; then
    mkdir -p "$trabalho/arquivos/$(dirname "$f")"
    git show "$ref:$f" > "$trabalho/arquivos/$f"
    printf '%s\t%s\n' "$t" "$f" >> "$lista"
  fi
done
sort -n -o "$lista" "$lista"

primeira="$(head -n 1 "$lista" | cut -f1 || true)"
nova_branch "${primeira:-$agora}"
while IFS=$'\t' read -r t f; do
  [ -n "$f" ] || continue
  mkdir -p "$(dirname "$f")"
  cp "$trabalho/arquivos/$f" "$f"
  git add "$f"
  GIT_AUTHOR_DATE="@$t" GIT_COMMITTER_DATE="@$t" git commit -q -m "mantido: $f"
done < "$lista"

# só sobrescreve se ninguém mexeu na branch enquanto isso (um envio novo, por exemplo)
if git push -q --force-with-lease="refs/heads/$RAMO:$sha_atual" origin "$RAMO-novo:refs/heads/$RAMO"; then
  echo "Branch $RAMO reescrita: $(wc -l < "$lista") arquivo(s) mantido(s)."
else
  echo "A branch mudou durante a limpeza; fica para a próxima rodada."
fi
