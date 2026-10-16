"""Executa somente a categoria 3; aceita --config, --q e --saida."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menu import main

if __name__ == "__main__":
    sys.argv[1:1] = ["--modo", "metaheuristica"]
    main()
