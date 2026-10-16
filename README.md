# ❯_realista

Página para rodar o `realista.py` (foto com aspecto de iPhone, só código) pelo GitHub Actions, sem servidor.

Você escolhe a foto na página, ela sobe para a branch `tmp`, o workflow **Processar** roda o script e a página mostra e baixa o resultado. O workflow **Limpar** esconde as fotos com mais de ~1h.

## Aviso importante: "esconder" não é "apagar"

Este repositório é público. As fotos passam pela branch `tmp`, que é reescrita a cada 15 minutos sem os commits com mais de 1h. Isso as tira do histórico visível, mas **o GitHub pode continuar servindo um commit antigo a quem souber o endereço (SHA) dele**, e só o suporte do GitHub apaga de vez. Quem estiver olhando o repositório durante a hora (clone, fork) também fica com a cópia. Use para fotos que você aceita expor por esse risco.

## Montar (uma vez)

1. Crie o repositório público `realista` (outro nome? troque `REPO` no `index.html`) e envie estes arquivos para a branch `main`.
2. **Settings → Pages → Source: GitHub Actions.**
3. **Actions → Limpar → Run workflow**, uma vez, para criar a branch `tmp`.
4. Crie um token em **Settings (da conta) → Developer settings → Fine-grained tokens**:
   - Repository access: *Only select repositories* → `realista`
   - Permissões do repositório: **Contents: Read and write** e **Actions: Read and write**
5. Abra `https://<seu-usuario>.github.io/realista/`, toque na chave e cole o token. Ele fica só no navegador.

## Usar

Escolha a foto, ajuste upscale, perfil e pelos, e toque na seta. Leva de 1 a 3 minutos.

## Observações

- Agendamentos do GitHub atrasam; a foto some do histórico entre 1h e ~1h20.
- Em repositório público, o GitHub desativa workflows agendados após 60 dias sem atividade no repositório. Se isso acontecer, reative em Actions.
- Limite do runner: o `realista.py` reduz o upscale para não passar de 16 MP (`--max-mp`). Uma foto de 12 MP, por exemplo, sai em 1×.
- Mexa no `realista.py` à vontade: o workflow só chama a linha de comando dele.
