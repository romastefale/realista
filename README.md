# ❯_realista

Página para rodar o `realista.py` (foto com aspecto de iPhone, só código) pelo GitHub Actions, sem servidor e sem chave de acesso. Usa o mesmo sistema de pedido do loggerview.

## Como usar

1. Abra **https://romastefale.github.io/realista/**
2. Ajuste upscale, perfil e pelos.
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
- O `realista.py` reduz o upscale para não passar de 16 MP (`--max-mp`). Uma foto de 12 MP, por exemplo, sai em 1×.
- A API pública do GitHub aceita 60 consultas por hora sem login; a página consulta a cada 10 s e depois a cada 30 s.
