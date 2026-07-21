# -*- coding: utf-8 -*-
"""Mirror check — ตรวจสอบตัวเลขส่งออกของไทยจากฝั่งประเทศปลายทาง

หลักการ: การค้าหนึ่งรายการถูกรายงาน 2 ฝั่ง (ไทยรายงานว่าส่งออก / ปลายทางรายงานว่านำเข้า)
ถ้าทั้งสองฝั่งใกล้เคียงกัน = ข้อมูลน่าเชื่อถือ
ถ้าปลายทางรายงานเป็น 0 = ตัวเลขฝั่งไทยอาจเป็น artifact จากการจัดประเภทผิด

หมายเหตุ: รัสเซียหยุดส่งข้อมูลให้ Comtrade หลังปี 2022 จึง mirror ตรงๆ ไม่ได้
          จึงใช้ โปแลนด์/ลิทัวเนีย/สหรัฐฯ ซึ่งรายงานสม่ำเสมอ เป็นตัวทดสอบแทน
"""
import io
import sys
import time
import json
import pandas as pd
import requests

sys.path.insert(0, 'scripts')
from comtrade_fetch import load_api_key, CMD_DRONE, BASE_AUTH, BASE_PREVIEW

out = io.StringIO()
def p(*a): print(*a, file=out)

THAILAND = '764'
REPORTERS = {'Poland': '616', 'Lithuania': '440', 'USA': '842', 'Cambodia': '116'}

api_key = load_api_key()
url = BASE_AUTH if api_key else BASE_PREVIEW
headers = {'Ocp-Apim-Subscription-Key': api_key} if api_key else {}

# ---------- 0. ตรวจหน่วยของ qty ก่อน ----------
p('=' * 74)
p('0) หน่วยของ qty คืออะไร (ตรวจจาก raw JSON)')
p('=' * 74)
raw = json.loads(open('data/raw/comtrade_hs8806_thailand_partners.json', encoding='utf-8').read())
units = {}
for r in raw:
    k = (r.get('qtyUnitCode'), r.get('qtyUnitAbbr'))
    units[k] = units.get(k, 0) + 1
for (code, abbr), n in sorted(units.items(), key=lambda x: -x[1]):
    p(f'  qtyUnitCode={code}  abbr={abbr}  -> {n} แถว')
p()
p('  (unit code 5 / "u" = number of items คือ "จำนวนชิ้น" ตามมาตรฐาน Comtrade)')

# ---------- 1. ตัวเลขที่ไทยรายงาน ----------
p()
p('=' * 74)
p('1) ตัวเลขที่ "ไทย" รายงานว่าส่งออกไปแต่ละประเทศ')
p('=' * 74)
part = pd.read_csv('data/processed/comtrade_hs8806_thailand_partners.csv')
thai_side = {}
for name in REPORTERS:
    sub = part[(part['flow'] == 'export') & (part['partner'].astype(str).str.contains(name.replace('USA', 'USA'), case=False, na=False))]
    for _, r in sub.iterrows():
        thai_side[(name, int(r['year']))] = r['value_usd']
        p(f'  {name:<12} {int(r["year"])}: {r["value_usd"]:>14,.0f} USD')

# ---------- 2. ถามจากฝั่งปลายทาง ----------
p()
p('=' * 74)
p('2) ตัวเลขที่ "ประเทศปลายทาง" รายงานว่านำเข้าจากไทย')
p('=' * 74)

results = []
for name, code in REPORTERS.items():
    for year in ('2023', '2024'):
        params = {
            'reporterCode': code,
            'period': year,
            'cmdCode': CMD_DRONE,
            'flowCode': 'M',
            'partnerCode': THAILAND,
            'includeDesc': 'True',
            'breakdownMode': 'classic',
        }
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=90)
            if resp.status_code != 200:
                p(f'  {name:<12} {year}: HTTP {resp.status_code}')
                time.sleep(1.5)
                continue
            recs = resp.json().get('data', [])
            got = sum(r.get('primaryValue') or 0 for r in recs)
            theirs = got if recs else 0.0
            ours = thai_side.get((name, int(year)))
            if ours is None:
                p(f'  {name:<12} {year}: ปลายทางรายงาน {theirs:>14,.0f} USD   (ไทยไม่ได้รายงานคู่ค้านี้ปีนี้)')
            else:
                ratio = theirs / ours if ours else 0
                verdict = 'ตรงกันดี' if 0.5 <= ratio <= 2.0 else ('ไม่ตรง!' if theirs == 0 else 'ต่างมาก')
                p(f'  {name:<12} {year}: ไทยว่า {ours:>13,.0f} | ปลายทางว่า {theirs:>13,.0f} | '
                  f'อัตราส่วน {ratio:>5.2f}x  {verdict}')
                results.append((name, year, ours, theirs, ratio))
        except Exception as e:
            p(f'  {name:<12} {year}: error {e}')
        time.sleep(1.5)

# ---------- 3. สรุป ----------
p()
p('=' * 74)
p('3) สรุปผลการตรวจสอบ')
p('=' * 74)
if not results:
    p('  ไม่มีคู่ที่เทียบได้')
else:
    confirmed = [r for r in results if r[3] > 0]
    zero = [r for r in results if r[3] == 0]
    p(f'  เทียบได้ทั้งหมด {len(results)} คู่')
    p(f'  ปลายทางยืนยันว่ามีการนำเข้าจริง: {len(confirmed)} คู่')
    p(f'  ปลายทางรายงานเป็นศูนย์:          {len(zero)} คู่')
    if zero:
        p()
        p('  คู่ที่ปลายทางรายงาน 0 (น่าสงสัยว่าเป็น artifact):')
        for name, year, ours, theirs, _ in zero:
            p(f'    - {name} {year}: ไทยว่าส่งออก {ours:,.0f} USD แต่ปลายทางไม่รายงานเลย')

with open('scripts/comtrade_mirror_out.txt', 'w', encoding='utf-8') as f:
    f.write(out.getvalue())
print('done')
