"""Tabela das moléculas estudadas.

Todas existem no banco de dados g2 do ASE e têm no máximo 12 átomos.
O campo `expected_linear` é apenas a expectativa física — a linearidade
efetiva é determinada pelo cálculo e gravada no JSON de saída.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MoleculeSpec:
    """Identificação de uma molécula do conjunto."""

    id: str
    ase_name: str
    name: str
    expected_linear: bool


MOLECULES: list[MoleculeSpec] = [
    MoleculeSpec("h2o", "H2O", "Água", False),
    MoleculeSpec("co2", "CO2", "Dióxido de carbono", True),
    MoleculeSpec("nh3", "NH3", "Amônia", False),
    MoleculeSpec("h2co", "H2CO", "Formaldeído", False),
    MoleculeSpec("c2h2", "C2H2", "Acetileno", True),
    MoleculeSpec("ch4", "CH4", "Metano", False),
    MoleculeSpec("ch3oh", "CH3OH", "Metanol", False),
    MoleculeSpec("c2h4", "C2H4", "Eteno", False),
    MoleculeSpec("c2h6", "C2H6", "Etano", False),
    MoleculeSpec("c6h6", "C6H6", "Benzeno", False),
]
