# -*- coding: utf-8 -*-
"""ขั้นที่ 3 — ประเมินมูลค่าตลาดจาก (จำนวนลำที่จดทะเบียน × ราคาต่อลำ)

ทำไมวิธีนี้ถึงมีค่า: ตัวเลขศุลกากร (SOURCES.md §8) วัดอุปสงค์ในประเทศไม่ได้เพราะปี 2568
มีถึง 70% ของยอดนำเข้าที่เป็น "ของผ่าน" (เข้ามาแล้วส่งออกต่อ) — แต่ **ของผ่านไม่มาจดทะเบียน
กับ กสทช.** วิธีนับลำแล้วคูณราคาจึงไม่มีรูนั้น

ฐานที่รายงาน (ตามที่ตกลงไว้):
  ก) ราคาขายปลีกในไทย รวม VAT       — เงินที่ผู้ใช้จ่ายจริง
  ข) ฐานเทียบนำเข้า (หัก VAT + กำไรตัวแทน) — ให้เทียบกับตัวเลขศุลกากรได้

กติกาตั้งราคา (ข้อเดียว ใช้ทุกแถว):
  ใช้ **ราคาไทยที่ต่ำที่สุดที่มีหลักฐาน** สำหรับตัวเครื่อง+รีโมต · ไม่เอาราคาล้างสต๊อก
  ถ้าไม่มีราคาตัวเปล่า → ใช้ชุดคอมโบแล้วติดป้าย · ถ้าไม่มีเลย → ใช้สัญญาภาครัฐแล้วติดป้าย
  ถ้ายังไม่มี → **ไม่ตั้งราคา** ไปอยู่ในกลุ่ม "ยังตีราคาไม่ได้" ซึ่งรายงานเป็นช่วงแยกต่างหาก
  → ตัวเลขที่ได้จึงเป็น **ขอบล่าง** โดยการออกแบบ

รันจาก root:  python scripts/nbtc_pricing/03_estimate_market_value.py
"""
import io
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PROC = ROOT / "data" / "processed"
OUTDIR = PROC / "nbtc_pricing"
REF = ROOT / "data" / "reference"
OUTTXT = Path(__file__).with_name("03_estimate_market_value_out.txt")

# ---- พารามิเตอร์ที่เปลี่ยนได้ (เขียนไว้ตรงนี้ ไม่ฝังในสูตร) ----
VAT = 0.07
MARGIN_LO, MARGIN_HI = 0.10, 0.25  # กำไรตัวแทน/ร้านค้า — ช่วงที่ใช้แปลงกลับเป็นฐานนำเข้า
AGRI_THRESHOLD = 0.60              # ≥60% ของลำแจ้งวัตถุประสงค์เกษตร = รุ่นโดรนเกษตร

out = io.StringIO()


def p(*a):
    print(*a, file=out)


def bt(x):
    """ล้านบาท"""
    return f"{x / 1e6:,.0f}"


def save(df_, path):
    """เขียน CSV แบบไม่ให้ไฟล์ที่เปิดค้างใน Excel ทำให้ทั้งรันพัง

    เจอจริงตอนพัฒนา: เปิด unpriced_models.csv ดูใน Excel ค้างไว้ แล้วรันสคริปต์
    → PermissionError ตอนเขียนไฟล์สุดท้าย ทิ้งงานที่คำนวณเสร็จแล้วทั้งหมด
    """
    try:
        df_.to_csv(path, index=False, encoding="utf-8-sig")
    except PermissionError:
        alt = path.with_suffix(".new.csv")
        df_.to_csv(alt, index=False, encoding="utf-8-sig")
        p(f"  ⚠️ {path.name} เปิดค้างอยู่ (น่าจะใน Excel) — เขียนลง {alt.name} แทน")


# --------------------------------------------------------------- 1) โหลด
cat = pd.read_csv(OUTDIR / "model_catalog.csv")
long = pd.read_csv(OUTDIR / "registrations_by_model_year.csv")
codemap = pd.read_csv(REF / "nbtc_code_map.csv")
prices = pd.read_csv(REF / "nbtc_model_prices.csv")
ycov = pd.read_csv(OUTDIR / "year_coverage.csv")
nbtc_months = dict(zip(ycov["year"].astype(int), ycov["months"].astype(int)))

N_TOTAL = int(long["units"].sum())

p("=" * 80)
p("ขั้นที่ 3 — มูลค่าตลาดโดรนไทย จากทะเบียน กสทช. × ราคาต่อลำ")
p("=" * 80)
p(f"ลำที่จดทะเบียนทั้งหมด : {N_TOTAL:,}")
p(f"รุ่นในแคตตาล็อก       : {len(cat):,}")
p(f"รุ่นที่มีราคา          : {len(prices):,}")
p()

# ------------------------------------------------- 2) รวมรหัสเข้าเป็นชื่อรุ่นเดียว
# ตาราง code map ย้ายได้ทั้งชื่อรุ่นและยี่ห้อ
# ที่ต้องย้ายยี่ห้อด้วย เพราะบางแถวช่อง Brand ถูกกรอกมั่ว (เช่น "AG" ย่อจาก Agras ทั้งที่เป็น DJI)
# ถ้าย้ายแต่ชื่อรุ่น ราคาจะจับคู่ไม่ติดเพราะตารางราคาคีย์ด้วย (ยี่ห้อ, รุ่น)
amap = {
    (b, m): (rb if isinstance(rb, str) and rb.strip() else b, rm)
    for b, m, rb, rm in zip(
        codemap["brand"], codemap["catalog_model"],
        codemap["resolved_brand"], codemap["resolved_model"],
    )
}
REBRAND = {
    (b, m) for b, m, rb in zip(codemap["brand"], codemap["catalog_model"], codemap["resolved_brand"])
    if isinstance(rb, str) and rb.strip()
}
# ต้องนับ "ลำที่ถูกย้าย" จากยี่ห้อ/รุ่นเดิม ก่อนเขียนทับ ไม่งั้นจะไปนับของที่อยู่ปลายทางอยู่แล้วด้วย
n_moved = int(long[[(b, m) in amap for b, m in zip(long["brand"], long["model"])]]["units"].sum())
n_rebrand = int(long[[(b, m) in REBRAND for b, m in zip(long["brand"], long["model"])]]["units"].sum())
rebrand_from = sorted({b for b, _ in REBRAND})

for d in (long, cat):
    # ต้องจำไว้ตรงนี้ว่าแถวไหนถูก code map ถอดให้ เพราะบรรทัดล่างจะเขียนทับช่อง brand
    # หลังจากนั้นจะเช็ค (brand, model) กับ amap ไม่ได้อีก — คู่กุญแจเปลี่ยนไปแล้ว
    d["_moved"] = [(b, m) in amap for b, m in zip(d["brand"], d["model"])]
    pairs = [amap.get((b, m), (b, m)) for b, m in zip(d["brand"], d["model"])]
    d["brand"] = [x[0] for x in pairs]
    d["model_final"] = [x[1] for x in pairs]

p(f"แถวที่ถูกรวมด้วยตาราง code map: {n_moved:,} ลำ")
p(f"  ในนั้นเป็นการ**ย้ายยี่ห้อ**ด้วย {n_rebrand:,} ลำ จากช่อง Brand ที่กรอกมั่ว: "
  f"{', '.join(rebrand_from)}")

# ชั้นของรุ่น (เกษตร/ทั่วไป) — ยึดตามจำนวนลำ ไม่ใช่ตามจำนวนรูปเขียน
cls = (
    cat.groupby(["brand", "model_final"])
    .apply(lambda g: (g["agri_units"].sum() / g["units"].sum()), include_groups=False)
    .rename("agri_share")
    .reset_index()
)
cls["class"] = np.where(cls["agri_share"] >= AGRI_THRESHOLD, "เกษตร", "ทั่วไป")

# --------------------------------- 2.5) กันราคาผกผัน: รุ่นเก่าต้องไม่แพงกว่ารุ่นที่ใหม่กว่า
# ทำไมต้องมี: ราคาที่เก็บมาจากคนละแหล่ง (ป้ายร้านทางการ / ร้านตัวแทน / สัญญาภาครัฐ) และคนละชุดขาย
# จึงเกิดกรณีที่รุ่นเก่าแพงกว่ารุ่นใหม่ในสายเดียวกัน ซึ่งเป็นไปไม่ได้ในตลาดจริง
# กติกา: ราคาของรุ่นหนึ่ง ต้องไม่เกินราคาสูงสุดของรุ่นที่ "เจเนอเรชันใหม่กว่า" ในสายเดียวกัน
# (เขียนเป็นกติกาในโค้ด ไม่ใช่พิมพ์ตัวเลขทับเอง — และรายงานทุกครั้งที่กติกาทำงาน)
tiers = pd.read_csv(REF / "nbtc_model_tiers.csv").rename(columns={"model": "model_final"})
prices = prices.rename(columns={"model": "model_final"}).merge(
    tiers[["brand", "model_final", "tier", "gen", "price_rule"]],
    on=["brand", "model_final"], how="left",
)

# 🚨 กติกานี้ใช้ได้เฉพาะสินค้าที่ราคาเรียงตาม "เจเนอเรชัน" คือโดรนถ่ายภาพ
# โดรนเกษตรราคาเรียงตาม **ขนาดถัง** ไม่ใช่ปีที่ออก — ของเก่าถังเล็กแพงกว่าของใหม่ถังใหญ่ได้จริง
# (AGRAS MG-1 ปี 2015 ถัง 10 ล. = 267,000 ปะทะ T20P ถัง 20 ล. = 220,000)
# ถ้าปล่อยให้กติกานี้จับเกษตรด้วย มันจะกด MG ลงเหลือราคาต่ำสุดของสาย T = กลบราคาจริงทิ้ง
# คอลัมน์ price_rule ใน nbtc_model_tiers.csv เป็นตัวบอกว่าแถวไหนใช้กติกาไหน
GEN_RULE = "เจเนอเรชัน"

# ⚠️ ต้องอ่านราคาจาก "ภาพก่อนแก้" ไม่ใช่จากตารางที่กำลังถูกแก้อยู่
# ไม่งั้นการแก้แถวหนึ่งจะไหลไปกดอีกแถว และผลลัพธ์จะขึ้นกับลำดับแถวใน CSV
base_price = prices["price_thb"].copy()
# เก็บ "ราคาที่เก็บมาก่อนถูกกด" ไว้ทุกแถว เพื่อให้ไฟล์ผลลัพธ์บอกได้ว่าแถวไหนถูกแก้
# ถ้าไม่เก็บ คนที่เปิด nbtc_model_prices.csv จะเห็นเลขที่รายงาน**ไม่ได้ใช้** (เช่น MINI 3 PRO)
prices["price_thb_collected"] = base_price
prices["capped_from"] = ""
caps, cap_flags = [], []
for i, row in prices.iterrows():
    if pd.isna(row.get("tier")) or row.get("price_rule") != GEN_RULE:
        continue
    # 🚨 รุ่นที่เลิกผลิตแล้ว ไม่เข้ากติกานี้
    # ของเก่าที่เลิกทำแล้วเหลือน้อย ราคาไม่ลดตามรุ่นใหม่เป็นเรื่องปกติของตลาด
    # (AGRAS MG-1 ปี 2558 ยังขาย 267,000 ขณะที่ T20P ปี 2566 ถัง 2 เท่าขาย 220,000)
    # ราคาพวกนี้ถูกต้องในฐานะ "ราคาที่ร้านขายจริง" การกดลงคือการลบราคาจริงทิ้ง
    if str(row.get("discontinued", "")).strip().lower() in ("yes", "y", "true", "1"):
        continue
    newer_idx = prices.index[(prices["tier"] == row["tier"]) & (prices["gen"] > row["gen"])]
    if not len(newer_idx):
        continue
    # 🚨 ต้องเทียบเฉพาะรุ่นที่ฐานราคาเดียวกัน
    # ฉบับแรกไม่เช็คเลย จึงเอาราคาชุดคอมโบไปเทียบกับตัวเปล่าแล้วสรุปว่า "แพงเกิน"
    # ซึ่งจับได้ 3 ครั้งว่าต้นเหตุจริงคือฐานปนกัน ไม่ใช่ราคาผิด:
    #   MAVIC 3 PRO 93,990 = Fly More Combo (ตัวเปล่า 73,990)
    #   MINI 3 PRO  30,990 = ชุดรีโมตมีจอ DJI RC (ตัวเปล่า RC-N1 25,690)
    #   MAVIC 2 PRO 56,500 = ราคาสัญญาภาครัฐ ไม่ใช่ป้ายร้าน
    # → ถ้าฐานต่างกันให้ **ฟ้อง** ไม่ใช่กด เพราะการกดข้ามฐานคือเอาราคาชุดหนึ่งไปแทนอีกชุด
    same_basis = newer_idx[prices.loc[newer_idx, "basis_kind"] == row["basis_kind"]]
    diff_basis = newer_idx.difference(same_basis)
    if len(diff_basis):
        lower = diff_basis[base_price[diff_basis] < base_price[i]]
        for j in lower:
            cap_flags.append({
                "model": row["model_final"], "ฐาน": row["basis_kind"], "ราคา": base_price[i],
                "เทียบกับ": prices.loc[j, "model_final"],
                "ฐานอีกฝั่ง": prices.loc[j, "basis_kind"], "ราคาอีกฝั่ง": base_price[j],
            })
    if not len(same_basis):
        continue
    # เพดาน = ราคา "ต่ำสุด" ของรุ่นที่ใหม่กว่าทั้งหมดในสาย ไม่ใช่สูงสุด
    # เพราะถ้าใช้สูงสุด รุ่นเก่าจะยังแพงกว่ารุ่นถัดไปได้อยู่ = ยังผกผันอยู่ แค่น้อยลง
    ceiling = base_price[same_basis].min()
    if base_price[i] > ceiling:
        src_model = prices.loc[base_price[same_basis].idxmin(), "model_final"]
        caps.append(
            {
                "model": row["model_final"], "เดิม": base_price[i], "เพดาน": ceiling,
                "เพดานมาจาก": src_model,
            }
        )
        prices.at[i, "price_thb"] = ceiling
        prices.at[i, "price_lo_thb"] = min(row["price_lo_thb"], ceiling)
        prices.at[i, "basis_kind"] = "อนุมาน"
        prices.at[i, "capped_from"] = src_model

p("----- กติกากันราคาผกผัน -----")
p(f"  ใช้กับ: แถวที่ price_rule = '{GEN_RULE}' เท่านั้น "
  f"({(prices['price_rule'] == GEN_RULE).sum()} รุ่น) — โดรนเกษตรไม่เข้ากติกานี้")
p("  กติกา: ราคาของรุ่นหนึ่ง ต้องไม่เกินราคาของรุ่นที่ใหม่กว่าในสายเดียวกัน **และฐานราคาเดียวกัน**")
p("  ไม่ใช้กับ: รุ่นที่ติดธง discontinued (เลิกผลิตแล้ว ราคาไม่ลดตามรุ่นใหม่เป็นเรื่องปกติ)")
n_disc = (prices.get("discontinued", pd.Series(dtype=str))
          .astype(str).str.strip().str.lower().isin(["yes", "y", "true", "1"]).sum())
p(f"    รุ่นที่ติดธงนี้: {n_disc} รุ่น")
if caps:
    for c in caps:
        p(f"  {c['model']:<14} {c['เดิม']:>9,.0f} → {c['เพดาน']:>9,.0f} ฿  "
          f"(เพดานจาก {c['เพดานมาจาก']} ฐานเดียวกัน)")
else:
    p("  ไม่มีรุ่นไหนเข้าเงื่อนไข")
if cap_flags:
    p()
    p(f"  ⚠️ {len(cap_flags)} คู่ที่รุ่นเก่าแพงกว่ารุ่นใหม่ **แต่คนละฐานราคา** — ฟ้องอย่างเดียว ไม่กด:")
    for f in cap_flags:
        p(f"     {f['model']} [{f['ฐาน']}] {f['ราคา']:,.0f} ฿  แพงกว่า  "
          f"{f['เทียบกับ']} [{f['ฐานอีกฝั่ง']}] {f['ราคาอีกฝั่ง']:,.0f} ฿")
    p("     → เทียบกันตรง ๆ ไม่ได้เพราะเป็นคนละชุดขาย ต้องไปหาราคาที่ฐานตรงกันมาแทน")
    p("     ห้ามกดข้ามฐาน เพราะเท่ากับเอาราคาชุดหนึ่งไปแทนที่อีกชุด")
p()

# ------------------- 2.6) ตัวตรวจโดรนเกษตร: ถังใหญ่ขึ้น ราคาต้องไม่ลด (รายงานอย่างเดียว)
# กติกากันราคาผกผันด้านบนใช้กับโดรนถ่ายภาพ ซึ่งเรียงด้วย "เจเนอเรชัน" — ใช้กับโดรนเกษตรไม่ได้
# เพราะราคาโดรนพ่นยาผูกกับ **ขนาดถัง** ไม่ใช่ปีที่ออก
#
# 🚨 ต้องเทียบ "ในสายเดียวกัน" ด้วย ไม่ใช่แค่ฐานราคาเดียวกัน
# ฉบับแรกเทียบข้ามสาย จึงฟ้อง 12 คู่ที่ 9 คู่เป็นการเทียบ MG (2015-16) กับ T (2020+)
# ซึ่งของเก่าถังเล็กแพงกว่าของใหม่ถังใหญ่ได้จริง = ตัวตรวจฟ้องผิด ซึ่งอันตรายกว่าไม่ฟ้อง
# เพราะคนอ่านจะไปแก้ราคาที่ถูกอยู่แล้วให้ผิดตามคำฟ้อง (เคสเดียวกับ §7 ของ verify_customs_docs)
#
# 🚨 ไม่แก้อัตโนมัติ เพราะราคาต่างร้านจริง ๆ ก็มี การไปกดเองจะกลบข้อมูลจริง
# หน้าที่ของตัวตรวจนี้คือ "ส่งเสียง" ว่ามีแถวที่ฐานราคาอาจปนกันอยู่ ก่อนที่มันจะถูกรวมเข้าไปในยอด
_p = prices.copy()
_p["L"] = _p["note"].astype(str).str.extract(r"ถัง\s*([\d.]+)\s*ลิตร").astype(float)
agri_rows = _p[_p["L"].notna() & _p["basis_kind"].str.startswith("ป้ายร้าน", na=False)]

p("----- ตัวตรวจ: โดรนเกษตรถังใหญ่ขึ้น ราคาต้องไม่ลด (ในฐานราคาและสายเดียวกัน) -----")

# ⚠️ รุ่นที่มีถังแต่ไม่มีแถวใน nbtc_model_tiers.csv จะหลุดการตรวจแบบเงียบ ๆ ต้องฟ้องก่อน
no_tier = agri_rows[agri_rows["tier"].isna()]
if len(no_tier):
    p(f"  🚨 {len(no_tier)} รุ่นมีความจุถังแต่ไม่มีสายกำกับใน nbtc_model_tiers.csv "
      f"— ตรวจไม่ได้และไม่เข้า fit: {', '.join(no_tier['model_final'])}")

size_flags = []
group_sizes = []
for (basis, tier), g in agri_rows.dropna(subset=["tier"]).groupby(["basis_kind", "tier"]):
    group_sizes.append((basis, tier, len(g)))
    g = g.sort_values("L")
    for i in range(len(g)):
        for j in range(i + 1, len(g)):
            a, b = g.iloc[i], g.iloc[j]
            if b["L"] > a["L"] and b["price_thb"] < a["price_thb"]:
                size_flags.append(
                    {"basis": basis, "tier": tier,
                     "small": a["model_final"], "sL": a["L"], "sp": a["price_thb"],
                     "big": b["model_final"], "bL": b["L"], "bp": b["price_thb"]}
                )
p(f"  รุ่นที่มีความจุถังกำกับไว้: {len(agri_rows)} รุ่น")
# ⚠️ ต้องพิมพ์ขนาดของแต่ละกลุ่ม เพราะกลุ่มที่มีรุ่นเดียวจับคู่กับใครไม่ได้ = ไม่ได้ถูกตรวจเลย
# ถ้าพิมพ์แต่ผลว่า "ไม่พบคู่ที่ผิดทิศ" คนอ่านจะเข้าใจว่าตรวจผ่าน ทั้งที่บางกลุ่มไม่ได้ตรวจ
p("  กลุ่มที่เทียบกัน (ฐานราคา × สาย) — กลุ่มที่มีรุ่นเดียวจับคู่ไม่ได้ จึงไม่ได้ถูกตรวจ:")
for basis, tier, n in sorted(group_sizes, key=lambda x: -x[2]):
    mark = "" if n >= 2 else "   ⚠️ รุ่นเดียว ไม่ได้ตรวจ"
    p(f"     {basis} · {tier}: {n} รุ่น{mark}")
if size_flags:
    p(f"  🚨 พบ {len(size_flags)} คู่ที่ถังใหญ่กว่าแต่ราคาถูกกว่า:")
    for f in size_flags:
        p(f"     [{f['basis']} · {f['tier']}] {f['big']} ถัง {f['bL']:.0f} ล. = {f['bp']:,.0f} ฿  "
          f"ถูกกว่า  {f['small']} ถัง {f['sL']:.0f} ล. = {f['sp']:,.0f} ฿")
    p("  → อาจเป็นฐานราคาที่ยังปนกันอยู่ หรือราคาต่างร้านจริง ๆ — ต้องเปิดหน้าต้นทางดูก่อนสรุป")
else:
    p("  ✅ ไม่พบคู่ที่ผิดทิศ")
p()

# ------------------------------------------------------------- 3) ต่อราคาเข้าไป
df = long.merge(prices, on=["brand", "model_final"], how="left").merge(
    cls[["brand", "model_final", "class", "agri_share"]], on=["brand", "model_final"], how="left"
)
df["class"] = df["class"].fillna("ทั่วไป")
df["has_price"] = df["price_thb"].notna()
# ธง "จดเป็นฝูง" มาจากขั้นที่ 1 — เป็นระดับยี่ห้อ ไม่ใช่ระดับรุ่น
# ⚠️ ขั้นที่ 3 รันได้โดยไม่ต้องรันขั้นที่ 1 ใหม่ (ผลของขั้น 1 อยู่ใน git แล้ว)
# ถ้า model_catalog.csv เป็นไฟล์เก่าที่ยังไม่มีคอลัมน์นี้ กลุ่มฝูงจะหายไปเงียบ ๆ
# แล้วลำพวกนั้นจะกลับไปถูกตีราคาด้วยช่วงราคาโดรนผู้บริโภคโดยไม่มีอะไรเตือน → ต้องพิมพ์บอกเสมอ
if "is_fleet_brand" in cat.columns:
    FLEET_BRANDS = set(cat.loc[cat["is_fleet_brand"].astype(bool), "brand"].unique())
else:
    FLEET_BRANDS = set()
df["is_fleet_brand"] = df["brand"].isin(FLEET_BRANDS)
_nf = int(df.loc[df["is_fleet_brand"], "units"].sum())
if FLEET_BRANDS:
    p(f"ยี่ห้อที่จดเป็นฝูง (จากขั้นที่ 1): {len(FLEET_BRANDS)} ยี่ห้อ {_nf:,} ลำ "
      f"— {', '.join(sorted(FLEET_BRANDS))}")
else:
    p("🚨 ไม่พบคอลัมน์ is_fleet_brand ใน model_catalog.csv — กลุ่ม 'จดเป็นฝูง' จะไม่ถูกแยกออก")
    p("   ให้รัน 01_build_model_catalog.py ใหม่ก่อน ไม่งั้นลำกลุ่มนั้นจะถูกตีราคา")
    p("   ด้วยช่วงราคาโดรนผู้บริโภคซึ่งสูงเกินจริง")
p()

priced_units = int(df.loc[df.has_price, "units"].sum())
p(f"ลำที่ตั้งราคาได้       : {priced_units:,} ({priced_units / N_TOTAL:.1%})")
p(f"ลำที่ยังตีราคาไม่ได้    : {N_TOTAL - priced_units:,} ({1 - priced_units / N_TOTAL:.1%})")
p()

p("----- ที่มาของราคาที่ใช้ (ถ่วงน้ำหนักด้วยจำนวนลำ) -----")
for kind, n in df[df.has_price].groupby("basis_kind")["units"].sum().sort_values(ascending=False).items():
    p(f"  {kind:<26} {int(n):>8,} ลำ  ({n / priced_units:6.1%})")
p()

# --------------------------------------------------- 4) มูลค่าของส่วนที่ตั้งราคาได้
for col in ("price_thb", "price_lo_thb", "price_hi_thb"):
    df[col.replace("price", "val").replace("_thb", "")] = df["units"] * df[col]

years = sorted(int(y) for y in df["year"].dropna().unique())
PARTIAL = {2017: "ต.ค.-ธ.ค.", 2026: "ม.ค.-มิ.ย."}

by_year = (
    df[df.has_price]
    .groupby("year")[["units", "val", "val_lo", "val_hi"]]
    .sum()
    .reset_index()
)
units_all = df.groupby("year")["units"].sum().rename("units_all")
by_year = by_year.merge(units_all, on="year")
by_year["coverage"] = by_year["units"] / by_year["units_all"]

p("=" * 80)
p("ก) มูลค่าตามราคาขายปลีกในไทย (รวม VAT) — เฉพาะลำที่ตั้งราคาได้")
p("=" * 80)
# 🚨 coverage ไม่เท่ากันทุกปี (73%-85%) → คอลัมน์ 'วัดได้' ดิบ ๆ เอาไปอ่านเป็นเส้นแนวโน้มไม่ได้
# เป็นข้อบกพร่องแบบเดียวกับที่ SOURCES.md §8 เตือนไว้เรื่องตัวเลขศุลกากร แค่คนละแกน
# จึงต้องพิมพ์คู่กันเสมอ: ค่าดิบ (ขอบล่างแน่นอน) กับ ค่าหารด้วย coverage (ถ้าที่เหลือราคาเฉลี่ยเท่ากัน)
by_year["val_scaled"] = by_year["val"] / by_year["coverage"]

p(f"{'ปี':<6}{'ลำทั้งหมด':>11}{'ตั้งราคาได้':>12}{'%':>7}   "
  f"{'วัดได้(ลบ.)':>13}{'÷coverage':>12}{'ขอบบน':>11}")
for _, r in by_year.iterrows():
    y = int(r["year"])
    tag = f"  ⚠️ {PARTIAL[y]}" if y in PARTIAL else ""
    p(f"{y:<6}{int(r['units_all']):>11,}{int(r['units']):>12,}{r['coverage']:>7.0%}   "
      f"{bt(r['val']):>13}{bt(r['val_scaled']):>12}{bt(r['val_hi']):>11}{tag}")
tot = by_year[["val", "val_lo", "val_hi", "val_scaled"]].sum()
p(f"{'สะสม':<6}{N_TOTAL:>11,}{priced_units:>12,}{priced_units / N_TOTAL:>7.0%}   "
  f"{bt(tot['val']):>13}{bt(tot['val_scaled']):>12}{bt(tot['val_hi']):>11}")
p()
p("🚨 แถว 'สะสม' คือ **มูลค่าของฝูงบินที่จดทะเบียนไว้ทั้งหมดตั้งแต่ปี 2560** ไม่ใช่ขนาดตลาด")
p("   ขนาดตลาดคือตัวเลข **รายปี** — ปี 2025 (พ.ศ. 2568) = ตัวเลขในแถวนั้น")
p()
p("🚨 อ่านเส้นแนวโน้มอย่างไรให้ไม่ผิด — coverage ไม่เท่ากันทุกปี (73%–85%)")
p("   คอลัมน์ 'วัดได้' คิดจากลำที่ตั้งราคาได้เท่านั้น ปีที่ coverage ต่ำจึงถูกกดลงโดยอัตโนมัติ")
p("   คอลัมน์ '÷coverage' คือถ้าสมมติว่าลำที่เหลือราคาเฉลี่ยเท่ากับลำที่ตั้งราคาได้")
_a, _b = by_year[by_year.year == 2024], by_year[by_year.year == 2025]
if len(_a) and len(_b):
    g_raw = _b["val"].iloc[0] / _a["val"].iloc[0] - 1
    g_scaled = _b["val_scaled"].iloc[0] / _a["val_scaled"].iloc[0] - 1
    p(f"   ตัวอย่างที่ต่างกันจริง — โต 2567→2568: อ่านจากค่าดิบ {g_raw:+.0%} · "
      f"อ่านจากค่าหาร coverage {g_scaled:+.0%}")
    p("   → **การเติบโตอยู่ระหว่างสองค่านี้ ห้ามหยิบค่าเดียวไปอ้าง**")
p("   (ยังดีกว่าศุลกากรที่รูแกว่ง 0%–70% แต่ไม่ได้แปลว่ารูหายไปแล้ว)")
p()
p("⚠️ ปี 2017 กับ 2026 ข้อมูลไม่ครบปี — ห้ามวางเทียบกับปีเต็ม")
p("⚠️ 'ขอบบน' คือผลของการใช้ราคาชุดคอมโบ/ราคาร้านที่แพงที่สุด ไม่ใช่ช่วงความเชื่อมั่นทางสถิติ")
p()

# ------------------------------------------- 5) ความไวต่อราคาที่ไม่ใช่ราคาป้ายร้าน
soft = df.has_price & df["basis_kind"].isin(["สัญญาภาครัฐ", "อนุมาน"])
p("----- ความไว: ถ้าตัดแถวที่ราคาไม่ได้มาจากป้ายร้านออก -----")
p(f"  แถวที่ราคามาจากสัญญาภาครัฐ/การอนุมาน: {int(df.loc[soft, 'units'].sum()):,} ลำ "
  f"({df.loc[soft, 'units'].sum() / priced_units:.1%} ของลำที่ตั้งราคาได้)")
p(f"  มูลค่าส่วนนั้น: {bt(df.loc[soft, 'val'].sum())} ลบ. "
  f"({df.loc[soft, 'val'].sum() / tot['val']:.1%} ของมูลค่ารวม)")
p(f"  → เหลือเฉพาะราคาป้ายร้าน: {bt(df.loc[df.has_price & ~soft, 'val'].sum())} ลบ.")
p()

# --------------------------------------------- 6) ส่วนที่ยังตีราคาไม่ได้ แยกตามชั้น
p("=" * 80)
p("ข) ส่วนที่ยังตีราคาไม่ได้ — รายงานเป็นช่วง แยกตามชั้น ไม่ยัดเข้าตัวเลขหลัก")
p("=" * 80)
p("ช่วงราคาของแต่ละกลุ่มมาจากราคารุ่นที่ตั้งราคาได้ในกลุ่มเดียวกันเท่านั้น")
p("  ถ้ามีตั้งแต่ 5 รุ่นขึ้นไป → ใช้เปอร์เซ็นไทล์ 10/90 ถ่วงน้ำหนักด้วยจำนวนลำ")
p("  ถ้าน้อยกว่านั้น → ใช้ขอบล่างสุด-ขอบบนสุดที่หาได้จริง และติดป้ายว่าฐานบาง")
p()
p("🚨 ชั้นเกษตรต้องแยก DJI ออกจากแบรนด์อื่น — รอบก่อนเอาราคา DJI ไปครอบทั้งหมด ซึ่งสูงเกินจริง")
p("   หลักฐาน: KASET GEN-Y GCS-9 ถัง 5 ลิตร ขาย 75,000 บาท")
p("   ส่วน DJI AGRAS T10 ถัง 8 ลิตร ขาย 153,000 บาท — ขนาดใกล้กันแต่ราคาต่างเท่าตัว")
p()

# 🚨 ชั้นเกษตรต้องแยก DJI ออกจากแบรนด์อื่น ไม่งั้นเอาราคา DJI ไปครอบทั้งหมด
# หลักฐานว่าต่างกันจริง: KASET GEN-Y GCS-9 (ถัง 5 ลิตร) ขาย 75,000 บาท
# ส่วน DJI AGRAS T10 (ถัง 8 ลิตร) ขาย 153,000 บาท — ต่างกันเท่าตัวที่ขนาดใกล้กัน
# 🚨 กลุ่ม "จดเป็นฝูง" ต้องแยกออกมาเป็น **ประมาณไม่ได้** ไม่ใช่เดาให้ต่ำลง
# ราคาต่อลำในตารางนี้เป็นราคาขายปลีก ซึ่งใช้กับของที่คนซื้อทีละเครื่อง
# แต่ฝูงพวกนี้ถูกจดทีละหลายร้อยลำในวันเดียว รุ่นเดียว จังหวัดเดียว = ขายกันเป็นระบบ
# เอาช่วงราคาโดรนผู้บริโภคไปครอบจะสูงเกินจริง แต่การไปเดาตัวเลขต่ำกว่าแทนก็ไม่มีหลักฐานรองรับ
# → รายงานว่าประมาณไม่ได้ ตามหลักเดียวกับที่ศุลกากรเขียนว่า "วัดไม่ได้" ใน SOURCES.md §8
FLEET_GROUP = "จดเป็นฝูง (ประมาณไม่ได้)"
df["group"] = np.where(
    df["is_fleet_brand"], FLEET_GROUP,
    np.where(df["class"] == "ทั่วไป", "ทั่วไป",
             np.where(df["brand"] == "DJI", "เกษตร-DJI", "เกษตร-ไม่ใช่ DJI")),
)

bands, unpriced_rows = {}, []
for c in ("ทั่วไป", "เกษตร-DJI", "เกษตร-ไม่ใช่ DJI"):
    ref = df[(df["group"] == c) & df.has_price]
    un = df[(df["group"] == c) & ~df.has_price]
    n = int(un["units"].sum())
    if not len(ref) or n == 0:
        continue
    n_models = ref[["brand", "model_final"]].drop_duplicates().shape[0]
    if n_models >= 5:
        # รุ่นมากพอให้เปอร์เซ็นไทล์มีความหมาย — ถ่วงน้ำหนักด้วยจำนวนลำ
        w = np.repeat(ref["price_thb"].values, ref["units"].astype(int).values)
        lo, hi = np.percentile(w, 10), np.percentile(w, 90)
        how = f"เปอร์เซ็นไทล์ 10/90 จาก {n_models} รุ่น"
    else:
        # รุ่นน้อยเกินกว่าจะทำเปอร์เซ็นไทล์ให้มีความหมาย → ใช้ขอบล่างสุด-ขอบบนสุดที่หาได้จริง
        lo, hi = ref["price_lo_thb"].min(), ref["price_hi_thb"].max()
        how = f"ขอบล่างสุด-ขอบบนสุดจาก {n_models} รุ่นเท่านั้น ⚠️ ฐานบาง"
    bands[c] = (lo, hi)
    unpriced_rows.append({"class": c, "units": n, "lo": lo, "hi": hi,
                          "val_lo": n * lo, "val_hi": n * hi})
    p(f"  {c:<18} ตั้งราคาได้ {int(ref['units'].sum()):>7,} ลำ  "
      f"ช่วง {lo:>9,.0f} – {hi:>9,.0f} ฿/ลำ   ({how})")
p()
# --------------------------- ชั้น 3: เส้นราคาต่อความจุถัง สำหรับรุ่นที่ชื่อบอกลิตร
# โดรนพ่นยาราคาผูกกับความจุถังเป็นหลัก และชื่อรุ่นของแบรนด์ไทยหลายเจ้าบอกความจุตรง ๆ
# (BA10L = 10 ลิตร · PANYA V.2-12L = 12 ลิตร) จึงประมาณได้ละเอียดกว่าการใช้ช่วงกลุ่มก้อนเดียว
#
# 🚨 กติกาที่ต้องยึด: fit เฉพาะราคาที่มาจาก **ป้ายร้านจริง** เท่านั้น
# ถ้าเอาราคาที่เราอนุมานเอง (T16/T20/T25P/T70P) ไป fit ด้วย = fit กับการเดาของตัวเอง
LIT_RE = re.compile(r"ถัง\s*([\d.]+)\s*ลิตร")
NAME_LIT_RE = re.compile(r"(\d{1,3}(?:\.\d)?)\s*(?:L\b|ลิตร)")

# 🚨 ต้อง fit บนฐานราคาเดียวเท่านั้น — ตรวจแล้วพบว่าสองฐานให้ผลคนละเรื่อง
#   ชุดพร้อมบิน (โดรน+แบต+แท่นชาร์จ) : ราคาขึ้นกับความจุจริง
#   ตัวเครื่องเปล่า (โดรน+รีโมต)      : แทบไม่ขึ้นกับความจุเลย (เคยวัดได้ R² = 0.005 จาก 5 รุ่น)
# → ใช้ฐาน "ชุดพร้อมบิน" เพราะเป็นเงินที่เกษตรกรจ่ายจริง และจุดอ้างอิงแบรนด์ไทยก็อยู่ฐานเดียวกัน
# ⚠️ R² ของทั้งสองฐานให้สคริปต์พิมพ์เอง อย่าเขียนตัวเลขตายไว้ในคอมเมนต์
#    เลขเก่า (0.92 / 0.005) เคยค้างอยู่ตรงนี้หลังตารางราคาเปลี่ยน จนไม่ตรงกับผลรันจริง
FIT_BASIS = "ป้ายร้าน-ชุดพร้อมบิน"
allp = prices.copy()
allp["L"] = allp["note"].astype(str).str.extract(LIT_RE).astype(float)
fit_pool = allp[allp["L"].notna() & (allp["basis_kind"] == FIT_BASIS) & (allp["brand"] == "DJI")]

# 🚨 ต้อง fit ภายใน "สายเดียวกัน" ด้วย ไม่ใช่แค่ฐานราคาเดียวกัน
# ราคาผูกกับความจุถังก็จริง แต่ผูกกันเฉพาะในสายเดียวกันเท่านั้น
# ตอนที่เอา MG (2015-16) มา fit รวมกับ T (2020+) ได้ R² = 0.492 · แยกสายแล้วได้ 0.816
# ที่เคยได้ 0.915 ไม่ได้แปลว่าเส้นดี แต่แปลว่าตอนนั้นบังเอิญยังไม่มีรุ่นสายเก่าอยู่ในกลุ่ม
# → เลือกสายที่ใหม่ที่สุด (gen สูงสุด) เพราะเป็นสายที่ยังขายอยู่ = ราคาที่ใช้ทำนายของปัจจุบันได้
FIT_TIER = None
_cap = fit_pool[fit_pool["price_rule"] == "ความจุ"].dropna(subset=["tier"])
if len(_cap):
    FIT_TIER = _cap.loc[_cap["gen"].idxmax(), "tier"]
    fitsrc = _cap[_cap["tier"] == FIT_TIER]
    dropped = _cap[_cap["tier"] != FIT_TIER]
else:
    fitsrc, dropped = fit_pool, fit_pool.iloc[0:0]

bare = allp[
    allp["L"].notna()
    & allp["basis_kind"].isin(["ป้ายร้าน-ตัวเปล่า", "ป้ายร้าน-ตัวเครื่อง"])
    & (allp["brand"] == "DJI")
]

p("=" * 80)
p("ชั้น 3 — ประมาณราคาจากความจุถัง (เฉพาะรุ่นที่ชื่อบอกลิตรตรง ๆ)")
p("=" * 80)

curve_rows, curve_note = [], ""
if len(fitsrc) >= 6:
    slope, intercept = np.polyfit(np.log(fitsrc["L"]), np.log(fitsrc["price_thb"]), 1)
    resid = np.log(fitsrc["price_thb"]) - (intercept + slope * np.log(fitsrc["L"]))
    r2 = 1 - (resid**2).sum() / ((np.log(fitsrc["price_thb"]) - np.log(fitsrc["price_thb"]).mean()) ** 2).sum()
    L_MIN, L_MAX = float(fitsrc["L"].min()), float(fitsrc["L"].max())

    def curve(L):
        return float(np.exp(intercept) * L**slope)

    p(f"ฐานราคาที่ใช้ fit: {FIT_BASIS} (โดรน+แบตเตอรี่+แท่นชาร์จ) — เงินที่เกษตรกรจ่ายจริง")
    p(f"สายที่ใช้ fit: {FIT_TIER} (สายที่ใหม่ที่สุดในกลุ่มที่ราคาผูกกับความจุ)")
    p(f"เส้นที่ fit ได้จากราคาป้ายจริงของ DJI {len(fitsrc)} รุ่น ({L_MIN:.0f}–{L_MAX:.0f} ลิตร):")
    p(f"  ราคา = {np.exp(intercept):,.0f} × ลิตร^{slope:.3f}    R² = {r2:.3f}")
    p(f"  ความชัน {slope:.3f} < 1 แปลว่าถังใหญ่ขึ้นราคาไม่ได้ขึ้นตาม — บาท/ลิตร ลดลงเรื่อย ๆ")

    # 🔍 แสดงผลของการแยกสายให้เห็นเป็นตัวเลข ไม่ใช่แค่เขียนว่าแยกแล้ว
    # ถ้าไม่พิมพ์เทียบไว้ วันหลังจะไม่มีใครรู้ว่าการแยกสายช่วยหรือไม่ช่วย
    if len(dropped):
        _all = pd.concat([fitsrc, dropped])
        _s, _i = np.polyfit(np.log(_all["L"]), np.log(_all["price_thb"]), 1)
        _res = np.log(_all["price_thb"]) - (_i + _s * np.log(_all["L"]))
        _r2 = 1 - (_res**2).sum() / ((np.log(_all["price_thb"]) - np.log(_all["price_thb"]).mean()) ** 2).sum()
        p(f"  ตัดออกจาก fit {len(dropped)} รุ่น (สาย {', '.join(sorted(dropped['tier'].unique()))}): "
          f"{', '.join(dropped['model_final'])}")
        p(f"  ถ้าเอามา fit รวมกันทุกสาย ({len(_all)} รุ่น): ความชัน {_s:.3f} · R² = {_r2:.3f} "
          f"→ แย่กว่า {r2 - _r2:+.3f}")
        p("  🚨 รุ่นที่ตัดออก **ยังอยู่ในตารางราคาและยังถูกนับเข้ามูลค่าตามปกติ** "
          "ตัดเฉพาะจากการเป็นวัตถุดิบของเส้นทำนายเท่านั้น")
    p(f"  ค่าคลาดเคลื่อนสูงสุดของจุดที่ใช้ fit: {np.abs(np.exp(resid) - 1).max():.1%}")
    p()

    # 🔍 ทำไมถึงต้องยึดฐานเดียว — ราคาตัวเครื่องเปล่าแทบไม่ขึ้นกับความจุ
    if len(bare) >= 3:
        bs, ba_ = np.polyfit(np.log(bare["L"]), np.log(bare["price_thb"]), 1)
        bres = np.log(bare["price_thb"]) - (ba_ + bs * np.log(bare["L"]))
        br2 = 1 - (bres**2).sum() / ((np.log(bare["price_thb"]) - np.log(bare["price_thb"]).mean()) ** 2).sum()
        p(f"เทียบกับถ้า fit บนราคา 'ตัวเครื่องเปล่า' ({len(bare)} รุ่น): "
          f"ความชัน {bs:.3f} · R² = {br2:.3f}")
        p("  → ราคาตัวเครื่องแทบไม่ขึ้นกับความจุถังเลย (ถัง 10 ลิตร 190,000 · 70 ลิตร 194,500)")
        p("  → สิ่งที่แพงขึ้นตามขนาดคือ **แบตเตอรี่กับแท่นชาร์จ** ไม่ใช่ตัวเครื่อง")
        p("  → จึงห้ามเอาสองฐานมา fit รวมกัน และห้ามใช้เส้นนี้กับราคาที่เป็นตัวเครื่องเปล่า")
        p()
    else:
        # ⚠️ ต้องพิมพ์บอกเมื่อเทียบไม่ได้ ไม่ใช่เงียบหายไปเฉย ๆ
        # การเทียบสองฐานเคยทำได้ตอนมี 5 รุ่นในฐาน 'ตัวเครื่อง' พอย้ายไปฐาน 'ชุดพร้อมบิน'
        # เหลือรุ่นเดียว บล็อกนี้ก็หายจากผลรันโดยไม่มีอะไรบอก — ซึ่งอ่านเหมือนไม่เคยมี
        p(f"⚠️ เทียบกับฐาน 'ตัวเครื่องเปล่า' ไม่ได้รอบนี้ — มีแค่ {len(bare)} รุ่นในฐานนั้น (ต้องมี 3 ขึ้นไป)")
        p("  เคยวัดได้ตอนฐานนั้นยังมีหลายรุ่น และเป็นที่มาของกติกา 'ยึดฐานเดียว'")
        p("  ตัวเลขอยู่ในรายงาน reports/2026-08-04_nbtc-unit-value/README.md — ไม่พิมพ์ซ้ำที่นี่")
        p("  เพราะเลขที่สคริปต์พิมพ์ออกมาต้องมาจากการคำนวณของรอบนั้นเสมอ ไม่ใช่ค่าที่พิมพ์ค้างไว้")
        p()

    # อัตราส่วนราคาแบรนด์ที่ไม่ใช่ DJI ต่อเส้น — ต้องเป็นฐานเดียวกับที่ fit เท่านั้น
    thsrc = allp[allp["L"].notna() & (allp["basis_kind"] == FIT_BASIS) & (allp["brand"] != "DJI")]
    ratios = [(r["brand"], r["model_final"], r["L"], r["price_thb"], r["price_thb"] / curve(r["L"]))
              for _, r in thsrc.iterrows()]
    RATIO_LO = min(x[4] for x in ratios) if ratios else 1.0
    p("อัตราส่วน ราคาแบรนด์ที่ไม่ใช่ DJI ÷ เส้นของ DJI ที่ความจุเดียวกัน:")
    for b, m, L, pz, rt in ratios:
        p(f"  {b} {m} ถัง {L:.0f} ลิตร ขาย {pz:,.0f} ฿ · เส้น DJI ทำนาย {curve(L):,.0f} ฿ → {rt:.2f}")
    p(f"🚨 มีจุดเทียบได้แค่ {len(ratios)} รุ่น — ใช้เป็น 'ขอบล่าง' ของอัตราส่วนเท่านั้น ไม่ใช่ค่ากลาง")
    p()
    p(f"กติกาที่ใช้ประมาณ: ขอบล่าง = เส้น × {RATIO_LO:.2f} · ขอบบน = เส้น × 1.00")
    p("  ขอบบนตั้งที่ราคาเทียบเท่า DJI เพราะ DJI เป็นแบรนด์พรีเมียมที่ผลิตจำนวนมาก")
    p("  แบรนด์เล็กจึงไม่น่าขายแพงกว่าที่ความจุเท่ากัน — เป็นข้อสมมติ ไม่ใช่สิ่งที่วัดได้")
    p()

    un_agri = df[(df["group"] == "เกษตร-ไม่ใช่ DJI") & ~df.has_price].copy()
    un_agri["L"] = un_agri["model_final"].astype(str).str.extract(NAME_LIT_RE).astype(float)
    un_agri.loc[(un_agri["L"] < 1) | (un_agri["L"] > 200), "L"] = np.nan
    withL = un_agri[un_agri["L"].notna()]

    per_model = withL.groupby(["brand", "model_final", "L"], as_index=False)["units"].sum()
    per_model["lo"] = per_model["L"].map(lambda L: curve(L) * RATIO_LO)
    per_model["hi"] = per_model["L"].map(curve)
    per_model["นอกช่วง fit"] = ~per_model["L"].between(L_MIN, L_MAX)
    per_model["val_lo"] = per_model["units"] * per_model["lo"]
    per_model["val_hi"] = per_model["units"] * per_model["hi"]
    per_model = per_model.sort_values("units", ascending=False)

    n_curve = int(per_model["units"].sum())
    p(f"รุ่นที่ประมาณด้วยเส้นนี้ได้: {n_curve:,} ลำ / {len(per_model)} รุ่น")
    p(f"{'ลำ':>7}  {'ยี่ห้อ':<14}{'รุ่น':<18}{'ลิตร':>5}{'ขอบล่าง':>11}{'ขอบบน':>11}")
    for _, r in per_model.iterrows():
        warn = "  ⚠️ นอกช่วงที่ fit" if r["นอกช่วง fit"] else ""
        p(f"{int(r['units']):>7,}  {r['brand']:<14}{r['model_final']:<18}{r['L']:>5.0f}"
          f"{r['lo']:>11,.0f}{r['hi']:>11,.0f}{warn}")
    n_out = int(per_model.loc[per_model["นอกช่วง fit"], "units"].sum())
    if n_out:
        p(f"⚠️ {n_out:,} ลำ ความจุอยู่นอกช่วง {L_MIN:.0f}–{L_MAX:.0f} ลิตร ที่ใช้ fit — เป็นการทาบเส้นออกนอกข้อมูล")
    p()
    p(f"รวมมูลค่าที่ประมาณได้จากเส้น: {bt(per_model['val_lo'].sum())} – {bt(per_model['val_hi'].sum())} ลบ.")
    flat_lo, flat_hi = bands.get("เกษตร-ไม่ใช่ DJI", (np.nan, np.nan))
    if flat_lo == flat_lo:
        p(f"เทียบกับถ้าใช้ช่วงกลุ่มก้อนเดียว ({flat_lo:,.0f}–{flat_hi:,.0f} ฿/ลำ): "
          f"{bt(n_curve * flat_lo)} – {bt(n_curve * flat_hi)} ลบ.")
        p("→ เส้นความจุทำให้ช่วงแคบลง เพราะแยกได้ว่าลำไหนถังเล็กลำไหนถังใหญ่")
    p()

    # ---- ตัวตรวจอิสระ: ช่วงราคาของ BUG AWAY ที่สื่อต่างประเทศเคยรายงานไว้ ----
    # CNN สัมภาษณ์ผู้บริหาร Bug Away เมื่อ ก.ค. 2019 ระบุช่วงราคาสินค้าทั้งสายที่ 2,400-9,000 USD
    # เป็นแหล่งอิสระที่ไม่เกี่ยวกับเส้นที่ fit เลย จึงใช้ตรวจได้
    FX2019 = 31.0  # บาท/ดอลลาร์ โดยประมาณในปี 2019
    ba_lo, ba_hi = 2400 * FX2019, 9000 * FX2019
    ba = per_model[per_model["brand"] == "BUG AWAY"]
    if len(ba):
        p("----- ตัวตรวจอิสระ: เทียบกับช่วงราคาที่ CNN เคยรายงานของ BUG AWAY -----")
        p(f"  CNN (ก.ค. 2019) ระบุสินค้าทั้งสายอยู่ที่ 2,400–9,000 USD "
          f"≈ {ba_lo:,.0f}–{ba_hi:,.0f} บาท (ที่ ~{FX2019:.0f} บาท/ดอลลาร์)")
        for _, r in ba.sort_values("L").iterrows():
            inside = ba_lo <= r["lo"] and r["hi"] <= ba_hi
            p(f"  {r['model_final']:<8} ถัง {r['L']:.0f} ลิตร → เส้นให้ {r['lo']:,.0f}–{r['hi']:,.0f} บาท  "
              f"{'✅ อยู่ในช่วงที่ CNN รายงาน' if inside else '⚠️ หลุดช่วง'}")
        p("  https://www.cnn.com/2019/07/03/asia/bug-away-thailand-drones-intl/index.html")
        p("  ⚠️ เป็นราคาปี 2019 และเป็นช่วงของทั้งสายผลิตภัณฑ์ ไม่ใช่ราคารายรุ่น — ใช้ดูว่าอยู่คนละโลกไหมเท่านั้น")
        p()

    curve_rows = [{
        "class": "เกษตร-ไม่ใช่ DJI (ชื่อบอกลิตร)", "units": n_curve,
        "lo": per_model["lo"].min(), "hi": per_model["hi"].max(),
        "val_lo": per_model["val_lo"].sum(), "val_hi": per_model["val_hi"].sum(),
    }]
    # ถอดลำที่ประมาณด้วยเส้นแล้ว ออกจากช่วงกลุ่มก้อนใหญ่ ไม่งั้นนับซ้ำ
    for row in unpriced_rows:
        if row["class"] == "เกษตร-ไม่ใช่ DJI":
            row["units"] -= n_curve
            row["val_lo"] = row["units"] * row["lo"]
            row["val_hi"] = row["units"] * row["hi"]
            row["class"] = "เกษตร-ไม่ใช่ DJI (ไม่มีเบาะแส)"
    save(per_model, OUTDIR / "capacity_curve_estimates.csv")
    curve_note = f"เส้น = {np.exp(intercept):,.0f} × ลิตร^{slope:.3f} (R²={r2:.2f}, n={len(fitsrc)})"
else:
    p("ข้อมูลไม่พอ fit เส้น (ต้องมีราคาป้ายจริงพร้อมความจุอย่างน้อย 6 รุ่น)")
p()

up = pd.DataFrame(unpriced_rows + curve_rows)
n_fleet = int(df[(df["group"] == FLEET_GROUP) & ~df.has_price]["units"].sum())
p(f"{'ชั้น':<10}{'ลำที่ยังไม่มีราคา':>18}{'มูลค่าขั้นต่ำ(ลบ.)':>20}{'มูลค่าขั้นสูง(ลบ.)':>20}")
for _, r in up.iterrows():
    p(f"{r['class']:<10}{int(r['units']):>18,}{bt(r['val_lo']):>20}{bt(r['val_hi']):>20}")
if n_fleet:
    p(f"{FLEET_GROUP:<10}{n_fleet:>18,}{'—':>20}{'—':>20}")
p(f"{'รวม':<10}{int(up['units'].sum()) + n_fleet:>18,}"
  f"{bt(up['val_lo'].sum()):>20}{bt(up['val_hi'].sum()):>20}")
p()
p("🚨 ตัวเลขสองคอลัมน์นี้เป็น **การประมาณ ไม่ใช่การวัด** — ห้ามเอาไปรวมกับตัวเลขหลัก")
p("   แล้วรายงานเป็นเลขตัวเดียว ต้องเขียนแยกเสมอว่าวัดได้เท่าไร เดาไว้เท่าไร")
if n_fleet:
    p()
    p(f"🚨 แถว '{FLEET_GROUP}' ไม่มีตัวเลขประมาณโดยตั้งใจ — {n_fleet:,} ลำนี้เป็นยี่ห้อที่ถูกจด")
    p(f"   ทีละหลายร้อยลำในวันเดียว รุ่นเดียว จังหวัดเดียว (ดูผลรันขั้นที่ 1 หัวข้อ 2.9)")
    p("   ราคาต่อลำในตารางเป็นราคาขายปลีก ซึ่งใช้กับของแบบนี้ไม่ได้ และการเดาตัวเลขต่ำกว่า")
    p("   มาแทนก็ไม่มีหลักฐานรองรับ → รายงานว่าประมาณไม่ได้ ดีกว่าใส่ตัวเลขที่รู้อยู่แล้วว่าผิด")
    p("   ⚠️ ผลข้างเคียง: ช่วงประมาณรวมแคบลงเพราะ**แยกกลุ่มได้ดีขึ้น** ไม่ใช่เพราะรู้ราคามากขึ้น")
p()

# --------------------------------------------------- 7) ใครกินมูลค่า — แยกตามชั้น
p("----- มูลค่าแยกตามชั้น (เฉพาะส่วนที่ตั้งราคาได้) -----")
seg = df[df.has_price].groupby("class")[["units", "val"]].sum()
for c, r in seg.iterrows():
    p(f"  {c:<8} {int(r['units']):>8,} ลำ ({r['units'] / priced_units:5.1%})   "
      f"{bt(r['val']):>10} ลบ. ({r['val'] / tot['val']:5.1%})")
p()
p("  15 รุ่นที่กินมูลค่าสูงสุด:")
top = df[df.has_price].groupby(["brand", "model_final"])[["units", "val"]].sum()
top = top.sort_values("val", ascending=False).head(15)
for (b, m), r in top.iterrows():
    p(f"    {bt(r['val']):>9} ลบ.  {int(r['units']):>7,} ลำ  {b} | {m}")
p()

# ------------------------------- 8) ฐานเทียบนำเข้า + ตรวจว่าตกอยู่ในกรอบศุลกากรไหม
p("=" * 80)
p("ค) แปลงเป็นฐานเทียบนำเข้า แล้วเช็กกับกรอบของศุลกากร")
p("=" * 80)
p(f"สูตร: ราคาป้าย ÷ (1+VAT {VAT:.0%}) ÷ (1+กำไรตัวแทน)   "
  f"โดยกำไรตัวแทนใช้ช่วง {MARGIN_LO:.0%}–{MARGIN_HI:.0%}")
p()


def to_import_basis(v, margin):
    return v / (1 + VAT) / (1 + margin)


cust = pd.read_csv(PROC / "customs_hs8806_by_code.csv")
CY2BE = {2025: 2568, 2024: 2567, 2023: 2566, 2022: 2565, 2026: 2569}
# อ่านปีแรกจากไฟล์จริง ไม่พิมพ์ค่าลงไปเอง — ถ้าวันหนึ่งดึงข้อมูลย้อนหลังเพิ่มได้ ตัวตรวจจะขยับตาม
CUSTOMS_FIRST_YEAR = int(cust["ปี"].min())

p(f"{'ปี':<6}{'ปี พ.ศ.':>9}{'ราคาป้าย(ลบ.)':>16}{'ฐานนำเข้า สูง':>16}{'ฐานนำเข้า ต่ำ':>16}"
  f"{'นำเข้าจริง(ลบ.)':>18}")
zone_rows = []
for _, r in by_year.iterrows():
    y = int(r["year"])
    be = CY2BE.get(y)
    imp = np.nan
    if be is not None:
        sub = cust[(cust["ปี"] == be) & (cust["ทิศทาง"] == "import")]
        imp = sub["มูลค่าบาท"].sum() if len(sub) else np.nan
    hi = to_import_basis(r["val"], MARGIN_LO)
    lo = to_import_basis(r["val"], MARGIN_HI)
    zone_rows.append({"year": y, "retail": r["val"], "imp_hi": hi, "imp_lo": lo, "customs_import": imp})
    tag = f"  ⚠️ {PARTIAL[y]}" if y in PARTIAL else ""
    p(f"{y:<6}{be if be else '-':>9}{bt(r['val']):>16}{bt(hi):>16}{bt(lo):>16}"
      f"{(bt(imp) if imp == imp else '-'):>18}{tag}")
zone = pd.DataFrame(zone_rows)
p()

# กรอบที่ต้องตกอยู่ข้างใน สำหรับปี 2568 (= ปฏิทิน 2025) — คำนวณสดจากข้อมูลศุลกากร
be, cy = 2568, 2025
sub = cust[cust["ปี"] == be]
imp_total = sub[sub["ทิศทาง"] == "import"]["มูลค่าบาท"].sum()
row25 = zone[zone["year"] == cy].iloc[0]
p(f"----- ตรวจกรอบปี {cy} (พ.ศ. {be}) -----")
p(f"  ขอบล่างที่ศุลกากรวัดได้จริง (ผ่าน GATE, SOURCES.md §8) : 1,677 ลบ.")
p(f"  ยอดนำเข้ารวมทั้งหมด (คำนวณสดจากไฟล์ศุลกากร)          : {bt(imp_total)} ลบ.")
p(f"  ค่าที่วิธีนี้ได้ (ฐานนำเข้า) ต่ำ–สูง                    : {bt(row25['imp_lo'])} – {bt(row25['imp_hi'])} ลบ.")
FLOOR = 1677e6
if row25["imp_lo"] >= FLOOR and row25["imp_hi"] <= imp_total:
    verdict = "✅ ทั้งช่วงอยู่ในกรอบ"
elif row25["imp_hi"] < FLOOR:
    verdict = "⚠️ ทั้งช่วงต่ำกว่าขอบล่างของศุลกากร"
elif row25["imp_lo"] > imp_total:
    verdict = "🚨 สูงกว่ายอดนำเข้าทั้งหมด — เป็นไปไม่ได้ ต้องไล่ก่อนเผยแพร่"
else:
    verdict = "◐ ช่วงคร่อมเส้น 1,677 — ขอบบนผ่าน ขอบล่างยังไม่ผ่าน"
gap = (FLOOR - row25["imp_hi"]) / FLOOR
p(f"  → {verdict}")
if row25["imp_hi"] < FLOOR:
    p(f"     ขอบบนต่ำกว่าเส้น {gap:.1%}  (ห่าง {bt(FLOOR - row25['imp_hi'])} ลบ.)")
elif row25["imp_lo"] < FLOOR:
    p(f"     ขอบล่างต่ำกว่าเส้น {(FLOOR - row25['imp_lo']) / FLOOR:.1%}")
p()
p("  แปลผล: สองวิธีนี้**เก็บข้อมูลคนละทางกันสนิท** (ศุลกากรนับมูลค่าสินค้าที่ผ่านด่าน ·")
p("  วิธีนี้นับลำที่จดทะเบียนแล้วคูณราคาป้าย) ขอบบนต่ำกว่าพื้นศุลกากรเพียง")
p(f"  {(FLOOR - row25['imp_hi']) / FLOOR:.2%} ส่วนขอบล่างต่ำกว่า {(FLOOR - row25['imp_lo']) / FLOOR:.1%}")
p("  → ใช้ยืนยันว่าขนาดอยู่ในระดับสมเหตุสมผล แต่ไม่ใช่เส้นสอบผ่านหรือหลักฐานว่าค่าจริงตรงกัน")
p()
p("  ⚠️ ถ้าต่ำกว่า 1,677 แปลว่าอะไร: เป็นสัญญาณว่ามีของที่นำเข้ามาแล้วยังไม่ถูกจดทะเบียน")
p("  (จดช้า/ไม่จด/ขายไม่ออก) — **ไม่ใช่เหตุให้ไปปรับกำไรตัวแทนให้ตัวเลขเข้ากรอบ**")
p()
p("  📌 ข้อสังเกตที่ทำให้การเทียบนี้สมเหตุสมผลขึ้นกว่าเดิม: พิกัด HS 8806 คือ **ตัวอากาศยาน**")
p("  ส่วนแบตเตอรี่นำเข้าใต้พิกัดอื่น (8507) ดังนั้นการที่ราคาโดรนเกษตรหลายรุ่นเปลี่ยนมาใช้")
p("  ฐาน 'ตัวเครื่องเปล่า' จึงตรงกับสิ่งที่ศุลกากรนับมากกว่าฐาน 'ชุดพร้อมบิน'")
p()

# ------------------------------ 9) ตัวตรวจที่แข็งที่สุด: จำนวนลำโดรนเกษตร ปะทะ ศุลกากร
p("=" * 80)
p("ง) ตัวตรวจข้ามแหล่ง: จำนวนลำโดรนเกษตร กสทช. ปะทะ จำนวนชิ้นที่ศุลกากรบันทึก")
p("=" * 80)
p("โดรนพ่นยาชั้น 25-150 กก. ถูกสำแดงได้ 2 พิกัด (88062400 รีโมตอย่างเดียว / 88069400 ที่เหลือ)")
p("ผู้สำแดงเลือกไม่เหมือนกัน จึงเทียบกับ **ยอดรวมสองพิกัด** เป็นเพดาน")
p()
p("ตะกร้าที่เอามาเทียบต้องเป็นของชั้นน้ำหนักเดียวกันเท่านั้น จึงใช้เฉพาะ DJI AGRAS ซีรีส์ T")
p("(DJI ระบุ T10 น้ำหนักวิ่งขึ้นสูงสุด 26.8 กก. ที่ถังเต็ม 10 ลิตร รุ่นใหญ่กว่านั้นหนักกว่า")
p(" → ทั้งซีรีส์อยู่เหนือเส้น 25 กก.)  https://www.dji.com/support/product/t10")
p("ที่ตัดออกจากตะกร้า: MG-1/MG-1P/MG-1S ถัง 10 ลิตรรุ่นเก่า ซึ่งอยู่ติดเส้น 25 กก.")
p("— ตัดออกเพื่อไม่ให้ผลตรวจไปขึ้นกับข้อสมมติที่ยังไม่ได้ยืนยัน")
p()

is_agras_t = (df["brand"] == "DJI") & df["model_final"].str.match(r"^AGRAS T\d", na=False)
agras_year = df[is_agras_t].groupby("year")["units"].sum()
other_agri = df[(df["class"] == "เกษตร") & ~is_agras_t]

p(f"{'ปี':<6}{'ปี พ.ศ.':>9}{'DJI AGRAS ซีรีส์ T':>20}{'88062400':>12}{'88069400':>12}"
  f"{'เพดานรวม':>12}   ผลตรวจ")
for cy_, be_ in sorted(CY2BE.items()):
    n_reg = int(agras_year.get(cy_, 0))
    s = cust[(cust["ปี"] == be_) & (cust["ทิศทาง"] == "import")]
    q24 = int(s[s["พิกัด8"] == 88062400]["ปริมาณ"].sum())
    q94 = int(s[s["พิกัด8"] == 88069400]["ปริมาณ"].sum())
    tot2 = q24 + q94
    # ⚠️ ทั้งสองฝั่งต้องครอบคลุมเดือนเท่ากันถึงจะเทียบได้ — ไม่งั้นฝั่งที่ข้อมูลสั้นกว่าจะดูน้อยเสมอ
    m_cust = int(s["เดือน"].nunique())
    m_nbtc = int(nbtc_months.get(cy_, 0))
    if n_reg == 0 or tot2 == 0:
        verdict = "ข้อมูลไม่พอ"
    elif be_ == CUSTOMS_FIRST_YEAR:
        # 🚨 ปีแรกที่มีพิกัด HS 8806 เทียบไม่ได้เลย ไม่ว่าตัวเลขจะออกมาอย่างไร
        # เพราะโดรนมักถูกจดทะเบียนหลังนำเข้าพอสมควร ของที่เข้ามาก่อนปีนี้จึงยังทยอยมาจด
        # แต่ฝั่งนำเข้ามองไม่เห็น เพราะตอนนั้นโดรนอยู่ใต้พิกัดเก่า (8802/8525)
        verdict = f"⏸️ เทียบไม่ได้ — พ.ศ. {be_} เป็นปีแรกที่มีพิกัด 8806 ของที่เข้ามาก่อนอยู่ใต้พิกัดเก่า"
    elif m_cust != m_nbtc:
        verdict = f"⏸️ เทียบไม่ได้ — ศุลกากรมี {m_cust} เดือน แต่ กสทช. มี {m_nbtc} เดือน"
    elif n_reg <= tot2:
        verdict = f"✅ อยู่ใต้เพดาน ({n_reg / tot2:.0%} ของที่นำเข้า)"
    else:
        verdict = "🚨 จดมากกว่าที่นำเข้ารวมกัน — ต้องไล่ก่อนเผยแพร่"
    p(f"{cy_:<6}{be_:>9}{n_reg:>20,}{q24:>12,}{q94:>12,}{tot2:>12,}   {verdict}")
p()
p("อ่านผลอย่างไร: จดน้อยกว่าที่นำเข้าเป็นเรื่องปกติ (ของเข้ามาแล้วอาจยังไม่ถูกขายหรือยังไม่จด)")
p("แต่ถ้าจดมากกว่าที่นำเข้ารวมกัน แปลว่ามีอะไรผิด")
p()
p("⚠️ สัดส่วนในคอลัมน์ขวาเป็น **ขอบล่างของสัดส่วนจริง** ไม่ใช่ค่าที่วัดได้ตรง ๆ")
p("   เพราะตัวตั้งเป็น DJI AGRAS อย่างเดียว แต่ตัวหารเป็นยอดนำเข้าของ**ทุกยี่ห้อ**ในสองพิกัดนั้น")
p("   (มี XAG และรายอื่นปนอยู่) ถ้าแยกเฉพาะ DJI ได้ ตัวหารจะเล็กลง สัดส่วนจริงจึงสูงกว่านี้")
p("   ข้อมูลศุลกากรไม่มีคอลัมน์ยี่ห้อ จึงแยกไม่ได้ — เขียนกำกับไว้แทนการเดา")
p()
p("🔍 ข้อค้นพบที่โผล่มาจากการตรวจนี้ — โดรนเกษตรที่ไม่ใช่ DJI หายไปจากสถิตินำเข้า")
p(f"  ลำเกษตรที่ไม่ใช่ AGRAS ซีรีส์ T: {int(other_agri['units'].sum()):,} ลำ "
  f"({other_agri['units'].sum() / df[df['class'] == 'เกษตร']['units'].sum():.0%} ของลำเกษตรทั้งหมด)")
for b, n in other_agri.groupby("brand")["units"].sum().sort_values(ascending=False).head(8).items():
    p(f"    {int(n):>7,}  {b}")
p("  ถ้ารวมกลุ่มนี้เข้าไปด้วย ยอดจดทะเบียนจะเกินยอดนำเข้าทั้งสองพิกัดทุกปี")
p("  → สอดคล้องกับการที่แบรนด์ไทยหลายรายประกอบ/ผลิตในประเทศ ตัวเครื่องสำเร็จรูปจึงไม่เข้า HS 8806")
p("  ⚠️ ยังพิสูจน์ไม่ได้ว่าประกอบในประเทศจริง — เขียนได้แค่ว่า 'ไม่ปรากฏในพิกัดนำเข้านี้'")
p("  📌 ความหมายต่อการประเมินตลาด: การวัดตลาดจากศุลกากรอย่างเดียวจะ**มองไม่เห็นเซกเมนต์นี้ทั้งก้อน**")
p()

# --------------------------------------------------------------- 10) เซฟผลลัพธ์
# 🚨 กติกาของไฟล์ผลลัพธ์สองไฟล์ล่างนี้: **ต้องอ่านรู้เรื่องโดยไม่ต้องเปิดไฟล์อื่นควบ**
# ที่มา: เดิมไฟล์ทั้งสองมีแค่ยี่ห้อ/รุ่น/จำนวนลำ/มูลค่า คนที่จะตรวจว่า "ราคานี้มาจากไหน"
# ต้องเปิด nbtc_model_prices.csv + nbtc_model_tiers.csv + nbtc_code_map.csv มาไล่เทียบเอง
# ซึ่งไม่มีใครทำจริง → เป็นช่องให้ตัวเลขที่ไม่มีที่มาหลุดเข้ารายงานได้ (เคสเดียวกับ 0.04%)
OUTDIR.mkdir(parents=True, exist_ok=True)
save(by_year, OUTDIR / "market_value_by_year.csv")
save(up, OUTDIR / "unpriced_brackets.csv")
save(zone, OUTDIR / "import_basis_check.csv")

# --- ก) รุ่นที่ตั้งราคาได้: แนบราคาที่ใช้ + ราคาที่เก็บมา + แหล่ง มาไว้ในแถวเดียวกัน
# price_thb          = ราคาที่สคริปต์**ใช้คูณจริง**
# price_thb_collected= ราคาที่เก็บมาจากแหล่ง ก่อนกติกากันราคาผกผันทำงาน
# capped_from        = ถ้าไม่ว่าง แปลว่าราคาถูกกดลงมาเพราะรุ่นนี้แพงกว่ารุ่นที่ใหม่กว่าชื่อนี้
PROV = [
    "price_thb", "price_thb_collected", "capped_from", "basis_kind",
    "source", "source_url", "asof", "confidence",
    "price_lo_thb", "price_hi_thb", "spread_reason", "note",
]
by_model = (
    df[df.has_price]
    .groupby(["brand", "model_final", "class"])[["units", "val", "val_lo", "val_hi"]]
    .sum()
    .sort_values("val", ascending=False)
    .reset_index()
    .merge(prices[["brand", "model_final", *PROV]], on=["brand", "model_final"], how="left")
)
assert by_model["price_thb"].notna().all(), "มีรุ่นที่ตั้งราคาได้แต่ต่อคอลัมน์ที่มาไม่ติด"
# ไฟล์นี้วางจำนวนลำกับราคาไว้ข้างกัน คนอ่านจะเอามาคูณเองแน่ ๆ — ต้องคูณแล้วตรงกับ val
# ถ้าวันหนึ่งมีการปรับราคารายปี/รายแถว ตัวตรวจนี้จะดังทันที ไม่ปล่อยให้ไฟล์ขัดกันเองเงียบ ๆ
assert np.allclose(by_model["val"], by_model["units"] * by_model["price_thb"]), \
    "units × price_thb ไม่เท่ากับ val — ไฟล์ตรวจย้อนหลังจะขัดกันเอง"
by_model = by_model[["brand", "model_final", "class", "units", "val", "val_lo", "val_hi", *PROV]]
save(by_model, OUTDIR / "market_value_by_model.csv")

# --- ข) รุ่นที่ยังตีราคาไม่ได้: ต้องบอกด้วยว่า "ไม่ได้เพราะอะไร"
# สองสาเหตุนี้แก้คนละทาง ถ้าไม่แยก รายการที่เหลือก็เป็นแค่กำแพง ไม่ใช่สิ่งที่ทำงานต่อได้
#   ก. รู้ว่าเป็นรุ่นอะไรอยู่แล้ว แต่ยังไม่มีหลักฐานราคา  → ไปหาราคา
#   ข. ยังไม่รู้ว่าเป็นรุ่นอะไร (ช่องรุ่นเป็นรหัส/ว่าง)   → ต้องถอดรหัสก่อน หาราคาไม่ได้
#
# ⚠️ resolved_via เป็นคำตัดสินของสคริปต์ 01 ซึ่ง **ตาราง code map ทำมือมาถอดทับทีหลังได้**
# มี 7 รหัสที่สคริปต์ 01 ถอดไม่ได้แต่ code map ถอดให้ (เช่น QF2W4K → AVATA)
# ถ้าอ่าน resolved_via ตรง ๆ แถวพวกนี้จะติดป้ายว่า "ไม่รู้ว่าเป็นรุ่นอะไร" ทั้งที่รู้แล้ว
# กติกา: รุ่นหนึ่ง "รู้แล้ว" ถ้ามีรูปเขียนใดรูปหนึ่งที่ถอดออกมาเป็นชื่อจริงได้ (จากสคริปต์หรือ code map)
UNKNOWN_VIA = {"รหัสที่ถอดไม่ได้", "ว่าง"}
cat["_named"] = ~cat["resolved_via"].isin(UNKNOWN_VIA) | cat["_moved"]
via = (
    cat.sort_values(["_named", "units"], ascending=[False, False])
    .drop_duplicates(subset=["brand", "model_final"])  # เอาทั้งแถว ไม่ใช่ทีละคอลัมน์
    [["brand", "model_final", "resolved_via", "sample_raw"]]
)
known = cat.groupby(["brand", "model_final"], as_index=False)["_named"].any()
unp = (
    df[~df.has_price]
    .groupby(["brand", "model_final", "class", "group"])["units"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
    .merge(via, on=["brand", "model_final"], how="left")
    .merge(known, on=["brand", "model_final"], how="left")
)
unp["reason"] = np.where(
    unp["_named"].fillna(True),
    "รู้รุ่นแล้ว แต่ยังไม่มีหลักฐานราคา",
    np.where(
        unp["resolved_via"] == "ว่าง",
        "ยังไม่รู้ว่าเป็นรุ่นอะไร — ช่องรุ่นว่าง",
        "ยังไม่รู้ว่าเป็นรุ่นอะไร — ช่องรุ่นเป็นรหัสที่ยังถอดไม่ได้",
    ),
)
unp = unp[["brand", "model_final", "class", "group", "units", "reason",
           "resolved_via", "sample_raw"]]
save(unp, OUTDIR / "unpriced_models.csv")

p("----- ไฟล์รายรุ่น: อ่านจบได้ในไฟล์เดียว -----")
n_capped = int((by_model["capped_from"].fillna("") != "").sum())
u_capped = int(by_model.loc[by_model["capped_from"].fillna("") != "", "units"].sum())
p(f"  market_value_by_model.csv — {len(by_model)} รุ่น มีคอลัมน์ราคาที่ใช้ ราคาที่เก็บมา แหล่ง URL วันที่")
p(f"    ในนั้น {n_capped} รุ่น ({u_capped:,} ลำ) ราคาถูกกติกากันราคาผกผันกดลง — ดูคอลัมน์ capped_from")
p(f"  unpriced_models.csv — {len(unp)} รุ่น แยกสาเหตุแล้ว:")
for r, g in unp.groupby("reason")["units"].agg(["size", "sum"]).sort_values("sum", ascending=False).iterrows():
    p(f"    {int(g['size']):>5,} รุ่น {int(g['sum']):>7,} ลำ  {r}")
p()

p("=" * 80)
p("ข้อจำกัดที่ต้องเขียนกำกับทุกครั้งที่อ้างตัวเลขชุดนี้")
p("=" * 80)
p("1. เป็นมูลค่า **ตามราคาป้ายขายปลีก** ไม่ใช่ยอดขายจริง — ส่วนลด/โปรโมชันไม่ถูกนับ")
p("2. ใช้ราคาเดียวต่อรุ่นทุกปี → เส้นรายปีสะท้อน 'จำนวน+ส่วนผสมรุ่น' ล้วน ไม่มีเงินเฟ้อปน")
p("   ✅ ข้อดี: เทียบข้ามปีได้ **ถ้าอ่านคู่กับคอลัมน์ coverage** ซึ่งศุลกากรทำไม่ได้เลย")
p("   ⚠️ ข้อเสีย: ไม่ใช่เงินที่หมุนจริงในปีนั้น เพราะราคาของจริงลดลงตามอายุรุ่น")
p("2ก. **ราคาที่เก็บมาไม่ได้อยู่ในช่วงเวลาเดียวกัน** — Phantom 3 Standard เป็นสัญญาปีงบ 2559 ·")
p("   Mavic Pro เป็นราคาป้ายปี 2569 ของสินค้าตกรุ่นปี 2559 · Mini 5 Pro เป็นราคาปัจจุบันของสินค้าปัจจุบัน")
p("   จึงเรียกว่า 'ฐานราคาคงที่' ได้ไม่เต็มปาก — กระทบปีแรก ๆ ซึ่งมูลค่าน้อยอยู่แล้วเป็นหลัก")
p("3. ทะเบียน กสทช. ไม่ใช่ยอดขาย — โดรนที่ไม่จดทะเบียนไม่อยู่ในนี้ (CAAT เคยประเมินว่ามี ~20,000 ลำ)")
p("4. ไม่มีเลขเครื่อง → เครื่องเดิมเปลี่ยนมือแล้วจดใหม่จะนับซ้ำ ตรวจไม่ได้")
p("5. ปี 2017 (3 เดือน) และ 2026 (6 เดือน) ไม่ครบปี")
p(f"6. ยังตีราคาไม่ได้ {N_TOTAL - priced_units:,} ลำ ({1 - priced_units / N_TOTAL:.0%}) — "
  "รายงานเป็นช่วงแยก ไม่รวมในตัวเลขหลัก")

OUTTXT.write_text(out.getvalue(), encoding="utf-8")
print(out.getvalue())
