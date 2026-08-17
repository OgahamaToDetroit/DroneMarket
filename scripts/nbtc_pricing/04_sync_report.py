"""ขั้นที่ 4 — ทำให้ตัวเลขในเอกสารตรงกับผลรันเสมอ

ทำสองอย่างที่แก้ปัญหาคนละชนิดกัน:

  ก) **เขียนตารางลงเอกสารเอง** (แก้ที่ต้นเหตุ)
     ตารางที่ทุกช่องมาจากผลรันปัจจุบัน จะถูกสร้างใหม่ทุกครั้งที่รัน
     ตัวเลขในตารางพวกนี้จึงไม่มีทางค้างอีก เพราะไม่มีใครพิมพ์มัน

  ข) **ตรวจตัวเลขที่อยู่กลางประโยค** (แก้ที่ปลายเหตุ)
     ตัวเลขที่ฝังอยู่ในข้อความบรรยาย generate ไม่ได้ เพราะบริบทเป็นของคนเขียน
     จึงได้แค่ตรวจว่ายังตรงกับผลรันไหม แล้วฟ้องถ้าไม่ตรง

🚨 สิ่งที่สคริปต์นี้ทำไม่ได้: ตรวจว่า**ตีความ**ถูกไหม
ตัวเลขตรงทุกช่องไม่ได้แปลว่าข้อความรอบ ๆ พูดถูก — ข้อความยังต้องอ่านเอง
(เป็นข้อจำกัดเดียวกับที่ verify_customs_docs.py เขียนกำกับตัวเองไว้)

🚨 ตารางที่ **ห้าม** ให้สคริปต์เขียน: ตารางเทียบ "ก่อน/หลัง"
คอลัมน์ "ก่อน" เป็นค่าที่ตรึงไว้เป็นประวัติ ถ้าให้สคริปต์สร้างใหม่ มันจะเขียนค่าปัจจุบัน
ลงทั้งสองคอลัมน์ = ลบประวัติทิ้ง ซึ่งขัดกฎ "ห้ามแก้รายงานย้อนหลัง" ของโปรเจกต์

รันหลังขั้นที่ 3:  python scripts/nbtc_pricing/04_sync_report.py
ออก exit 1 ถ้ามีตัวเลขในข้อความที่ไม่ตรงกับผลรัน
"""
import io
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "data" / "processed" / "nbtc_pricing"
REF = ROOT / "data" / "reference"
REPORT = ROOT / "reports" / "2026-08-04_nbtc-unit-value" / "README.md"
DATA_MD = ROOT / "DATA.md"
OUTTXT = Path(__file__).with_name("04_sync_report_out.txt")

out = io.StringIO()


def p(*a):
    print(*a, file=out)


# ------------------------------------------------------------------ 1) โหลดผลรัน
by_year = pd.read_csv(OUTDIR / "market_value_by_year.csv", encoding="utf-8-sig")
brackets = pd.read_csv(OUTDIR / "unpriced_brackets.csv", encoding="utf-8-sig")
by_model = pd.read_csv(OUTDIR / "market_value_by_model.csv", encoding="utf-8-sig")
ycov = pd.read_csv(OUTDIR / "year_coverage.csv", encoding="utf-8-sig")
prices = pd.read_csv(REF / "nbtc_model_prices.csv", encoding="utf-8-sig")
catalog = pd.read_csv(OUTDIR / "model_catalog.csv", encoding="utf-8-sig")
unpriced = pd.read_csv(OUTDIR / "unpriced_models.csv", encoding="utf-8-sig")

# ปีที่ข้อมูลไม่ครบ 12 เดือน — ต้องติดป้าย ⚠️ ในตาราง ไม่งั้นคนจะเอาไปเทียบกับปีเต็ม
PARTIAL = {int(r["year"]): int(r["months"]) for _, r in ycov.iterrows() if int(r["months"]) < 12}
LATEST_FULL = max(y for y in by_year["year"] if int(y) not in PARTIAL)

MONTH_LABEL = {2017: "ต.ค.-ธ.ค.", 2026: "ม.ค.-มิ.ย."}


def be(y: int) -> str:
    return str(int(y) + 543)


def mb(v) -> int:
    """บาท → ล้านบาท (ปัดเป็นจำนวนเต็ม เท่ากับที่ผลรันพิมพ์)"""
    return round(float(v) / 1e6)


# ------------------------------------------------------- 2) สร้างตารางมูลค่ารายปี
def build_yearly() -> str:
    rows = ["| ปี | ลำทั้งหมด | ตั้งราคาได้ | coverage | **วัดได้ (ลบ.)** | ÷coverage | ขอบบน |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for _, r in by_year.iterrows():
        y = int(r["year"])
        label = be(y)
        if y in PARTIAL:
            label = f"{be(y)} ({MONTH_LABEL.get(y, f'{PARTIAL[y]}/12 เดือน')}) ⚠️"
        cells = [f"{int(r['units_all']):,}", f"{int(r['units']):,}",
                 f"{r['coverage']:.0%}", f"{mb(r['val']):,}",
                 f"{mb(r['val_scaled']):,}", f"{mb(r['val_hi']):,}"]
        # ปีเต็มล่าสุด = ตัวเลขที่คนหยิบไปใช้บ่อยสุด ทำตัวหนาให้หาเจอง่าย
        if y == LATEST_FULL:
            label = f"**{label}**"
            cells[3] = f"**{cells[3]}**"
            cells[4] = f"**{cells[4]}**"
        rows.append("| " + " | ".join([label, *cells]) + " |")
    tot = ["*205,287*", f"*{int(by_model['units'].sum()):,}*",
           f"*{by_model['units'].sum() / 205287:.0%}*",
           f"*{mb(by_model['val'].sum()):,}*",
           f"*{mb(by_year['val_scaled'].sum()):,}*",
           f"*{mb(by_year['val_hi'].sum()):,}*"]
    rows.append("| *สะสมทุกปี* | " + " | ".join(tot) + " |")
    return "\n".join(rows)


# --------------------------------------------- 3) สร้างตารางส่วนที่ยังตีราคาไม่ได้
# ที่มาของช่วงราคาแต่ละกลุ่ม — เป็นคำอธิบายวิธี ไม่ใช่ตัวเลข จึงเขียนไว้ตรงนี้ได้
# ถ้ากลุ่มไหนไม่มีในตารางนี้ สคริปต์จะเว้นว่างแทนการเดา
BRACKET_SRC = {
    "ทั่วไป": "เปอร์เซ็นไทล์ 10/90 ของราคาที่มี",
    "เกษตร-DJI": "เปอร์เซ็นไทล์ 10/90 ของราคาที่มี",
    "เกษตร-ไม่ใช่ DJI (ไม่มีเบาะแส)": "⚠️ ขอบล่างสุด-บนสุด ฐานบาง",
    "เกษตร-ไม่ใช่ DJI (ชื่อบอกลิตร)": "เส้นราคาต่อความจุ (ชั้น 3)",
}
# กลุ่มที่ไม่มีในไฟล์ผลลัพธ์เพราะจงใจไม่ประมาณ — ต้องแสดงในตารางด้วย ไม่งั้นจำนวนลำจะหาย
FLEET_ROW = "จดเป็นฝูง (ประมาณไม่ได้)"


def build_brackets() -> str:
    rows = ["| กลุ่ม | ลำ | ช่วงราคาของกลุ่ม | ที่มาของช่วง | มูลค่าขั้นต่ำ | มูลค่าขั้นสูง |",
            "|---|---:|---:|---|---:|---:|"]
    for _, r in brackets.iterrows():
        cls = str(r["class"])
        band = f"{int(r['lo']):,} – {int(r['hi']):,} ฿" if pd.notna(r["lo"]) else "—"
        rows.append(f"| {cls} | {int(r['units']):,} | {band} | {BRACKET_SRC.get(cls, '')} | "
                    f"{mb(r['val_lo']):,} ลบ. | {mb(r['val_hi']):,} ลบ. |")
    # กลุ่มฝูงไม่อยู่ใน unpriced_brackets.csv เพราะไม่มีค่าประมาณ ต้องดึงจำนวนลำจากอีกทาง
    n_fleet = int(unpriced["units"].sum()) - int(brackets["units"].sum())
    if n_fleet > 0:
        rows.append(f"| **{FLEET_ROW}** | **{n_fleet:,}** | — | **ประมาณไม่ได้** | **—** | **—** |")
    rows.append(f"| **รวม** | **{int(unpriced['units'].sum()):,}** | | | "
                f"**{mb(brackets['val_lo'].sum()):,} ลบ.** | "
                f"**{mb(brackets['val_hi'].sum()):,} ลบ.** |")
    return "\n".join(rows)


# ------------------------------------------------- 4) แทรกลงเอกสารระหว่าง marker
def inject(path: Path, key: str, block: str) -> str:
    """แทนที่เนื้อหาระหว่าง marker คู่ — รันซ้ำได้ ไม่ซ้อนทับ

    🚨 marker ต้องครอบ **เฉพาะแถวตาราง** ห้ามครอบข้อความเตือนรอบ ๆ
    ไม่งั้นรอบรันถัดไปจะลบข้อความเหล่านั้นทิ้งเงียบ ๆ ซึ่งเป็นเนื้อหาที่มีค่าที่สุดในรายงาน
    """
    m = f"<!--TABLE_{key}-->"
    t = path.read_text(encoding="utf-8")
    start = t.find(m)
    if start == -1:
        return f"⏭️ {path.name}: ไม่มี marker {m} — ข้าม"
    end = t.find(m, start + len(m))
    if end == -1:
        return f"🚨 {path.name}: มี marker {m} แค่ตัวเดียว ต้องมีเป็นคู่ — ไม่แทรก"
    new = t[:start] + f"{m}\n{block}\n{m}" + t[end + len(m):]
    if new == t:
        return f"✓ {path.name}: {key} ตรงอยู่แล้ว ไม่ต้องเขียน"
    path.write_text(new, encoding="utf-8")
    return f"✏️ {path.name}: เขียน {key} ใหม่"


# --------------------------------------------- 5) ตรวจตัวเลขที่อยู่กลางประโยค
# ตัวเลขพวกนี้ฝังในข้อความ generate ไม่ได้ จึงตรวจอย่างเดียว
# 🚨 ต้องเทียบแบบ "ต้องมีข้อความนี้ตรง ๆ" ไม่ใช่ "เลขนี้โผล่ที่ไหนสักแห่งไหม"
# เพราะตัวเลขเดียวกันโผล่ได้หลายที่ในไฟล์ ทำให้ตัวตรวจขึ้นเขียวทั้งที่ช่องนั้นผิด
# (กับดักเดียวกับที่ verify_customs_docs.py เจอตอนแก้ 1,830 เป็น 1,999 แล้วยังผ่าน)
def sentence_checks() -> list[tuple[str, str, Path]]:
    n_priced = int(by_model["units"].sum())
    capped = by_model[by_model["capped_from"].notna()
                      & (by_model["capped_from"].astype(str).str.strip() != "")]
    # 🚨 ต้องนับจาก unpriced_models ไม่ใช่ brackets — เพราะกลุ่มฝูงไม่มีในไฟล์ brackets
    # (จงใจไม่ประมาณ) ถ้านับจาก brackets จะหายไป 6 พันกว่าลำโดยไม่มีอะไรเตือน
    n_unpriced = int(unpriced["units"].sum())
    y2025 = by_year[by_year["year"] == 2025].iloc[0]
    return [
        ("จำนวนรุ่นในตารางราคา", f"ราคา {len(prices)} รุ่น", REPORT),
        ("จำนวนคู่ในแคตตาล็อก", f"แคตตาล็อกรุ่น {len(catalog):,} คู่", REPORT),
        ("รุ่นที่ถูกกดราคา", f"กดราคา {len(capped)} รุ่นลง ({int(capped['units'].sum()):,} ลำ)", REPORT),
        ("ลำที่ตั้งราคาได้ (หัวข้อ)", f"{n_priced:,} ลำที่ตั้งราคาได้", REPORT),
        ("ลำที่ยังตีราคาไม่ได้ (หัวข้อ)", f"ส่วนที่ยังตีราคาไม่ได้ {n_unpriced:,} ลำ", REPORT),
        ("ปี 2568 ใน DATA.md", f"ตั้งราคาได้ {n_priced:,} ลำ", DATA_MD),
        ("ช่วงปี 2568 ใน DATA.md", f"{mb(y2025['val']):,}–{mb(y2025['val_scaled']):,} ล้านบาท", DATA_MD),
    ]


# --------------------------------------------------------------------- ทำงานจริง
p("=" * 78)
p("ขั้นที่ 4 — ทำให้ตัวเลขในเอกสารตรงกับผลรัน")
p("=" * 78)
p()
p("----- ก) เขียนตารางลงเอกสาร -----")
for path, key, block in [
    (REPORT, "YEARLY", build_yearly()),
    (REPORT, "BRACKETS", build_brackets()),
    (DATA_MD, "YEARLY_SHORT", None),
]:
    if block is None:
        # DATA.md ใช้ตารางย่อ 2 ปีล่าสุดที่ครบปี
        rows = ["| ปี | ตั้งราคาได้ (ลำ) | ทั้งหมด (ลำ) | มูลค่า (ล้านบาท) | หารด้วย coverage |",
                "|---|---|---|---|---|"]
        for y in [yr for yr in by_year["year"] if int(yr) not in PARTIAL][-2:]:
            r = by_year[by_year["year"] == y].iloc[0]
            val, scaled = f"{mb(r['val']):,}", f"{mb(r['val_scaled']):,}"
            if int(y) == LATEST_FULL:
                val, scaled = f"**{val}**", f"**{scaled}**"
            rows.append(f"| {be(y)} | {int(r['units']):,} | {int(r['units_all']):,} | "
                        f"{val} | {scaled} |")
        block = "\n".join(rows)
    p("  " + inject(path, key, block))
p()

p("----- ข) ตรวจตัวเลขที่อยู่กลางประโยค -----")
p("  วิธีตรวจ: หาข้อความเต็มวลี ไม่ใช่หาเฉพาะตัวเลข")
p("  เพราะตัวเลขเดียวกันโผล่ได้หลายที่ ทำให้ตัวตรวจขึ้นเขียวทั้งที่ช่องนั้นผิด")
p()
fails = []
checked = 0
for label, phrase, path in sentence_checks():
    if not path.exists():
        p(f"  ⏭️ {label}: ไม่มีไฟล์ {path.name}")
        continue
    checked += 1
    if phrase in path.read_text(encoding="utf-8"):
        p(f"  ✅ {label:<28} · {phrase}")
    else:
        p(f"  ❌ {label:<28} · ไม่พบวลี: {phrase}")
        fails.append((label, phrase, path.name))
p()
p(f"  ตรวจจริง {checked} วลี · ผ่าน {checked - len(fails)} · ไม่ผ่าน {len(fails)}")
if fails:
    p()
    p("  🚨 ต้องแก้เอกสารให้ตรงกับผลรัน (หรือแก้สคริปต์ถ้าวลีในเอกสารเปลี่ยนรูปไปแล้ว)")
    for label, phrase, fname in fails:
        p(f"     {fname}: {label} — ควรเขียนว่า '{phrase}'")
p()
p("⚠️ สคริปต์นี้ตรวจแค่ตัวเลข **ไม่ได้ตรวจว่าตีความถูกไหม**")
p("   ตัวเลขตรงทุกช่องไม่ได้แปลว่าข้อความรอบ ๆ พูดถูก — ข้อความยังต้องอ่านเอง")

OUTTXT.write_text(out.getvalue(), encoding="utf-8")
print(out.getvalue())
sys.exit(1 if fails else 0)
