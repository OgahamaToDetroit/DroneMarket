# -*- coding: utf-8 -*-
"""ขั้นที่ 1 — แกะคอลัมน์ Brand/Model ของทะเบียน กสทช. ให้เหลือ "รุ่นเดียวกันคือก้อนเดียวกัน"

ปัญหาที่ต้องแก้: ช่อง Model ของ DJI ราว 41% เป็น **รหัสภายในโรงงาน** (MT2PD, DN1A0626)
ไม่ใช่ชื่อรุ่นที่คนซื้อขายกัน จึงตั้งราคาไม่ได้

วิธีแก้ที่ไม่ต้องเดา: อีกราว 14% ของแถวเขียน **ทั้งรหัสและชื่อรุ่นในช่องเดียวกัน**
    MT2PD (DJI MINI 2 FLY MORE COMBO)
    DEN225/DJI NEO 2 FLY MORE COMBO
    AGRAS T50 (3WWDZ-40B)
→ ชุดข้อมูลถอดรหัสตัวเองได้ สร้าง dict `รหัส → ชื่อรุ่น` จากแถวพวกนี้
  แล้วเอาไปเติมให้แถวที่มีแต่รหัส

ผลลัพธ์:
    data/processed/nbtc_pricing/model_catalog.csv   ← แคตตาล็อกรุ่น + จำนวนลำรายปี
    data/processed/nbtc_pricing/code_dictionary.csv ← dict รหัส→ชื่อ พร้อมจำนวนแถวที่ยืนยัน
    data/processed/nbtc_pricing/code_conflicts.csv  ← รหัสที่ชี้ไปหลายรุ่น (ต้องดูด้วยตา)
    scripts/nbtc_pricing/01_build_model_catalog_out.txt

รันจาก root:  python scripts/nbtc_pricing/01_build_model_catalog.py
"""
import io
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "raw" / "drone_data.xlsx"
OUTDIR = ROOT / "data" / "processed" / "nbtc_pricing"
OUTTXT = Path(__file__).with_name("01_build_model_catalog_out.txt")

out = io.StringIO()


def p(*a):
    print(*a, file=out)


# ---------------------------------------------------------------- 0) โหลดดิบ
# ไฟล์นี้โหลดมือจาก https://datacatalog.nbtc.go.th/dataset/dataset_11_94 แบบไม่กรองอะไรเลย
# โปรเจกต์ไม่มีสคริปต์ดึงอัตโนมัติ (ดู SOURCES.md §1) จึงอ่านไฟล์ดิบตรง ๆ
if not RAW.exists():
    raise SystemExit(f"ไม่พบไฟล์ดิบ {RAW} — ดาวน์โหลดจาก datacatalog.nbtc.go.th ก่อน")

SNAPSHOT = datetime.fromtimestamp(RAW.stat().st_mtime, tz=timezone.utc).astimezone()
df = pd.read_excel(RAW)
N_RAW = len(df)

p("=" * 78)
p("ขั้นที่ 1 — แกะรุ่นจากทะเบียน กสทช.")
p("=" * 78)
p(f"ไฟล์ดิบ      : {RAW.relative_to(ROOT)}")
p(f"snapshot     : {SNAPSHOT:%Y-%m-%d %H:%M} (mtime ของไฟล์ที่โหลดมา)")
p(f"จำนวนแถว     : {N_RAW:,}  (1 แถว = 1 ลำ — ชุดนี้ไม่มีคอลัมน์จำนวน)")
p(f"คอลัมน์      : {', '.join(df.columns)}")
p()


# ---------------------------------------------------------- 1) ปี (พ.ศ.→ค.ศ.)
def parse_year(s):
    try:
        return int(str(s).split()[-1]) - 543
    except Exception:
        return None


df["year"] = df["ApprovedDate"].map(parse_year)

TH_MONTH = {
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
}


def parse_month(s):
    try:
        return TH_MONTH.get(str(s).split()[1])
    except Exception:
        return None


df["month"] = df["ApprovedDate"].map(parse_month)

# ปีที่มีข้อมูลไม่ครบ 12 เดือน — ห้ามเอาไปเทียบกับปีเต็ม
months_per_year = df.groupby("year")["month"].nunique()
PARTIAL_YEARS = {int(y): int(m) for y, m in months_per_year.items() if m < 12}
p("----- ความครบถ้วนรายปี -----")
for y, m in months_per_year.items():
    flag = f"  ⚠️ ไม่ครบปี ({m}/12 เดือน)" if m < 12 else ""
    p(f"  {int(y)}: {m:>2} เดือน · {int((df['year'] == y).sum()):>7,} ลำ{flag}")
p()


# ------------------------------------------------------------- 2) แบรนด์
# รวมชื่อที่สะกดต่างกันแต่เป็นเจ้าเดียวกัน — SOURCES.md §1 เตือนไว้ว่าถ้าไม่รวมจะนับต่ำไปครึ่งหนึ่ง
# ⚠️ ห้าม match แบบ substring เด็ดขาด (`ICS` จะไปโดน `Autel Robotics`) — ตารางนี้เทียบตรงตัวล้วน
BRAND_ALIAS = {
    "NACDRONE": "NAC DRONE",
    "NAC-DRONE": "NAC DRONE",
    "HOVER AIR": "HOVERAIR",
    "HOVER-AIR": "HOVERAIR",
    "DGI": "DJI",          # สะกดสลับตัวอักษร
    "DGI AGRAS": "DJI",
    "DJI AGRAS": "DJI",
    "DJI INNOVATIONS": "DJI",
    "เกษตรเจนวาย": "KASET GEN-Y",
    "เกษตร เจน วาย": "KASET GEN-Y",
    "AUTEL": "AUTEL ROBOTICS",
}


def norm_brand(s):
    b = re.sub(r"\s+", " ", str(s).strip().upper())
    return BRAND_ALIAS.get(b, b)


df["brand"] = df["Brand"].map(norm_brand)

p("----- ผลของตารางรวมชื่อแบรนด์ -----")
raw_brand = df["Brand"].astype(str).str.strip().str.upper().str.replace(r"\s+", " ", regex=True)
merged = 0
for alias, target in sorted(BRAND_ALIAS.items()):
    n = int((raw_brand == alias).sum())
    if n:
        p(f"  {alias:<20} → {target:<16} {n:>6,} ลำ")
        merged += n
p(f"  รวมที่ถูกย้าย {merged:,} ลำ · แบรนด์ {raw_brand.nunique()} → {df['brand'].nunique()} ชื่อ")
p()


# ------------------------------------------------- 3) แยกรหัส/ชื่อ ออกจากช่อง Model
# รหัสตัวเครื่องของ DJI: ตัวอักษร 2-3 ตัว + เลข + ตัวอักษร/เลข (MT2PD, DN1A0626, CZ3SCL, DEN225)
CODE_RE = re.compile(r"^[A-Z]{2,3}\d[A-Z0-9]{1,7}$")
# รหัสโดรนเกษตร DJI/XAG ตามมาตรฐานจีน (3WWDZ = เครื่องพ่นยาไร้คนขับ)
AGRI_CODE_RE = re.compile(r"^3WWDZ-[A-Z0-9.]+$")
# 🚨 รหัสรีโมต ไม่ใช่ตัวเครื่อง — ถ้าไม่คัดออกจะกลายเป็น "รุ่น" ปลอมและถูกตั้งราคา
CTRL_RE = re.compile(r"^(RC|RM)\d+[A-Z]*$")

# วงเล็บกำกับภูมิภาค/ชุดขาย/รีโมต — ตัดทิ้งก่อนเทียบชื่อรุ่น
NOISE = [
    r"\(GL\)", r"\(EU\)", r"\(CE\)", r"\(D\)", r"\(FCC\)", r"\(JP\)", r"\(TH\)",
    r"\(DJI RC ?2?\)", r"\(DJI RC-?N?\d?\)", r"\(DJI RC PRO\)", r"\(RC ?2?\)",
    r"\(AIRCRAFT\)", r"\(REMOTE CONTROLLER\)", r"\(DRONE\)",
    r"\(THREE BATTERIES?\)", r"\(TWO BATTERIES?\)", r"\(SINGLE BATTERY\)",
    r"\(DJI GOGGLES ?\d?\)", r"\(DJI GOGGLES N3\)",
]
COMBO_RE = re.compile(r"FLY MORE COMBO PLUS|FLY MORE COMBO|PRO-?VIEW COMBO|MOTION COMBO|COMBO")

# คำที่บอกว่าชิ้นส่วนนี้เป็น "ชื่อรุ่น" ไม่ใช่รหัส
FAMILY_WORDS = {
    "MINI", "MAVIC", "AIR", "PHANTOM", "NEO", "FLIP", "AVATA", "AGRAS", "MATRICE",
    "INSPIRE", "SPARK", "TELLO", "EVO", "ZINO", "ANAFI", "KARMA", "ATOM", "EASY",
    "SALUTE", "MIST", "ULTRA", "GCS", "T10", "T16", "T20", "T25", "T30", "T40",
    "T50", "T70", "T100", "P100",
}


def strip_noise(s):
    for pat in NOISE:
        s = re.sub(pat, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def split_fragments(s):
    """ตัดช่อง Model เป็นชิ้น ๆ ตามตัวคั่น แล้วคืนชิ้นที่ไม่ว่าง"""
    parts = re.split(r"[/(),\[\]]+", s)
    return [re.sub(r"\s+", " ", x).strip() for x in parts if x and x.strip()]


def classify(frag):
    """คืน 'code' / 'ctrl' / 'name' / 'other'"""
    f = frag.strip().upper()
    if CTRL_RE.match(f):
        return "ctrl"
    if AGRI_CODE_RE.match(f):
        return "code"
    if CODE_RE.match(f) and any(c.isdigit() for c in f):
        return "code"
    toks = set(re.split(r"[\s\-]+", f))
    if toks & FAMILY_WORDS:
        return "name"
    return "other"


# ชื่อรุ่นที่สะกดต่างกันแต่เป็นรุ่นเดียวกัน (กติกาการเขียน ไม่ใช่ตัวเลข จึงอยู่ในโค้ด)
MODEL_ALIAS = {
    "MINI2": "MINI 2", "MINI3": "MINI 3", "MINI4": "MINI 4",
    "MINI 4 K": "MINI 4K", "MINI4K": "MINI 4K",
    "MINI PRO 3": "MINI 3 PRO", "MINI PRO 4": "MINI 4 PRO",
    "MAVIC MINI 2": "MINI 2", "MAVIC AIR2": "MAVIC AIR 2",
    "MAVIC AIR 2S": "AIR 2S", "MAVIC AIR2S": "AIR 2S",
    "PHANTOM 4 PROFESSIONAL": "PHANTOM 4 PRO",
    "PHANTOM 4 PROFESSIONAL V2.0": "PHANTOM 4 PRO V2.0",
    "PHANTOM 3 PROFESSIONAL": "PHANTOM 3 PRO",
    "PHANTOM 4 ADVANCED": "PHANTOM 4 ADV",
    "PHANTOM 3 ADVANCED": "PHANTOM 3 ADV",
    "AGRAS T20P": "AGRAS T20P", "T20P": "AGRAS T20P", "T16/20": "AGRAS T16",
    "T10": "AGRAS T10", "T20": "AGRAS T20", "T25": "AGRAS T25",
    "T30": "AGRAS T30", "T40": "AGRAS T40", "T50": "AGRAS T50",
    "AG T20P": "AGRAS T20P", "AG T40": "AGRAS T40", "AG T30": "AGRAS T30",
}


def canon_name(frag):
    """ทำชื่อรุ่นให้เป็นรูปมาตรฐาน — ตัด DJI นำหน้า / ตัดคำชุดขาย / รวมคำสะกดต่าง"""
    s = strip_noise(frag.upper())
    s = re.sub(r"^DJI\s+", "", s)
    s = COMBO_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip(" -/")
    return MODEL_ALIAS.get(s, s)


records = []
# ⚠️ ต้อง fillna ก่อน astype — บน pandas รุ่นนี้ astype(str) ปล่อย NaN เป็น float ทิ้งไว้
purposes = df["PurposeOfUseAircraft"].fillna("").astype(str).tolist()
for i, (raw_model, brand, year) in enumerate(zip(df["Model"], df["brand"], df["year"])):
    s = re.sub(r"\s+", " ", str(raw_model).strip().upper())
    frags = split_fragments(strip_noise(s))
    codes, names = [], []
    for fr in frags:
        kind = classify(fr)
        if kind == "code":
            codes.append(fr.upper())
        elif kind == "name":
            nm = canon_name(fr)
            if nm:
                names.append(nm)
        # 'ctrl' ทิ้ง · 'other' เก็บไว้เป็นชื่อสำรองด้านล่าง
    if not names and not codes:
        # ไม่เข้าพวกไหนเลย — ใช้ข้อความทั้งช่องเป็นชื่อ (เช่น STD4117S, DMD-M400W-V3)
        nm = canon_name(s)
        if nm:
            names.append(nm)
    records.append(
        {
            "brand": brand,
            "raw": s,
            "codes": codes,
            "names": names,
            "is_combo": bool(COMBO_RE.search(s)),
            "year": year,
            # ใช้จำแนกกลุ่มรุ่นทีหลัง — โดรนเกษตรราคาคนละชั้นกับโดรนถ่ายภาพสิบเท่า
            "is_agri": "เกษตร" in purposes[i],
        }
    )

parsed = pd.DataFrame(records)
parsed["n_code"] = parsed["codes"].map(len)
parsed["n_name"] = parsed["names"].map(len)

p("----- ผลการแยกช่อง Model -----")
both = parsed[(parsed.n_code > 0) & (parsed.n_name > 0)]
only_code = parsed[(parsed.n_code > 0) & (parsed.n_name == 0)]
only_name = parsed[(parsed.n_code == 0) & (parsed.n_name > 0)]
neither = parsed[(parsed.n_code == 0) & (parsed.n_name == 0)]
for label, sub in [
    ("มีทั้งรหัสและชื่อ (ใช้สร้าง dict)", both),
    ("มีแต่รหัส (ต้องถอด)", only_code),
    ("มีแต่ชื่อ (ใช้ได้เลย)", only_name),
    ("ไม่เข้าพวกไหน", neither),
]:
    p(f"  {label:<38} {len(sub):>7,}  ({len(sub) / N_RAW:6.2%})")
p()


# ------------------------------------------ 4) สร้าง dict รหัส→ชื่อ พร้อมรายงานที่ชนกัน
code_to_names = defaultdict(Counter)
for _, r in both.iterrows():
    for c in r["codes"]:
        for n in r["names"]:
            code_to_names[(r["brand"], c)][n] += 1

name_to_codes = defaultdict(Counter)
for (brand, c), names in code_to_names.items():
    for n, k in names.items():
        name_to_codes[(brand, n)][c] += k

dict_rows, conflict_rows = [], []
for (brand, c), names in sorted(code_to_names.items()):
    total = sum(names.values())
    top_name, top_n = names.most_common(1)[0]
    share = top_n / total
    dict_rows.append(
        {
            "brand": brand,
            "code": c,
            "model": top_name,
            "rows_support": total,
            "top_share": round(share, 4),
            "n_distinct_names": len(names),
            "all_names": " | ".join(f"{n}×{k}" for n, k in names.most_common()),
        }
    )
    if len(names) > 1:
        conflict_rows.append(
            {
                "kind": "code→หลายชื่อ",
                "brand": brand,
                "key": c,
                "chosen": top_name,
                "chosen_share": round(share, 4),
                "candidates": " | ".join(f"{n}×{k}" for n, k in names.most_common()),
            }
        )

for (brand, n), codes in sorted(name_to_codes.items()):
    if len(codes) > 1:
        conflict_rows.append(
            {
                "kind": "ชื่อ→หลายรหัส",
                "brand": brand,
                "key": n,
                "chosen": codes.most_common(1)[0][0],
                "chosen_share": round(codes.most_common(1)[0][1] / sum(codes.values()), 4),
                "candidates": " | ".join(f"{c}×{k}" for c, k in codes.most_common()),
            }
        )

code_dict = {(r["brand"], r["code"]): r["model"] for r in dict_rows}
dict_df = pd.DataFrame(dict_rows).sort_values("rows_support", ascending=False)
conf_df = pd.DataFrame(conflict_rows)

p("----- dict รหัส→ชื่อ ที่ถอดได้จากตัวข้อมูลเอง -----")
p(f"  ถอดได้ {len(dict_df):,} รหัส")
p(f"  ชนกัน  {len(conf_df):,} รายการ (ดู code_conflicts.csv — ต้องดูด้วยตา ไม่ทับเงียบ ๆ)")
p()
p("  20 รหัสที่มีแถวยืนยันมากที่สุด:")
for _, r in dict_df.head(20).iterrows():
    warn = "  ⚠️ ชนกัน" if r["n_distinct_names"] > 1 else ""
    p(f"    {r['code']:<12} → {r['model']:<34} ({r['rows_support']:>5,} แถวยืนยัน){warn}")
p()
if len(conf_df):
    p("  รายการที่ชนกัน 15 อันดับแรก:")
    for _, r in conf_df.head(15).iterrows():
        p(f"    [{r['kind']}] {r['key']:<16} เลือก {r['chosen']:<26} ({r['chosen_share']:.0%})")
        p(f"        ตัวเลือก: {r['candidates'][:120]}")
p()


# ------------------------------------------------------- 5) เติมชื่อให้แถวที่มีแต่รหัส
def resolve(row):
    if row["names"]:
        return row["names"][0], "ชื่อในช่องเอง"
    for c in row["codes"]:
        hit = code_dict.get((row["brand"], c))
        if hit:
            return hit, "ถอดจากรหัส"
    if row["codes"]:
        return row["codes"][0], "รหัสที่ถอดไม่ได้"
    return "(ไม่ระบุ)", "ว่าง"


res = parsed.apply(resolve, axis=1, result_type="expand")
parsed["model"] = res[0]
parsed["resolved_via"] = res[1]

p("----- ผลการเติมชื่อ -----")
for via, n in parsed["resolved_via"].value_counts().items():
    p(f"  {via:<24} {n:>7,}  ({n / N_RAW:6.2%})")
gained = int((parsed["resolved_via"] == "ถอดจากรหัส").sum())
still = int((parsed["resolved_via"] == "รหัสที่ถอดไม่ได้").sum())
p()
p(f"  → dict ที่ข้อมูลถอดตัวเองกู้ชื่อรุ่นกลับมาได้ {gained:,} ลำ ({gained / N_RAW:.1%} ของทั้งชุด)")
p(f"  → ยังเหลือรหัสที่ถอดไม่ได้ {still:,} ลำ ({still / N_RAW:.1%}) — ไปอยู่ในกลุ่ม 'ยังไม่มีราคา'")
p()

p("  รหัสที่ถอดไม่ได้ 25 ตัวที่มีจำนวนมากสุด (ยังไม่รู้ว่าเป็นรุ่นอะไร):")
unres = parsed[parsed["resolved_via"] == "รหัสที่ถอดไม่ได้"]
for (b, m), k in unres.groupby(["brand", "model"]).size().sort_values(ascending=False).head(25).items():
    p(f"    {k:>6,}  {b} | {m}")
p()


# ------------------------------------------------------------------ 6) แคตตาล็อก
cat = (
    parsed.groupby(["brand", "model"])
    .agg(
        units=("model", "size"),
        combo_units=("is_combo", "sum"),
        agri_units=("is_agri", "sum"),
        n_raw_variants=("raw", "nunique"),
    )
    .reset_index()
)
# ≥60% ของลำแจ้งวัตถุประสงค์ว่าเกษตร → ถือเป็นรุ่นโดรนเกษตร (จำแนกจากข้อมูล ไม่ใช่เดา)
cat["agri_share"] = (cat["agri_units"] / cat["units"]).round(3)
cat["class"] = ["เกษตร" if s >= 0.6 else "ทั่วไป" for s in cat["agri_share"]]
via = parsed.groupby(["brand", "model"])["resolved_via"].agg(lambda s: s.value_counts().index[0])
cat = cat.merge(via.rename("resolved_via"), on=["brand", "model"])
sample = parsed.groupby(["brand", "model"])["raw"].agg(lambda s: " ;; ".join(list(s.value_counts().index[:3])))
cat = cat.merge(sample.rename("sample_raw"), on=["brand", "model"])

year_piv = parsed.pivot_table(index=["brand", "model"], columns="year", values="raw", aggfunc="count", fill_value=0)
year_piv.columns = [f"units_{int(c)}" for c in year_piv.columns]
cat = cat.merge(year_piv.reset_index(), on=["brand", "model"])
cat = cat.sort_values("units", ascending=False).reset_index(drop=True)
cat.insert(0, "rank", range(1, len(cat) + 1))
cat["cum_share"] = (cat["units"].cumsum() / N_RAW).round(4)

p("----- แคตตาล็อกรุ่นหลังรวมแล้ว -----")
p(f"  brand-model ก่อนรวม (ข้อความดิบ) : {df.groupby(['brand', df['Model'].astype(str).str.strip().str.upper()]).ngroups:,} คู่")
p(f"  brand-model หลังรวม              : {len(cat):,} คู่")
for t in (0.5, 0.8, 0.9, 0.95, 0.99):
    need = int((cat["cum_share"] < t).sum()) + 1
    p(f"    ครอบคลุม {t:.0%} ของลำ ต้องตั้งราคา {need:>4,} คู่")
p()
p("  30 อันดับแรกหลังรวม:")
for _, r in cat.head(30).iterrows():
    p(f"    {r['rank']:>3}. {r['units']:>7,}  {r['cum_share']:6.1%}  {r['brand']} | {r['model']}"
      f"   [{r['resolved_via']}, {r['n_raw_variants']} รูปเขียน]")
p()

OUTDIR.mkdir(parents=True, exist_ok=True)
# จำนวนเดือนที่มีข้อมูลในแต่ละปี — ขั้นถัดไปต้องใช้กันการเทียบข้ามแหล่งที่หน้าต่างเวลาไม่เท่ากัน
months_per_year.rename("months").reset_index().to_csv(
    OUTDIR / "year_coverage.csv", index=False, encoding="utf-8-sig"
)
cat.to_csv(OUTDIR / "model_catalog.csv", index=False, encoding="utf-8-sig")
dict_df.to_csv(OUTDIR / "code_dictionary.csv", index=False, encoding="utf-8-sig")
if len(conf_df):
    conf_df.to_csv(OUTDIR / "code_conflicts.csv", index=False, encoding="utf-8-sig")

# เก็บผลไว้ให้ขั้นที่ 2 ใช้ (ยุบเป็นราย brand-model-ปี แล้ว ไม่ต้อง parse ใหม่)
long = (
    parsed.groupby(["brand", "model", "year", "is_combo", "resolved_via"])
    .size()
    .rename("units")
    .reset_index()
)
long.to_csv(OUTDIR / "registrations_by_model_year.csv", index=False, encoding="utf-8-sig")

p("=" * 78)
p("ไฟล์ผลลัพธ์:")
p("  data/processed/nbtc_pricing/model_catalog.csv")
p("  data/processed/nbtc_pricing/code_dictionary.csv")
p("  data/processed/nbtc_pricing/code_conflicts.csv")
p("  data/processed/nbtc_pricing/registrations_by_model_year.csv")
p()
p("⚠️ ข้อจำกัดที่ต้องเขียนกำกับทุกครั้ง:")
p("  1. ชุดนี้เป็นทะเบียน 'คลื่นความถี่' ไม่ใช่ยอดขาย — โดรนที่ไม่จดทะเบียนไม่อยู่ในนี้")
p("  2. ไม่มีเลขเครื่อง/เลขผู้ถือ → ถ้าเครื่องเดิมเปลี่ยนมือแล้วจดใหม่ จะนับซ้ำโดยตรวจไม่ได้")
p(f"  3. ปีที่ข้อมูลไม่ครบ: {', '.join(f'{y} ({m}/12 เดือน)' for y, m in sorted(PARTIAL_YEARS.items()))}")
p("     ห้ามเอาไปวางเทียบกับปีเต็มโดยไม่ติดป้าย")
p("  4. รหัสที่ถอดไม่ได้ยังไม่รู้ว่าเป็นรุ่นอะไร — ห้ามเดาราคาให้")

OUTTXT.write_text(out.getvalue(), encoding="utf-8")
print(out.getvalue())
