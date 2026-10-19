#!/usr/bin/env bash
# Demonstração curta para o professor: 2 pedidos, Q variável, orçamento 10.
# Padrão: exato + gulosa + SA/GA/GRASP/ACO próprios.
# Com --bibliotecas: inclui também ga_lib, sa_lib e pso_lib (pymoo/simanneal).
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ"

if [[ -x "$RAIZ/.venv/bin/python" ]]; then
  PY="$RAIZ/.venv/bin/python"
else
  PY="$(command -v python3)"
fi

SAIDA="resultados/demo_10"
ALGORITMOS=""
if [[ "${1:-}" == "--bibliotecas" ]] || [[ "${1:-}" == "--todos" ]]; then
  ALGORITMOS="--algoritmos todos"
  SAIDA="resultados/demo_10_todos"
fi

echo "Python: $PY"
echo "Saída:  $SAIDA"
# shellcheck disable=SC2086
"$PY" menu.py --modo comparar \
  --config experimentos/q_variavel_exemplo.json \
  $ALGORITMOS \
  --saida "$SAIDA"
echo "Abra $SAIDA/RESUMO.md"
