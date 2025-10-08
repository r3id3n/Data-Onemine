from __future__ import annotations
import pandas as pd
from sqlalchemy import text
from mtdataonemine.db import get_engine_local
#from mtdataonemine.db.connections import get_local_engine

_SQL = """
SELECT M.MachineId, M.Name, C.IpAddress
FROM Machine M
INNER JOIN Computer C ON (M.ComputerId = C.ComputerId)
"""

def fetch_machines() -> pd.DataFrame:
    with get_engine_local().connect() as con:
        return pd.read_sql_query(text(_SQL), con)
