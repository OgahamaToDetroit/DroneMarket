# -*- coding: utf-8 -*-
import pandas as pd
import io, sys

out = io.StringIO()
def p(*a): print(*a, file=out)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 250)

# ---- Data dictionary ----
p('===== DATA DICTIONARY (raw) =====')
dd = pd.read_excel('data-dictionary.xlsx', header=None)
p('shape:', dd.shape)
p(dd.to_string())
p()

# ---- Main data ----
p('===== MAIN DATA =====')
# try to detect header row: read raw first
raw = pd.read_excel('drone_data.xlsx', header=None, nrows=5)
p('--- first 5 raw rows (no header) ---')
p(raw.to_string())
p()

df = pd.read_excel('drone_data.xlsx')
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

with open('explore_out.txt', 'w', encoding='utf-8') as f:
    f.write(out.getvalue())
print('written explore_out.txt')
