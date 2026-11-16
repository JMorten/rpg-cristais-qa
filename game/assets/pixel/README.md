# Assets de pixel art

Estes assets alimentam o protótipo `pixel_slice.py` e a arte pixel experimental
do jogo principal (**Configurações → Vídeo → Arte pixel**).

- **Pixel Art Top Down - Basic** — Cainos — uso livre (pessoal e comercial) —
  https://cainos.itch.io/pixel-art-top-down-basic
- **Shabby Chic Exterior Tiles** — cyanowl — CC0 —
  https://opengameart.org/content/shabby-chic-exterior-tiles
- **24x32 characters with faces (big pack)** — Svetlana Kushnariova (Cabbit) —
  CC-BY 3.0 — https://lpc.opengameart.org/content/24x32-characters-with-faces-big-pack
- **0x72 - DungeonTileset II** — 0x72 — CC0 —
  https://0x72.itch.io/dungeontileset-ii
- **Silkscreen** — Jason Kottke — OFL 1.1 —
  https://fonts.google.com/specimen/Silkscreen (em `assets/fonts/`)

## Estrutura

- `cainos/tileset_grass.png` — grama e flores (tiles de 32×32). O chão de pedra,
  terra e as trilhas são gerados por código em `pixel_terreno.py`.
- `cainos/plant.png` — árvores e arbustos usados em todos os biomas.
- `cainos/props.png` — bancos, barris, caixotes, potes, placas, lápides e a
  plataforma da fonte. Os recortes usados estão em `pixel_props.RECORTES`.
- `cainos/struct.png` — muros e arcos de ruína.
- `casas/casa_grande.png` e `casas/casa_pequena.png` — casas montadas a partir do kit
  Shabby Chic (telhado, parede, janela e porta). `shabby_chic_home.png` é o kit original.
- `cabbit/heroes/`, `cabbit/npc/`, `cabbit/monsters/` — charsets de 24×32 com
  3 quadros × 4 direções (72×128 por arquivo).
- `ox72/monstros/` — 139 quadros de animação (idle/run/hit) dos monstros do pack
  0x72, usados por `pixel_enemy.py`.
- `ox72/props/` — 19 props do mesmo pack. `column.png` é usado nas Ruínas;
  baú, crânio, frascos, moeda e coração de HUD ficam guardados para uso futuro.

## Estruturas e ícones

Fonte, altar, canteiro, bandeira, bigorna, banca e fogueira **não vêm de nenhum
pack**: são desenhadas por código em `pixel_props.py`, em escala 1×, com contorno
de 1 px e paleta reduzida. Assim seguem a mesma luz e o mesmo tamanho dos props
do Cainos, sem depender de um tileset que não existe.

Os ícones de item e habilidade também são desenhados por código, em
`pixel_icons.py`: quadro de 16×16 ampliado por fator inteiro (2×, 3× ou 4×).
Os retratos de classe (`pixel_portrait.py`) não têm arte própria: recortam a
cabeça e os ombros do charset do herói, então o retrato é o mesmo personagem
que anda no mapa.

O fundo xadrez original do pack da Cabbit foi removido; o resto da arte é original.

## Licenças

**Pixel Art Top Down - Basic (Cainos)**: pode ser usado em projetos gratuitos e
comerciais. Crédito não é obrigatório, mas o projeto credita por educação.

**Shabby Chic Exterior Tiles (cyanowl)**: CC0 (domínio público). Sem obrigações.

**0x72 - DungeonTileset II (0x72)**: CC0 (domínio público). Sem obrigações.

**Silkscreen (Jason Kottke)**: SIL Open Font License 1.1. Pode ser embutida no jogo;
o texto da licença está em `assets/fonts/OFL-Silkscreen.txt`.

**24x32 characters (Svetlana Kushnariova)**: CC-BY 3.0. Obrigatório creditar a autora.
Texto usado no projeto:

> Personagens 24×32 por Svetlana Kushnariova (lana-chan@yandex.ru),
> licença CC-BY 3.0 — https://lpc.opengameart.org/content/24x32-characters-with-faces-big-pack

Se o protótipo virar o jogo final, esse crédito precisa aparecer nos créditos do jogo.
