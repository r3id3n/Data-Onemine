from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class CartirHeader:
    CartirId: int
    Name: str
    CreatedAt: str
    UpdatedAt: str

# Puedes agregar más dataclasses si lo necesitas más adelante.
