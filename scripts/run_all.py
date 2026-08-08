"""Roda o cálculo das 10 moléculas, valida a física e gera web/data.json.

Uma molécula que falha é registrada e omitida do JSON; as demais seguem.
"""

from __future__ import annotations

import datetime
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.molecules import MOLECULES
from scripts.run_molecule import (
    DELTA,
    FMAX,
    MODEL_NAME,
    MODEL_TYPE,
    NFREE,
    compute_molecule,
    load_calculator,
)

RAIZ = Path(__file__).resolve().parents[1]
RESULTS = RAIZ / "results"
SAIDA = RAIZ / "web" / "data.json"

# Fundamentais experimentais em cm^-1, de tabelas espectroscópicas padrão.
# Usados apenas para conferência no terminal; não vão para a página.
# As frequências harmônicas calculadas ficam sistematicamente ~5% acima
# das fundamentais medidas, porque estas incluem anarmonicidade.
REFERENCIAS_EXPERIMENTAIS = {
    "h2o": [1595, 3657, 3756],
    "co2": [667, 1333, 2349],
    "nh3": [950, 1627, 3337, 3444],
    "ch4": [1306, 1534, 2917, 3019],
    "c2h2": [612, 730, 1974, 3289, 3374],
}


def calcular_todas() -> tuple[list[dict], list[tuple[str, str]]]:
    """Calcula todas as moléculas. Devolve (registros, falhas)."""
    _, calculator = load_calculator()
    registros: list[dict] = []
    falhas: list[tuple[str, str]] = []

    for i, spec in enumerate(MOLECULES, start=1):
        print(f"\n[{i}/{len(MOLECULES)}] {spec.id} ({spec.ase_name})", flush=True)
        try:
            registros.append(compute_molecule(spec, calculator, RESULTS))
        except Exception as erro:  # noqa: BLE001 — uma falha não pode parar o lote
            falhas.append((spec.id, f"{type(erro).__name__}: {erro}"))
            traceback.print_exc()

    return registros, falhas


def validar(registros: list[dict]) -> list[str]:
    """Confere a física de cada registro. Devolve a lista de problemas."""
    problemas: list[str] = []

    print("\n" + "=" * 64)
    print("VALIDAÇÃO — contagem de modos e frequências imaginárias")
    print("=" * 64)

    for r in registros:
        n = r["n_atoms"]
        esperado = 3 * n - (5 if r["is_linear"] else 6)
        obtido = len(r["modes"])
        marca = "ok " if obtido == esperado else "ERRO"
        if obtido != esperado:
            problemas.append(f"{r['id']}: {obtido} modos, esperado {esperado}")
        if r["n_imaginary"]:
            problemas.append(f"{r['id']}: {r['n_imaginary']} frequência(s) imaginária(s)")
            marca = "ERRO"
        print(
            f"{marca} {r['id']:6s} {r['formula']:6s} "
            f"modos {obtido:2d}/{esperado:2d}  imaginárias {r['n_imaginary']}"
        )

    print("\n" + "=" * 64)
    print("CONFERÊNCIA COM FUNDAMENTAIS EXPERIMENTAIS (cm^-1)")
    print("valores harmônicos ficam ~5% acima por não incluir anarmonicidade")
    print("=" * 64)

    por_id = {r["id"]: r for r in registros}
    for mol_id, experimentais in REFERENCIAS_EXPERIMENTAIS.items():
        registro = por_id.get(mol_id)
        if registro is None:
            continue
        calculadas = [m["freq_cm1"] for m in registro["modes"]]
        print(f"\n{mol_id} ({registro['formula']})")
        for exp in experimentais:
            mais_proxima = min(calculadas, key=lambda c: abs(c - exp))
            desvio = 100.0 * (mais_proxima - exp) / exp
            print(f"   exp {exp:6.0f}   calc {mais_proxima:7.1f}   desvio {desvio:+6.1f}%")

    return problemas


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    SAIDA.parent.mkdir(exist_ok=True)

    registros, falhas = calcular_todas()
    problemas = validar(registros)

    dados = {
        "model": {"type": MODEL_TYPE, "name": MODEL_NAME},
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "settings": {"fmax_eV_per_A": FMAX, "delta_A": DELTA, "nfree": NFREE},
        "molecules": registros,
    }
    SAIDA.write_text(json.dumps(dados, indent=1, ensure_ascii=False))

    print("\n" + "=" * 64)
    print("RESUMO")
    print("=" * 64)
    print(f"moléculas calculadas: {len(registros)}/{len(MOLECULES)}")
    print(f"arquivo gerado: {SAIDA} ({SAIDA.stat().st_size / 1024:.0f} kB)")

    for mol_id, erro in falhas:
        print(f"FALHOU  {mol_id}: {erro}")
    for problema in problemas:
        print(f"PROBLEMA  {problema}")

    if not falhas and not problemas:
        print("nenhuma falha, nenhum problema de validação")

    return 1 if falhas or problemas else 0


if __name__ == "__main__":
    sys.exit(main())
