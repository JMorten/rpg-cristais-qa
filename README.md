# QA Pages — Cristais de Aether

Versão web do jogo para testes de QA no iPhone/Safari.

## Como testar

Acesse: https://jmorten.github.io/rpg-cristais-qa/

## Testes Locais

```powershell
python -m http.server 8000
# Acesse: http://localhost:8000
```

## Limitações Conhecidas

- Áudio desativado (Safari requer interação do usuário)
- Save depende de IndexedDB (não funciona em modo privado)
- Performance em iPhone antigo pode ser limitada
- Orientação landscape recomendada
- ~4.2 MB de download inicial