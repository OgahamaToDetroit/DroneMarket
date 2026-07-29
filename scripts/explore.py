# -*- coding: utf-8 -*-
"""สำรวจโครงสร้างไฟล์ดิบของ กสทช. — คอลัมน์ ชนิดข้อมูล ค่าที่หายไป

รันจาก root ของโปรเจกต์:  python scripts/explore.py
"""
import pandas as pd
import io, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'data' / 'raw'

out = io.StringIO()
def p(*a): print(*a, file=out)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 250)

# ---- Data dictionary ----
p('===== DATA DICTIONARY (raw) =====')
dd = pd.read_excel(RAW / 'data-dictionary.xlsx', header=None)
p('shape:', dd.shape)
p(dd.to_string())
p()

# ---- Main data ----
p('===== MAIN DATA =====')
# try to detect header row: read raw first
raw = pd.read_excel(RAW / 'drone_data.xlsx', header=None, nrows=5)
p('--- first 5 raw rows (no header) ---')
p(raw.to_string())
p()

df = pd.read_excel(RAW / 'drone_data.xlsx')
p('shape:', df.shape)
p('columns:', list(df.columns))
p()
p('--- dtypes ---')
p(df.dtypes.to_string())
p()
p('--- head(5) ---')
p(df.head(5).to_string())
p()
p('--- nulls per column ---')
p(df.isna().sum().to_string())

with open(ROOT / 'scripts' / 'explore_out.txt', 'w', encoding='utf-8') as f:
    f.write(out.getvalue())
print('done -> scripts/explore_out.txt')
