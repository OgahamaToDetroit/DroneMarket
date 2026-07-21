# -*- coding: utf-8 -*-
"""เจาะลึก: unit economics + ช่องว่างการจดทะเบียน + ทดสอบว่าเป็น re-export หรือไม่"""
import io
import sys
import time
import pandas as pd
import requests

sys.path.insert(0, 'scripts')
from comtrade_fetch import load_api_key, REPORTER_THAILAND, CMD_DRONE, BASE_AUTH, BASE_PREVIEW

out = io.StringIO()
def p(*a): print(*a, file=out)

part = pd.read_csv('data/processed/comtrade_hs8806_thailand_partners.csv')
world = pd.read_csv('data/processed/comtrade_hs8806_thailand_world.csv')

# ---------- 1. unit economics ----------
p('=' * 74)
p('1) ราคาเฉลี่ยต่อลำ และน้ำหนักเฉลี่ย (คำนวณจาก value/qty/weight)')
p('=' * 74)
p(f'  {"ปี":<6}{"ทิศทาง":<9}{"คู่ค้า":<22}{"ลำ":>10}{"USD/ลำ":>11}{"kg/ลำ":>9}')
p('  ' + '-' * 65)

def unit_rows(df, label_filter=None):
    for _, r in df.iterrows():
        q = r['qty'] or 0
        if q <= 0:
            continue
        w = r['net_weight_kg'] or 0
        p(f'  {int(r["year"]):<6}{r["flow"]:<9}{str(r["partner"])[:20]:<22}'
          f'{q:>10,.0f}{r["value_usd"]/q:>11,.0f}{(w/q if q else 0):>9,.2f}')

key_rows = part[
    ((part['partner'] == 'China') & (part['flow'] == 'import')) |
    ((part['partner'] == 'Russian Federation') & (part['flow'] == 'export')) |
    ((part['partner'] == 'Poland') & (part['flow'] == 'export'))
].sort_values(['flow', 'year'])
unit_rows(key_rows)

# ---------- 2. ปริมาณรวม นำเข้า vs ส่งออก vs จดทะเบียน ----------
p()
p('=' * 74)
p('2) ปริมาณ (จำนวนลำ): นำเข้า vs ส่งออก vs จดทะเบียนกับ กสทช.')
p('=' * 74)
reg = pd.read_csv('data/processed/summary_by_year.csv')
reg.columns = ['year', 'registrations']
regmap = reg.set_index('year')['registrations'].to_dict()

qty = part.pivot_table(index='year', columns='flow', values='qty', aggfunc='sum').fillna(0)
p(f'  {"ปี":<6}{"นำเข้า(ลำ)":>13}{"ส่งออก(ลำ)":>13}{"คงเหลือ":>12}{"จดทะเบียน":>12}{"อัตราจดทะเบียน":>16}')
p('  ' + '-' * 72)
for y in sorted(qty.index):
    imp_q = qty.loc[y, 'import'] if 'import' in qty.columns else 0
    exp_q = qty.loc[y, 'export'] if 'export' in qty.columns else 0
    net_q = imp_q - exp_q
    n = regmap.get(y, 0)
    rate = f'{n/net_q*100:.0f}%' if net_q > 0 else '—'
    p(f'  {int(y):<6}{imp_q:>13,.0f}{exp_q:>13,.0f}{net_q:>12,.0f}{n:>12,}{rate:>16}')
p()
p('  * "คงเหลือ" = นำเข้า - ส่งออก (ลำ) คือของที่น่าจะอยู่ในไทย')
p('  * อัตราจดทะเบียน < 100% = มีโดรนนำเข้าที่ไม่ได้ขึ้นทะเบียนกับ กสทช.')

# ---------- 3. ทดสอบ re-export โดยตรง ----------
p()
p('=' * 74)
p('3) ทดสอบ: Comtrade แยก re-export (RX) / re-import (RM) ไว้หรือไม่')
p('=' * 74)
api_key = load_api_key()
url = BASE_AUTH if api_key else BASE_PREVIEW
headers = {'Ocp-Apim-Subscription-Key': api_key} if api_key else {}

found_any = False
for year in ('2023', '2024'):
    params = {
        'reporterCode': REPORTER_THAILAND,
        'period': year,
        'cmdCode': CMD_DRONE,
        'flowCode': 'RX,RM',       # RX = re-export, RM = re-import
        'includeDesc': 'True',
        'breakdownMode': 'classic',
        'partnerCode': '0',
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=90)
        if resp.status_code != 200:
            p(f'  {year}: HTTP {resp.status_code}')
            continue
        recs = resp.json().get('data', [])
        if not recs:
            p(f'  {year}: ไม่มีข้อมูล RX/RM (ไทยไม่ได้แยกรายงาน re-export)')
        else:
            found_any = True
            for r in recs:
                p(f'  {year}: {r.get("flowCode")} {r.get("primaryValue"):>15,.0f} USD')
    except Exception as e:
        p(f'  {year}: error {e}')
    time.sleep(1)

p()
if not found_any:
    p('  => ไทยรายงานทุกอย่างรวมใน flow "X" (ส่งออก) ไม่แยก re-export ออกมา')
    p('     ดังนั้นจากข้อมูลนี้ "แยกไม่ได้" ว่าเป็นของผลิตในไทย หรือของนำเข้าแล้วส่งต่อ')

# ---------- 4. เทียบสัดส่วน ----------
p()
p('=' * 74)
p('4) ส่งออกคิดเป็นสัดส่วนเท่าไรของที่นำเข้ามา')
p('=' * 74)
val = part.pivot_table(index='year', columns='flow', values='value_usd', aggfunc='sum').fillna(0)
for y in sorted(val.index):
    i, e = val.loc[y, 'import'], val.loc[y, 'export']
    iq = qty.loc[y, 'import'] if 'import' in qty.columns else 0
    eq = qty.loc[y, 'export'] if 'export' in qty.columns else 0
    p(f'  {int(y)}:  มูลค่า ส่งออก/นำเข้า = {e/i*100:5.1f}%   |   ปริมาณ ส่งออก/นำเข้า = {eq/iq*100:5.1f}%')

with open('scripts/comtrade_deepdive_out.txt', 'w', encoding='utf-8') as f:
    f.write(out.getvalue())
print('done')
