# -*- coding: utf-8 -*-
"""
moc_hs_trade.py — มูลค่านำเข้า/ส่งออกโดรน (HS 8806) รายเดือน จากกระทรวงพาณิชย์

ต้นทางเดียวกับที่ไทยส่งให้ UN Comtrade แต่ละเอียดกว่า:
    Comtrade  = รายปี, USD อย่างเดียว
    MOC       = **รายเดือน**, ทั้ง USD และ **เงินบาท**, มียอดสะสมรายปีให้ด้วย

API: GET https://tradereport.moc.go.th/api/importharmonizecountries   (นำเข้า)
     GET https://tradereport.moc.go.th/api/exportharmonizecountries   (ส่งออก)
     year    = ปี ค.ศ. (Integer)
     month   = เดือน 1-12 (Integer)
     hs_code = ระบุได้ 2, 4, 6, 8 หรือ 11 หลัก  ← พารามิเตอร์คือ hs_code ไม่ใช่ hscode
     limit   = สูงสุด 10
ไม่ต้องใช้ API key · อัปเดตรายเดือน (หลังวันที่ 20)

--- ตรวจสอบความถูกต้องแล้ว ---
ยอดสะสมปี 2024 ของ MOC ตรงกับ UN Comtrade ทุกหลัก เช่น
    จีน 86,083,776 · สิงคโปร์ 582,012 · สหรัฐฯ 259,472 · มาเลเซีย 239,919
ยืนยันว่า Comtrade รับข้อมูลไทยมาจากชุดนี้โดยตรง

--- ข้อจำกัด ---
* limit สูงสุด 10 → ได้แค่ประเทศคู่ค้า top 10 ของแต่ละเดือน
  (ประเทศเล็ก ๆ นอก top 10 จะตกหล่น — ยอดรวมรายเดือนจึงเป็น "อย่างน้อย")
* ฟิลด์ acc_* คือยอดสะสมตั้งแต่ต้นปีถึงเดือนนั้น เดือน 12 = ทั้งปี

--- วิธีใช้ ---
    python scripts/moc_hs_trade.py                        # ปี 2024-2025 ทั้งนำเข้าและส่งออก
    python scripts/moc_hs_trade.py --years 2025
    python scripts/moc_hs_trade.py --hs 880610 --years 2025
"""
from __future__ import annotations

import argparse
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

ENDPOINTS = {
    "import": "https://tradereport.moc.go.th/api/importharmonizecountries",
    "export": "https://tradereport.moc.go.th/api/exportharmonizecountries",
}
MAX_LIMIT = 10          # API บังคับเพดานไว้ที่ 10


def to_float(v) -> float:
    """ตัวเลขจาก API ส่งกลับมาเป็น string ต้องแปลงก่อนใช้"""
    try:
        return float(str(v).replace(",", "") or 0)
    except ValueError:
        return 0.0


def fetch_month(flow: str, year: int, month: int, hs_code: str) -> list[dict]:
    resp = requests.get(ENDPOINTS[flow],
                        params={"year": year, "month": month,
                                "hs_code": hs_code, "limit": MAX_LIMIT},
                        timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def main() -> None:
    ap = argparse.ArgumentParser(description="ดึงมูลค่าการค้า HS 8806 รายเดือนจากกระทรวงพาณิชย์")
    # default ต้องครอบคลุมทุกปีที่รายงานใช้ ไม่งั้นรันเปล่า ๆ แล้วเขียนทับ CSV
    # จะทำให้กราฟในรายงานเหลือน้อยปีกว่าข้อความรอบ ๆ โดยไม่มีอะไรเตือน
    ap.add_argument("--years", default="2022,2023,2024,2025",
                    help="ปี ค.ศ. คั่นด้วย comma (HS 8806 มีข้อมูลตั้งแต่ 2022)")
    ap.add_argument("--hs", default="8806", help="รหัส HS (2/4/6/8/11 หลัก)")
    ap.add_argument("--flows", default="import,export", help="import และ/หรือ export")
    args = ap.parse_args()

    years = [int(y.strip()) for y in args.years.split(",") if y.strip()]
    flows = [f.strip() for f in args.flows.split(",") if f.strip()]

    rows: list[dict] = []
    for flow in flows:
        for year in years:
            for month in range(1, 13):
                try:
                    recs = fetch_month(flow, year, month, args.hs)
                except Exception as e:
                    print(f"  [WARN] {flow} {year}-{month:02d}: {e}")
                    continue
                for r in recs:
                    rows.append({
                        "year": int(r.get("year", year)),
                        "month": int(r.get("month", month)),
                        "flow": flow,
                        "country_code": r.get("country_code"),
                        "country_en": r.get("country_name_en"),
                        "country_th": r.get("country_name_th"),
                        "quantity": to_float(r.get("quantity")),
                        "value_usd": to_float(r.get("value_usd")),
                        "value_baht": to_float(r.get("value_baht")),
                        "acc_value_usd": to_float(r.get("acc_value_usd")),
                        "acc_value_baht": to_float(r.get("acc_value_baht")),
                    })
                print(f"  {flow:<7} {year}-{month:02d}: {len(recs)} ประเทศ")
                time.sleep(0.5)

    if not rows:
        print("[WARN] ไม่พบข้อมูล — ตรวจสอบปี/รหัส HS "
              "(HS 8806 มีข้อมูลตั้งแต่ปี 2022)")
        return

    df = pd.DataFrame(rows)
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = PROC_DIR / f"moc_hs{args.hs}_monthly.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[OK] saved -> {csv_path.relative_to(PROJECT_ROOT)}  ({len(df)} แถว)")

    print(f"\n===== มูลค่ารายเดือน HS {args.hs} (USD) =====")
    monthly = df.groupby(["year", "month", "flow"])["value_usd"].sum().unstack(fill_value=0)
    for (year, month), r in monthly.iterrows():
        imp, exp = r.get("import", 0), r.get("export", 0)
        print(f"  {year}-{month:02d}   นำเข้า {imp:>13,.0f} | ส่งออก {exp:>13,.0f}")

    # ยอดรวมทั้งปีต้องรวมจาก value_usd ทั้ง 12 เดือน
    # ห้ามใช้ acc_* ของเดือนสุดท้ายเดี่ยว ๆ เพราะเพดาน limit=10 ทำให้ประเทศที่
    # หลุด top-10 ในเดือนนั้นหายไปทั้งยอดสะสม (ปี 2024 หายไป 776,088 USD)
    print(f"\n===== ยอดรวมทั้งปี (รวมจาก 12 เดือน) =====")
    annual = df.groupby(["year", "flow"])[["value_usd", "value_baht"]].sum()
    for year in sorted(df["year"].unique()):
        for flow in flows:
            if (year, flow) not in annual.index:
                continue
            r = annual.loc[(year, flow)]
            print(f"  {year} {flow:<7}: {r['value_usd']:>14,.0f} USD | {r['value_baht']:>18,.0f} บาท")
        if all((year, f) in annual.index for f in ("import", "export")):
            net = annual.loc[(year, "import"), "value_usd"] - annual.loc[(year, "export"), "value_usd"]
            print(f"  {year} {'net':<7}: {net:>14,.0f} USD  (นำเข้า - ส่งออก)")

    # เทียบยอดรวม 12 เดือน กับ acc ของเดือนสุดท้าย เพื่อดูว่าเพดาน limit ทำให้หายไปเท่าไร
    print(f"\n===== ผลของเพดาน limit=10 =====")
    for year in sorted(df["year"].unique()):
        for flow in flows:
            sub = df[(df["year"] == year) & (df["flow"] == flow)]
            if sub.empty:
                continue
            last = sub[sub["month"] == sub["month"].max()]
            acc_only = last["acc_value_usd"].sum()
            full = sub["value_usd"].sum()
            print(f"  {year} {flow:<7}: acc เดือนสุดท้าย {acc_only:>14,.0f} | "
                  f"รวม 12 เดือน {full:>14,.0f} | หายไป {full - acc_only:>11,.0f}")

    print(f"\n===== ประเทศคู่ค้าหลัก (รวมทุกเดือนที่ดึงมา) =====")
    for flow in flows:
        sub = df[df["flow"] == flow]
        if sub.empty:
            continue
        print(f"\n-- {flow.upper()} --")
        top = sub.groupby("country_en")["value_usd"].sum().sort_values(ascending=False).head(10)
        total = top.sum()
        for country, usd in top.items():
            share = usd / total * 100 if total else 0
            print(f"  {str(country)[:26]:<28} {usd:>14,.0f} USD  ({share:5.1f}%)")

    print("\n⚠️  limit สูงสุด 10 → ได้เฉพาะคู่ค้า top 10 ของแต่ละเดือน "
          "ยอดรวมจึงเป็นค่า 'อย่างน้อย'")


if __name__ == "__main__":
    main()
