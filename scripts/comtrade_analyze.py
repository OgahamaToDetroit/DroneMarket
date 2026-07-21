# -*- coding: utf-8 -*-
"""วิเคราะห์ข้อมูลการค้าโดรน HS 8806 ของไทย + เชื่อมกับข้อมูลทะเบียน กสทช.

รันหลัง comtrade_fetch.py แล้ว (ต้องมีทั้ง _world.csv และ _partners.csv)
"""
import io
import pandas as pd

out = io.StringIO()
def p(*a): print(*a, file=out)

world = pd.read_csv('data/processed/comtrade_hs8806_thailand_world.csv')
part = pd.read_csv('data/processed/comtrade_hs8806_thailand_partners.csv')

# ---------- 1. ภาพรวมรายปี ----------
p('=' * 70)
p('1) มูลค่าการค้าโดรนไทย HS 8806 รายปี (USD)')
p('=' * 70)
piv = world.pivot_table(index='year', columns='flow', values='value_usd', aggfunc='sum').fillna(0)
prev_i = prev_e = None
for y, r in piv.iterrows():
    imp, exp = r.get('import', 0), r.get('export', 0)
    gi = f'{(imp/prev_i-1)*100:+6.1f}%' if prev_i else '     —'
    ge = f'{(exp/prev_e-1)*100:+8.1f}%' if prev_e else '       —'
    p(f'  {int(y)}:  import {imp:>13,.0f} ({gi})  |  export {exp:>12,.0f} ({ge})  |  net {imp-exp:>13,.0f}')
    prev_i, prev_e = imp, exp

p()
p('  ขนาดตลาดนำเข้าโต {:.1f} เท่า จาก 2022 -> 2024'.format(
    piv.loc[2024, 'import'] / piv.loc[2022, 'import']))
p('  การส่งออกโต {:.0f} เท่า จาก 2022 -> 2024'.format(
    piv.loc[2024, 'export'] / piv.loc[2022, 'export']))

# ---------- 2. นำเข้า: กระจุกตัวแค่ไหน ----------
p()
p('=' * 70)
p('2) การนำเข้า — แหล่งที่มา')
p('=' * 70)
imp = part[part['flow'] == 'import']
for y in sorted(imp['year'].unique()):
    sub = imp[imp['year'] == y].sort_values('value_usd', ascending=False)
    tot = sub['value_usd'].sum()
    p(f'\n  ปี {int(y)} (รวม {tot:,.0f} USD, {len(sub)} คู่ค้า)')
    for _, r in sub.head(5).iterrows():
        p(f'    {str(r["partner"])[:26]:<28} {r["value_usd"]:>13,.0f}  ({r["value_usd"]/tot*100:5.2f}%)')

# ---------- 3. ส่งออก: ปลายทางเปลี่ยนไปยังไง ----------
p()
p('=' * 70)
p('3) การส่งออก — ปลายทางเปลี่ยนไปอย่างไร')
p('=' * 70)
exp = part[part['flow'] == 'export']
for y in sorted(exp['year'].unique()):
    sub = exp[exp['year'] == y].sort_values('value_usd', ascending=False)
    tot = sub['value_usd'].sum()
    p(f'\n  ปี {int(y)} (รวม {tot:,.0f} USD, {len(sub)} ปลายทาง)')
    for _, r in sub.head(6).iterrows():
        p(f'    {str(r["partner"])[:26]:<28} {r["value_usd"]:>13,.0f}  ({r["value_usd"]/tot*100:5.2f}%)')

# ---------- 4. ไทยเป็นคู่ค้าตัวเอง = re-import/re-export ----------
p()
p('=' * 70)
p('4) รายการที่คู่ค้า = ไทยเอง (re-import / re-export)')
p('=' * 70)
self_trade = part[part['partner_code'] == 764]
if self_trade.empty:
    p('  ไม่มี')
else:
    for _, r in self_trade.sort_values(['year', 'flow']).iterrows():
        p(f'  {int(r["year"])} {r["flow"]:<7} {r["value_usd"]:>13,.0f} USD')

# ---------- 5. เชื่อมกับข้อมูล กสทช. ----------
p()
p('=' * 70)
p('5) เชื่อมกับทะเบียน กสทช. — มูลค่าต่อเครื่องโดยนัย')
p('=' * 70)
reg = pd.read_csv('data/processed/summary_by_year.csv')
reg.columns = ['year', 'registrations']
reg = reg.set_index('year')['registrations'].to_dict()

p(f'  {"ปี":<6}{"จดทะเบียน(ลำ)":>15}{"นำเข้าสุทธิ(USD)":>20}{"USD/ลำ":>12}')
p('  ' + '-' * 51)
for y in sorted(piv.index):
    if y not in reg:
        continue
    net = piv.loc[y, 'import'] - piv.loc[y, 'export']
    n = reg[y]
    p(f'  {int(y):<6}{n:>15,}{net:>20,.0f}{net/n:>12,.0f}')
p()
p('  * "นำเข้าสุทธิ" = นำเข้า - ส่งออก คือของที่น่าจะเหลืออยู่ในประเทศจริง')
p('  * ตัวเลข USD/ลำ เป็นค่าเฉลี่ยคร่าวๆ ไม่ใช่ราคาขายปลีก (ไม่รวมภาษี/กำไรผู้ขาย)')

# ---------- 6. ตรวจสอบความสอดคล้อง ----------
p()
p('=' * 70)
p('6) ตรวจสอบความถูกต้องของข้อมูล')
p('=' * 70)
for y in sorted(piv.index):
    for flow in ('import', 'export'):
        w = piv.loc[y, flow]
        pt = part[(part['year'] == y) & (part['flow'] == flow)]['value_usd'].sum()
        diff = abs(w - pt)
        flag = 'OK ' if diff / max(w, 1) < 0.005 else 'ต่าง!'
        p(f'  {int(y)} {flow:<7} world={w:>13,.0f}  sum(partners)={pt:>13,.0f}  {flag}')
p()
p('  (ถ้าตรงกัน = ยืนยันว่าไม่มีการนับซ้ำจาก breakdownMode/partnerCode=0)')

with open('scripts/comtrade_analyze_out.txt', 'w', encoding='utf-8') as f:
    f.write(out.getvalue())
print('done')
