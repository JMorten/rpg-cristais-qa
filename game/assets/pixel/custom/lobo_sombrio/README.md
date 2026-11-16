# Lobo Sombrio V1 — arte própria

Direção provisória: Dark Fantasy Pixel Art. Referência fornecida pelo usuário,
criada no ChatGPT; não é parte do pacote 0x72 e não recebe sua atribuição CC0.

## Organização

- `referencias/`: prancha original preservada sem alteração dos bytes.
- `fontes/`: futuros arquivos editáveis.
- `previas/`: candidatos e comparações, não carregados pelo jogo.
- `sprites/`: somente arte aprovada para uso no jogo.

## Contrato V1

Avaliação visual: candidato 32 x 32 rejeitado pelo usuário por perda de detalhes.
Novas candidatas 48 x 48 e 64 x 64 em `previas/comparacao_48_64.png`, ambas
mostradas em escala 2x (96 x 96 e 128 x 128 na tela, respectivamente).
Opção B (64 x 64) aprovada pelo usuário e instalada em `sprites/`.
O loader usa esta pose estática em escala 2x (128 x 128 na tela).

PNG RGBA de 64 x 64 por quadro, alfa binário (0/255), fundo transparente.
Exibição de 48 x 48 na tela (redução do arquivo de 64 x 64). Âncora central inferior,
patas na linha 46, com margem inferior de 1 pixel. Preservar a paleta da arte.
Um único quadro estático: `sprites/lobo_sombrio_idle_f0.png`, olhando à direita.
Não espelhar automaticamente nem gerar movimentos. A mesma pose será exibida
durante perseguição. Reiniciar o jogo após trocar o arquivo (cache em memória).

64 x 64 é o formato aprovado, não a resolução nativa da prancha.
A prancha de 1536 x 1024 não é um atlas regular e contém fundo e legendas.
Os rótulos 24 x 16 não correspondem às dimensões reais dos desenhos.

O renderer geral alterna idle/run a 8 fps. Desde a missão 02 (28/10/2026), em
branch `dev/lobo-animacao-e-telegraph`, há uma caminhada **experimental**.

## Caminhada experimental (missão 02, NÃO aprovada em definitivo)

- Quatro quadros 64 x 64 em `sprites/lobo_sombrio_walk_f0..f3.png`, extraídos da
  linha 2 da prancha de referência (`scripts/extrair_andar_lobo.py`).
- Mesmo contrato do idle: PNG RGBA 64 x 64, alfa binário (0/255), exibidos em 48 x 48,
  âncora central inferior, sem espelhamento (uma única pose por direção).
- Chave `LOBO_ANDAR = True` em `pixel_enemy.py`. Os quadros só são usados no estado
  `chase` (perseguição), a 8 fps; idle e demais estados continuam no quadro estático V1.
- Fallback garantido: quadro ausente/inválido/arquivo corrompido é descartado e a
  caminhada vira pausas do idle; sem idle válido, o lobo usa o desenho original.
- Prévias para aprovação visual em `previas/`: `lobo_sombrio_walk_animado.gif`
  (quadros isolados, 3x) e `demo_lobo_no_jogo.gif` (perseguição renderizada pelo
  código do jogo). Comparação lado a lado em `previas/comparacao_walk_f0_f3.png`.
- Quadro walk inválido é descartado individualmente: faltando um quadro, a caminhada
  é exibida com a sequência compactada (sem travar nem cair no desenho original).
- Continua proibido: dano, ataque, morte, flip por direção. Se os quadros forem
  rejeitados, recomputar os recortes e revalidar testes antes de reinstalar.

## Preparação local

Pillow 13.0.0 disponível no ambiente de desenvolvimento; não é dependência
adicional do jogo. Executar `python scripts/preparar_lobo.py` na raiz.
O script recorta a primeira pose IDLE direita, aplica uma máscara de cor
específica da prancha e reduz com nearest-neighbor. Não inventa quadros.
A máscara e a redução podem perder detalhes: revisar a comparação antes de
aprovar. O candidato permanece em `previas/`; não copiar automaticamente
para `sprites/`.

Sem PNG aprovado válido, o Lobo Sombrio usa seu desenho original como fallback,
nunca o wogol. Demais inimigos continuam no carregador existente.
