"""Gera a whitelist hardcoded de licenca usada pelo executavel."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRADA = ROOT / "codclipc_liberados.txt"
SAIDA = ROOT / "core" / "licenca_config.py"


def _carregar_codigos() -> list[int]:
    if not ENTRADA.exists():
        raise FileNotFoundError(f"Arquivo de licencas nao encontrado: {ENTRADA}")

    codigos: set[int] = set()
    for numero_linha, raw in enumerate(ENTRADA.read_text(encoding="utf-8-sig").splitlines(), start=1):
        linha = raw.split("#", 1)[0].strip()
        if not linha:
            continue
        try:
            codigos.add(int(linha))
        except ValueError as exc:
            raise ValueError(f"{ENTRADA.name}: linha {numero_linha} invalida: {raw!r}") from exc

    if not codigos:
        raise ValueError(f"Informe ao menos um CODCLIPC em {ENTRADA.name}.")
    return sorted(codigos)


def gerar() -> None:
    codigos = _carregar_codigos()
    corpo = "\n".join(f"    {codigo}," for codigo in codigos)
    SAIDA.write_text(
        '"""Whitelist de CODCLIPC gerada por scripts/gerar_licenca_config.py."""\n'
        "from __future__ import annotations\n\n"
        "# Nao edite este arquivo diretamente. Edite codclipc_liberados.txt e rode build.bat.\n"
        "CODCLIPC_LIBERADOS = {\n"
        f"{corpo}\n"
        "}\n",
        encoding="utf-8",
    )
    print(f"Licencas geradas em {SAIDA}: {', '.join(str(codigo) for codigo in codigos)}")


if __name__ == "__main__":
    gerar()
