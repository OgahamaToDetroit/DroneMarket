# -*- coding: utf-8 -*-
"""
moc_importers.py — ค้นบริษัทที่ชื่อเกี่ยวกับโดรน จากทะเบียนผู้นำเข้า-ส่งออก กระทรวงพาณิชย์

API: GET https://tradereport.moc.go.th/api/importersexporters
     search_type = name | address
     keyword     = คำค้น (ภาษาไทยเท่านั้น — คำอังกฤษคืน 0 เสมอ)
     limit       = ค่าเริ่มต้น 20, สูงสุด 1000
     page_index  = ค่าเริ่มต้น 1
ไม่ต้องใช้ API key · อัปเดตรายเดือน (หลังวันที่ 20)

═══════════════════════════════════════════════════════════════════════
⚠️  ข้อจำกัดสำคัญ — อ่านก่อนใช้ผลลัพธ์
═══════════════════════════════════════════════════════════════════════
API นี้ค้นได้แค่ "ชื่อ" กับ "ที่อยู่" **ไม่มีตัวกรองพิกัดศุลกากร (HS code)**
และ response มีแค่ name / address / phone ไม่มีฟิลด์บอกว่าสินค้าอะไร
หรือเป็นผู้นำเข้าหรือผู้ส่งออก

ดังนั้นผลลัพธ์คือ:
  ✅ "บริษัทที่อยู่ในทะเบียนผู้นำเข้า-ส่งออกของกระทรวงพาณิชย์
      และมีชื่อเกี่ยวข้องกับโดรน"
  ❌ ไม่ใช่ "ผู้นำเข้าโดรน (HS 8806)" และไม่ได้บอกมูลค่าการนำเข้า

ถ้าต้องการมูลค่านำเข้าโดรนแยกรายประเทศ ให้ใช้ `moc_hs_trade.py` แทน
(คนละ endpoint ที่กรอง HS code ได้จริง)

การจับคู่เป็นแบบ substring จึงมี false positive เช่น "ไฮโดรนิคส์"
(hydronics) ที่มีตัวอักษร "โดรน" อยู่ข้างใน — สคริปต์กรองออกให้แล้ว
และรายงานว่ากรองอะไรออกไปบ้าง

--- วิธีใช้ ---
    python scripts/moc_importers.py
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = PROJECT_ROOT / "data" / "processed"

API = "https://tradereport.moc.go.th/api/importersexporters"

# คำค้นทั่วไป — เลือกเฉพาะคำที่ให้ผลตรงจริง
# หมายเหตุ: ไม่ใส่ "แอโร" (106 ผล ส่วนใหญ่เป็น aerosol/aerospace)
#           และ "เอวิเอชั่น" (120 ผล เป็นสายการบิน/MRO) เพราะกลบผลจริง
KEYWORDS = ["โดรน", "ยูเอวี"]

# ค้นเจาะจงชื่อแบรนด์ที่พบในข้อมูลทะเบียน กสทช. (ถอดเสียงเป็นไทย)
BRAND_LOOKUPS = {
    "โพลาโดรน": "POLADRONE",
    "เอชจี โรโบติกส์": "HG ROBOTICS",
    "ดีเจไอ": "DJI",
}

# ตัดชื่อที่มีคำค้นอยู่ข้างในแต่ไม่เกี่ยวกับโดรน
#   ไฮโดร-   = hydro  (ไฮโดรนิคส์, ไฮโดรนีโอ, ไฮโดรนอทส์)
#   ดีเจไออี = DJIE   (บจก.ดีเจไออี เมดิคอล — บริษัทการแพทย์ คนละรายกับ DJI)
FALSE_POSITIVE_PATTERNS = ["ไฮโดร", "ดีเจไออี"]


def search_all(keyword: str, search_type: str = "name") -> list[dict]:
    """ดึงผลทุกหน้าของคำค้นหนึ่งคำ"""
    rows: list[dict] = []
    page = 1
    while True:
        resp = requests.get(API, params={"search_type": search_type, "keyword": keyword,
                                         "limit": 1000, "page_index": page}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        rows.extend(data.get("datas", []))
        if page >= data.get("total_page", 1) or not data.get("datas"):
            break
        page += 1
        time.sleep(0.8)
    return rows


def extract_province(address: str) -> str:
    """ดึงชื่อจังหวัดจากที่อยู่ เช่น '... จังหวัดกรุงเทพมหานคร 10110' -> กรุงเทพมหานคร"""
    m = re.search(r"จังหวัด\s*([^\s0-9]+)", str(address))
    return m.group(1) if m else ""


def main() -> None:
    collected: dict[tuple[str, str], dict] = {}
    excluded: list[tuple[str, str]] = []
    dupe_count = 0

    print("=== ค้นตามคำทั่วไป ===")
    for kw in KEYWORDS:
        rows = search_all(kw)
        print(f"  {kw:<12} API คืน {len(rows)} รายการ")
        for r in rows:
            name = str(r.get("name", "")).strip()
            addr = str(r.get("address", "")).strip()

            hit = next((p for p in FALSE_POSITIVE_PATTERNS if p in name), None)
            if hit:
                excluded.append((name, f"มี '{hit}' — ไม่เกี่ยวกับโดรน"))
                continue

            key = (name, addr)          # dedup ด้วย ชื่อ+ที่อยู่
            if key in collected:        # สาขาคนละที่ถือเป็นคนละแถว (ถูกต้อง)
                dupe_count += 1
                continue
            collected[key] = {
                "name": name, "address": addr, "phone": str(r.get("phone", "")).strip(),
                "province": extract_province(addr), "matched": kw, "match_type": "keyword",
            }
        time.sleep(1.0)

    print("\n=== ค้นเจาะจงชื่อแบรนด์จากข้อมูล กสทช. ===")
    for th_name, brand in BRAND_LOOKUPS.items():
        rows = search_all(th_name)
        print(f"  {th_name:<18} ({brand:<12}) -> {len(rows)} รายการ")
        for r in rows:
            name = str(r.get("name", "")).strip()
            addr = str(r.get("address", "")).strip()

            # ต้องกรอง false positive ที่ชั้นนี้ด้วย ไม่ใช่แค่ชั้นคำค้นทั่วไป
            hit = next((p for p in FALSE_POSITIVE_PATTERNS if p in name), None)
            if hit:
                excluded.append((name, f"มี '{hit}' — ไม่เกี่ยวกับโดรน"))
                continue

            key = (name, addr)
            if key in collected:
                # เจอจากคำค้นทั่วไปแล้ว — อัปเกรดเป็น brand match
                collected[key]["match_type"] = "brand"
                collected[key]["matched"] = f"{th_name} ({brand})"
                continue
            collected[key] = {
                "name": name, "address": addr, "phone": str(r.get("phone", "")).strip(),
                "province": extract_province(addr),
                "matched": f"{th_name} ({brand})", "match_type": "brand",
            }
        time.sleep(1.0)

    df = pd.DataFrame(collected.values()).sort_values(["match_type", "name"])

    PROC_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = PROC_DIR / "moc_drone_companies.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(f"\n[OK] saved -> {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"     บริษัทที่เก็บได้ {len(df)} ราย "
          f"(ตัด false positive {len(excluded)} · รวมแถวซ้ำ {dupe_count})")

    if excluded:
        print("\n--- ตัดออกเพราะไม่เกี่ยวกับโดรน ---")
        for name, why in excluded:
            print(f"    {name}  [{why}]")

    print("\n=== รายชื่อบริษัท ===")
    for _, r in df.iterrows():
        tag = "[แบรนด์]" if r["match_type"] == "brand" else "        "
        prov = r["province"] or "-"
        print(f"  {tag} {r['name'][:44]:<46} {prov:<16} {r['phone']}")

    if not df.empty:
        print("\n=== กระจายตามจังหวัด ===")
        for prov, n in df["province"].replace("", "ไม่ระบุ").value_counts().items():
            print(f"  {prov:<20} {n}")

    print("\n⚠️  ผลนี้คือ 'บริษัทในทะเบียนผู้นำเข้า-ส่งออกที่ชื่อเกี่ยวกับโดรน'")
    print("    ไม่ใช่ 'ผู้นำเข้าโดรน' — API ไม่มีข้อมูลว่าบริษัทไหนนำเข้าสินค้าอะไร")


if __name__ == "__main__":
    main()
