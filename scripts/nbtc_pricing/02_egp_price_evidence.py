# -*- coding: utf-8 -*-
"""ขั้นที่ 2 — ขุด "ราคาต่อลำ" ของจริงออกจากสัญญา e-GP มาเป็นหลักฐานตั้งราคา

ทำไมต้องมี: ราคาที่ค้นจากเว็บเป็นราคาป้าย (ตั้งไว้เท่านี้) ส่วน e-GP เป็น **ราคาที่จ่ายจริง
ในไทย** และมีย้อนหลังถึงปีงบ 2558 จึงใช้ตั้งราคารุ่นเก่าที่เลิกขายแล้วได้ ซึ่งเว็บหาไม่เจอ

วิธี: คัดเฉพาะโครงการ "ซื้อตัวเครื่อง" (ตัดซ่อม/แบต/อะไหล่/เช่า/อบรมออก) →
ถอดจำนวนจากชื่อโครงการ (รองรับเลขไทย ๑๒๓) → ราคาต่อลำ = ราคาที่ตกลง ÷ จำนวน

🚨 ข้อจำกัดที่ต้องเขียนกำกับ:
  - ราคาภาครัฐมักรวมอุปกรณ์เสริม/ประกัน/อบรม จึงมักสูงกว่าราคาป้ายร้านค้า
  - ชื่อโครงการไม่ได้บอกชุดขาย (ตัวเปล่า/Fly More Combo) → ใช้เป็น "ช่วง" ไม่ใช่ค่าเดียว
  - n น้อยมากในหลายรุ่น — รุ่นที่ n<3 ให้ถือเป็นตัวชี้ทิศ ไม่ใช่ราคาอ้างอิง

ผลลัพธ์: data/processed/nbtc_pricing/egp_price_evidence.csv
รันจาก root:  python scripts/nbtc_pricing/02_egp_price_evidence.py
"""
import io
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
EGP = ROOT / "data" / "processed" / "egp_drone_projects.csv"
OUTDIR = ROOT / "data" / "processed" / "nbtc_pricing"
OUTTXT = Path(__file__).with_name("02_egp_price_evidence_out.txt")

out = io.StringIO()


def p(*a):
    print(*a, file=out)


df = pd.read_csv(EGP)
p("=" * 78)
p("ขั้นที่ 2 — ราคาต่อลำจากสัญญา e-GP")
p("=" * 78)
p(f"โครงการทั้งหมดในไฟล์: {len(df):,}")

NAME = "ชื่อโครงการ"
AGREED = "ราคาตกลงซื้อ/จ้าง"
BUDGET = "งบประมาณ(บาท)"

# ---------------------------------------------------------- 1) คัดเฉพาะ "ซื้อตัวเครื่อง"
# ตัดของที่ไม่ใช่ตัวเครื่องออก — ถ้าไม่ตัด ราคาต่อลำจะต่ำผิดเพราะไปรวมค่าซ่อม/แบตเตอรี่
NOT_AIRCRAFT = re.compile(
    r"ซ่อม|บำรุง|แบตเตอ|อะไหล่|ใบพัด|ชาร์จ|กระเป๋า|ประกัน|อบรม|ฝึก|หลักสูตร|"
    r"ซอฟต์แวร์|โปรแกรม|ลิขสิทธิ์|เช่า|ค่าบริการ|จ้างบิน|จ้างสำรวจ|จ้างถ่าย|"
    r"ต่อต้าน|ตรวจจับ|รบกวน|jammer|anti-?drone",
    re.I,
)
BUY = df["ชื่อประเภทโครงการ"].astype(str).str.contains("ซื้อ", na=False)
mask = BUY & ~df[NAME].astype(str).str.contains(NOT_AIRCRAFT, na=False)
buy = df[mask].copy()
p(f"เหลือหลังคัดเฉพาะ 'ซื้อตัวเครื่อง': {len(buy):,}")

# ---------------------------------------------------------------- 2) ถอดจำนวน
TH_DIGIT = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
QTY_RE = re.compile(r"จำนวน\s*([\d,]+)\s*(?:ตัว|เครื่อง|ลำ|ชุด|ระบบ)")


def get_qty(name):
    s = str(name).translate(TH_DIGIT)
    m = QTY_RE.search(s)
    if not m:
        return None
    try:
        q = int(m.group(1).replace(",", ""))
        return q if 1 <= q <= 500 else None
    except ValueError:
        return None


buy["qty"] = buy[NAME].map(get_qty)

# ราคาที่ใช้: ราคาตกลงจริงก่อน ถ้าเป็น 0 หรือว่าง (= ยังไม่ได้ผู้ชนะ) ค่อยใช้งบประมาณ
agreed = pd.to_numeric(buy[AGREED], errors="coerce")
budget = pd.to_numeric(buy[BUDGET], errors="coerce")
buy["price"] = agreed.where(agreed > 0, budget)
buy["price_from"] = ["ราคาตกลงจริง" if a > 0 else "งบประมาณ" for a in agreed.fillna(0)]

ok = buy[(buy["qty"].notna()) & (buy["price"] > 0)].copy()
ok["unit_price"] = ok["price"] / ok["qty"]
p(f"ระบุจำนวนได้และมีราคา    : {len(ok):,}")
p(f"  ในนั้นเป็นราคาตกลงจริง : {int((ok['price_from'] == 'ราคาตกลงจริง').sum()):,}")
p()

# ---------------------------------------------------- 3) จับรุ่นจากชื่อโครงการ
# เขียนแบบ "ตัวยาวมาก่อน" เพราะ Phantom 4 Pro ต้องไม่ถูก Phantom 4 คว้าไปก่อน
MODEL_PATTERNS = [
    ("DJI", "AGRAS T50", r"(?:AGRAS\s*)?T\s*-?50\b"),
    ("DJI", "AGRAS T40", r"(?:AGRAS\s*)?T\s*-?40\b"),
    ("DJI", "AGRAS T30", r"(?:AGRAS\s*)?T\s*-?30\b"),
    ("DJI", "AGRAS T25", r"(?:AGRAS\s*)?T\s*-?25\b"),
    ("DJI", "AGRAS T20P", r"(?:AGRAS\s*)?T\s*-?20\s*P\b"),
    ("DJI", "AGRAS T20", r"(?:AGRAS\s*)?T\s*-?20\b"),
    ("DJI", "AGRAS T16", r"(?:AGRAS\s*)?T\s*-?16\b"),
    ("DJI", "AGRAS T10", r"(?:AGRAS\s*)?T\s*-?10\b"),
    ("DJI", "AGRAS MG-1", r"\bMG\s*-?\s*1\s*[PS]?\b"),
    ("DJI", "MATRICE 350 RTK", r"(?:MATRICE|M)\s*-?350"),
    ("DJI", "MATRICE 300 RTK", r"(?:MATRICE|M)\s*-?300"),
    ("DJI", "MATRICE 30T", r"(?:MATRICE|M)\s*-?30\s*T"),
    ("DJI", "MATRICE 4T", r"(?:MATRICE|M)\s*-?4\s*T\b"),
    ("DJI", "MATRICE 4E", r"(?:MATRICE|M)\s*-?4\s*E\b"),
    ("DJI", "MAVIC 3 THERMAL", r"MAVIC\s*3.{0,12}(?:THERMAL|T\b)"),
    ("DJI", "MAVIC 3 ENTERPRISE", r"MAVIC\s*3.{0,12}(?:ENTERPRISE|3E\b)"),
    ("DJI", "MAVIC 3 CLASSIC", r"MAVIC\s*3\s*CLASSIC"),
    ("DJI", "MAVIC 3 PRO", r"MAVIC\s*3\s*PRO"),
    ("DJI", "MAVIC 3", r"MAVIC\s*3\b"),
    ("DJI", "MAVIC 2 PRO", r"MAVIC\s*2\s*PRO"),
    ("DJI", "MAVIC 2 ZOOM", r"MAVIC\s*2\s*ZOOM"),
    ("DJI", "MAVIC AIR 2", r"MAVIC\s*AIR\s*2"),
    ("DJI", "MAVIC AIR", r"MAVIC\s*AIR\b"),
    ("DJI", "MAVIC MINI", r"MAVIC\s*MINI"),
    ("DJI", "MAVIC PRO", r"MAVIC\s*PRO"),
    ("DJI", "AIR 3S", r"\bAIR\s*3\s*S\b"),
    ("DJI", "AIR 3", r"\bAIR\s*3\b"),
    ("DJI", "AIR 2S", r"\bAIR\s*2\s*S\b"),
    ("DJI", "PHANTOM 4 RTK", r"PHANTOM\s*4.{0,10}RTK"),
    ("DJI", "PHANTOM 4 PRO", r"PHANTOM\s*(?:4|๔).{0,8}PRO"),
    ("DJI", "PHANTOM 4 ADV", r"PHANTOM\s*(?:4|๔).{0,8}ADV"),
    ("DJI", "PHANTOM 4", r"PHANTOM\s*(?:4|๔)"),
    ("DJI", "PHANTOM 3 PRO", r"PHANTOM\s*(?:3|๓).{0,8}PRO"),
    ("DJI", "PHANTOM 3 ADV", r"PHANTOM\s*(?:3|๓).{0,8}ADV"),
    ("DJI", "PHANTOM 3 STANDARD", r"PHANTOM\s*(?:3|๓).{0,8}STANDARD"),
    ("DJI", "PHANTOM 3", r"PHANTOM\s*(?:3|๓)"),
    ("DJI", "INSPIRE 2", r"INSPIRE\s*2"),
    ("DJI", "INSPIRE 1", r"INSPIRE\s*1"),
    ("DJI", "MINI 4 PRO", r"MINI\s*4\s*PRO"),
    ("DJI", "MINI 3 PRO", r"MINI\s*3\s*PRO"),
    ("DJI", "MINI 3", r"MINI\s*3\b"),
    ("DJI", "MINI 2 SE", r"MINI\s*2\s*SE"),
    ("DJI", "MINI 2", r"MINI\s*2\b"),
    ("DJI", "MINI SE", r"MINI\s*SE"),
    ("DJI", "MINI 4K", r"MINI\s*4\s*K"),
    ("DJI", "AVATA 2", r"AVATA\s*2"),
    ("DJI", "AVATA", r"AVATA\b"),
    ("DJI", "FPV", r"\bFPV\b"),
    ("DJI", "SPARK", r"\bSPARK\b"),
    ("DJI", "TELLO", r"\bTELLO\b"),
]

rows = []
for _, r in ok.iterrows():
    name = str(r[NAME]).upper().translate(TH_DIGIT)
    for brand, model, pat in MODEL_PATTERNS:
        if re.search(pat, name):
            rows.append(
                {
                    "brand": brand,
                    "model": model,
                    "unit_price": r["unit_price"],
                    "qty": int(r["qty"]),
                    "year_be": r["_ปีงบ"],
                    "price_from": r["price_from"],
                    "project": str(r[NAME])[:110],
                }
            )
            break  # จับรุ่นแรกที่เจอเท่านั้น — กันนับซ้ำ

ev = pd.DataFrame(rows)
p(f"โครงการที่ระบุรุ่นได้    : {len(ev):,}  ({ev['model'].nunique() if len(ev) else 0} รุ่น)")
p()

if len(ev):
    # ตัดค่าที่หลุดโลกทิ้ง (ต่ำกว่า 3 พัน = ของชิ้นเล็ก · สูงกว่า 5 ล้าน/ลำ = ปนของอื่น)
    before = len(ev)
    ev = ev[(ev["unit_price"] >= 3_000) & (ev["unit_price"] <= 5_000_000)]
    p(f"ตัดราคาต่อลำที่หลุดช่วง 3,000–5,000,000 บาท ออก {before - len(ev)} แถว")
    p()

    agg = (
        ev.groupby(["brand", "model"])["unit_price"]
        .agg(n="count", p_min="min", p_median="median", p_max="max")
        .reset_index()
        .sort_values("n", ascending=False)
    )
    agg["years_be"] = [
        "-".join(
            str(int(x))
            for x in (
                ev[(ev.brand == b) & (ev.model == m)]["year_be"].min(),
                ev[(ev.brand == b) & (ev.model == m)]["year_be"].max(),
            )
        )
        for b, m in zip(agg["brand"], agg["model"])
    ]

    p("----- ราคาต่อลำจาก e-GP (บาท) -----")
    p(f"{'รุ่น':<22}{'n':>4}  {'ต่ำสุด':>12}{'มัธยฐาน':>13}{'สูงสุด':>13}   ปีงบ")
    for _, r in agg.iterrows():
        mark = "" if r["n"] >= 3 else "  ⚠️ n น้อย"
        p(f"{r['model']:<22}{r['n']:>4}  {r['p_min']:>12,.0f}{r['p_median']:>13,.0f}"
          f"{r['p_max']:>13,.0f}   {r['years_be']}{mark}")
    p()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    agg.to_csv(OUTDIR / "egp_price_evidence.csv", index=False, encoding="utf-8-sig")
    ev.to_csv(OUTDIR / "egp_price_rows.csv", index=False, encoding="utf-8-sig")

    p("ตัวอย่างแถวที่ใช้ (รุ่นละ 1 แถว):")
    for m in agg["model"].head(18):
        s = ev[ev.model == m].sort_values("unit_price").iloc[len(ev[ev.model == m]) // 2]
        p(f"  {m:<20} {s['unit_price']:>11,.0f} ฿/ลำ  (จำนวน {s['qty']}) {s['project'][:70]}")

p()
p("=" * 78)
p("⚠️ อ่านตัวเลขชุดนี้อย่างไร")
p("  - เป็นราคา **ภาครัฐ** มักรวมอุปกรณ์เสริม/ประกัน/อบรม → สูงกว่าราคาป้ายร้านค้า")
p("  - ชื่อโครงการไม่บอกชุดขาย (ตัวเปล่า / Fly More Combo) → ใช้เป็นช่วง ไม่ใช่ค่าเดียว")
p("  - รุ่นที่ n < 3 เป็นตัวชี้ทิศเท่านั้น")
p("  - ไม่ครอบคลุมตลาดเอกชน ซึ่งเป็นส่วนใหญ่ของทะเบียน กสทช.")

OUTTXT.write_text(out.getvalue(), encoding="utf-8")
print(out.getvalue())
