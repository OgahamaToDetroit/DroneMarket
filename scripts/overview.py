# -*- coding: utf-8 -*-
import pandas as pd
import io, re

out = io.StringIO()
def p(*a): print(*a, file=out)

df = pd.read_excel('drone_data.xlsx')
total = len(df)

# ---- Parse Thai Buddhist-era date: e.g. "16 ต.ค. 2560" ----
thmon = {'ม.ค.':1,'ก.พ.':2,'มี.ค.':3,'เม.ย.':4,'พ.ค.':5,'มิ.ย.':6,
         'ก.ค.':7,'ส.ค.':8,'ก.ย.':9,'ต.ค.':10,'พ.ย.':11,'ธ.ค.':12}
def parse_year(s):
    try:
        parts = str(s).split()
        be = int(parts[-1])
        return be - 543
    except Exception:
        return None
def parse_month(s):
    try:
        parts = str(s).split()
        return thmon.get(parts[1])
    except Exception:
        return None

df['year'] = df['ApprovedDate'].map(parse_year)
df['month'] = df['ApprovedDate'].map(parse_month)

# normalize brand lightly
df['BrandN'] = df['Brand'].astype(str).str.strip().str.upper()

p('TOTAL RECORDS:', total)
p('Year range:', int(df['year'].min()), '-', int(df['year'].max()))
p('Records with unparsed year:', int(df['year'].isna().sum()))
p()

p('===== 1) REGISTRATIONS BY YEAR (Gregorian) =====')
by_year = df.groupby('year').size()
for y, n in by_year.items():
    if pd.notna(y):
        p(f'  {int(y)}: {n:>7,}')
p()

p('===== 2) TOP 20 BRANDS (market share by registrations) =====')
bc = df['BrandN'].value_counts()
p('Distinct brands:', df['BrandN'].nunique())
for name, n in bc.head(20).items():
    p(f'  {name:<22} {n:>7,}  ({n/total*100:5.2f}%)')
p(f'  DJI share = {bc.get("DJI",0)/total*100:.2f}%')
p()

p('===== 3) PURPOSE OF USE =====')
pc = df['PurposeOfUseAircraft'].value_counts(dropna=False)
for name, n in pc.head(12).items():
    label = str(name)[:70]
    p(f'  {n:>7,}  ({n/total*100:5.2f}%)  {label}')
p()

p('===== 4) TOP 20 PROVINCES =====')
prov = df['ProvinceName'].value_counts()
p('Distinct provinces:', df['ProvinceName'].nunique())
for name, n in prov.head(20).items():
    p(f'  {str(name):<20} {n:>7,}  ({n/total*100:5.2f}%)')
p()

p('===== 5) TOP 20 MODELS =====')
mc = df['Model'].astype(str).str.strip().value_counts()
for name, n in mc.head(20).items():
    p(f'  {str(name):<28} {n:>7,}  ({n/total*100:5.2f}%)')
p()

p('===== 6) DJI vs OTHERS by YEAR =====')
df['is_dji'] = (df['BrandN'] == 'DJI')
piv = df[df['year'].notna()].pivot_table(index='year', columns='is_dji', values='Brand', aggfunc='count', fill_value=0)
piv.columns = ['Others' if c is False else 'DJI' for c in piv.columns]
for y, row in piv.iterrows():
    dji = row.get('DJI',0); oth = row.get('Others',0); tot = dji+oth
    share = dji/tot*100 if tot else 0
    p(f'  {int(y)}:  DJI {int(dji):>6,} | Others {int(oth):>6,} | DJI share {share:5.1f}%')

with open('overview_out.txt','w',encoding='utf-8') as f:
    f.write(out.getvalue())

# also save reusable CSV summaries
by_year.rename('registrations').to_csv('summary_by_year.csv', encoding='utf-8-sig')
bc.head(50).rename('registrations').to_csv('summary_by_brand.csv', encoding='utf-8-sig')
prov.rename('registrations').to_csv('summary_by_province.csv', encoding='utf-8-sig')
pc.rename('registrations').to_csv('summary_by_purpose.csv', encoding='utf-8-sig')
print('done')
