# ❯_realista

Página para rodar o `realista.py` (foto com aspecto de iPhone, só código) pelo GitHub Actions, sem servidor e sem chave de acesso. Usa o mesmo sistema de pedido do loggerview.

## Como usar

1. Abra **https://romastefale.github.io/realista/**
2. Ajuste perfil, pelos e formato (JPG ou PNG). O upscale é sempre 2×.
3. Toque na seta. Abre no GitHub uma issue já preenchida: **anexe a foto** nela (ou, antes, cole na página o link de uma foto que já esteja online e deixe o campo preenchido) e toque em *Create*. Você precisa estar logado como dono do repositório.
4. Volte para a página: ela acompanha o processamento (1 a 3 minutos) e mostra o resultado, com botão para baixar.

Também dá para rodar à mão em **Actions → Processar → Run workflow**, informando o link da foto.

## Como funciona

- A issue (`processar <versão>`) dispara o workflow **Processar**. Só issues abertas pelo dono do repositório são atendidas.
- O workflow baixa a foto, roda o `realista.py` e grava `saida/<versão>.jpg` na branch `tmp`. Depois tira a foto do texto da issue e a fecha.
- A página baixa o resultado de `raw.githubusercontent.com`. Sem token, porque o repositório é público.
- O workflow **Limpar** (a cada 15 min) reescreve a branch `tmp` sem os commits com mais de 1h.

## Avisos importantes

**"Esconder" não é "apagar".** O repositório é público. A branch `tmp` é reescrita sem os commits antigos, mas o GitHub pode continuar servindo um commit antigo a quem souber o endereço (SHA) dele, e só o suporte do GitHub apaga de vez.

**A foto anexada na issue é o ponto mais exposto.** O workflow tira o link do texto da issue, mas o histórico de edições da issue guarda a versão anterior e o endereço do anexo continua ativo. Quem tiver esse endereço consegue abrir a foto. Para fotos que você não quer expostas, não use este caminho.

## Montar (uma vez)

1. Settings → Pages → Source: **GitHub Actions**.
2. Actions → **Limpar** → Run workflow, uma vez, para criar a branch `tmp`.
3. Em Settings → Actions → General, deixe *Workflow permissions* em *Read and write*.

## Observações

- Agendamentos do GitHub atrasam; a foto some do histórico entre 1h e ~1h20. Em repositório público o GitHub desativa workflows agendados após 60 dias sem atividade.
- PNG não perde qualidade, mas fica bem maior que o JPG (em 2×, uma foto de 12 MP pode passar de 80 MB). O JPG sai com qualidade 93.
- Perfis disponíveis: `dia` e `noite` (e `auto`, que escolhe um dos dois). Para criar outro, adicione uma entrada em `PERFIS` no `realista.py` e o nome em três lugares: `choices` do argumento `-p` no `realista.py`, a lista em `scripts/pedido.py` e o `<select id="perfil">` do `index.html`.
- O upscale é sempre 2× e o limite de megapixels do script foi elevado a 100 MP (`--max-mp 100`), então uma foto de 12 MP sai com 8064×6048. Em teste, isso levou de 20 a 50 s e 3 a 4 GB de memória. O GitHub recusa arquivos acima de 100 MB, então um PNG acima de ~90 MiB é recomprimido sem perda e, se ainda passar, entregue como JPG de qualidade 95 (4:4:4); a página avisa e baixa o arquivo que existir.
- A API pública do GitHub aceita 60 consultas por hora sem login; a página consulta a cada 10 s e depois a cada 30 s.
