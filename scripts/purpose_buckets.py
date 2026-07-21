# -*- coding: utf-8 -*-
"""Consolidate the messy multi-value PurposeOfUseAircraft column into clean buckets.
A single registration can list multiple purposes (comma-separated), so bucket
counts are multi-label (a row may count toward more than one bucket) while the
denominator stays fixed at total registrations for intuitive percentages.
"""
import pandas as pd
import io, json

out = io.StringIO()
def p(*a): print(*a, file=out)

df = pd.read_excel('data/raw/drone_data.xlsx')
total = len(df)

buckets = {
    'เกษตรกรรม': ['เกษตร'],
    'งานอดิเรก/ถ่ายภาพ/กีฬา': ['งานอดิเรก', 'กีฬา', 'บันเทิง'],
    'ถ่ายภาพ/ถ่ายทำภาพยนตร์': ['ถ่ายภาพ', 'ภาพยนตร์', 'โทรทัศน์', 'รายงานข่าว'],
    'กิจกรรมองค์กร/บริษัท': ['บริษัท', 'หน่วยงาน'],
}

counts = {k: 0 for k in buckets}
counts['อื่นๆ/ไม่ระบุ'] = 0

def classify(s):
    if not isinstance(s, str) or not s.strip():
        return []
    hits = []
    for bucket, keywords in buckets.items():
        if any(kw in s for kw in keywords):
            hits.append(bucket)
    return hits

none_count = 0
for val in df['PurposeOfUseAircraft']:
    hits = classify(val)
    if hits:
        for h in hits:
            counts[h] += 1
    else:
        counts['อื่นๆ/ไม่ระบุ'] += 1

p('TOTAL REGISTRATIONS:', total)
p()
p('===== Consolidated purpose buckets (multi-label, % of total) =====')
for k, v in sorted(counts.items(), key=lambda x: -x[1]):
    p(f'  {k:<28} {v:>7,}  ({v/total*100:5.2f}%)')

# sanity: how many rows had 2+ tags
multi = sum(1 for val in df['PurposeOfUseAircraft'] if len(classify(val)) >= 2)
p()
p('Rows tagged with 2+ purposes:', multi, f'({multi/total*100:.2f}%)')

with open('scripts/purpose_buckets_out.txt', 'w', encoding='utf-8') as f:
    f.write(out.getvalue())

with open('data/processed/purpose_buckets.json', 'w', encoding='utf-8') as f:
    json.dump({'total': total, 'counts': counts}, f, ensure_ascii=False, indent=2)

print('done')
