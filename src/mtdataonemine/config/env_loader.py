from __future__ import annotations
import os, sys
from pathlib import Path
from typing import Iterable, Optional
from dotenv import load_dotenv, find_dotenv

def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) and hasattr(sys, "_MEIPASS")

def _candidates() -> Iterable[Path]:
    if _is_frozen():
        yield Path(sys.executable).parent / ".env"
    # src/mtdataonemine/.env
    yield Path(__file__).resolve().parents[1] / ".env"
    # repo root: src/.. => .env
    yield Path(__file__).resolve().parents[2] / ".env"
    # cwd
    yield Path.cwd() / ".env"
    fd = find_dotenv(usecwd=True)
    if fd:
        yield Path(fd)

_loaded = False
def load_env_once(verbose: bool=False) -> Optional[Path]:
    global _loaded
    if _loaded:
        return None
    for cand in _candidates():
        try:
            if cand and cand.exists():
                load_dotenv(cand, override=False)
                _loaded = True
                if verbose: print(f"[env_loader] .env: {cand}")
                return cand
        except Exception as e:
            if verbose: print(f"[env_loader] fallo {cand}: {e}")
    if verbose: print("[env_loader] .env no encontrado")
    return None

def get_env(key: str, default: Optional[str]=None, strip_space: bool=True) -> Optional[str]:
    val = os.getenv(key, default)
    return val.strip() if (strip_space and isinstance(val, str)) else val

def debug_dump(keys: Iterable[str]) -> str:
    return "\n".join(f"{k}={'<SET>' if os.getenv(k) else '<MISSING>'} {repr(os.getenv(k)) if os.getenv(k) else ''}" for k in keys)
