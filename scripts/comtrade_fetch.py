# -*- coding: utf-8 -*-
"""
comtrade_fetch.py — ดึงมูลค่าการค้าโดรน (HS 8806) ของไทย จาก UN Comtrade API

ใช้คู่กับข้อมูลทะเบียน กสทช. (จำนวนเครื่อง) เพื่อให้ได้ภาพตลาดครบ:
    กสทช.     = ปริมาณ + ส่วนแบ่งแบรนด์
    Comtrade  = มูลค่าเป็น USD (market size จริง)

--- วิธีใช้ ---
    1) ใส่ API key ในไฟล์ .env ที่ root ของโปรเจกต์:
           COMTRADE_API_KEY=xxxxxxxx
       (สมัครฟรีที่ https://comtradedeveloper.un.org/)

    2) รัน:
           python scripts/comtrade_fetch.py                    # ยอดรวมนำเข้า+ส่งออก รายปี
           python scripts/comtrade_fetch.py --partners         # แยกตามประเทศคู่ค้า
           python scripts/comtrade_fetch.py --years 2022,2023,2024

--- ข้อควรรู้ ---
    * HS 8806 "Unmanned aircraft" เพิ่งถูกสร้างขึ้นในระบบ HS2022
      จึงมีข้อมูลตั้งแต่ปี 2022 เป็นต้นไปเท่านั้น
      ก่อนหน้านั้นโดรนถูกจัดอยู่ใน 8802 / 8525 ปนกับสินค้าอื่น
    * ถ้ายังไม่ใส่ key สคริปต์จะใช้ public preview endpoint ให้อัตโนมัติ
      (ใช้ได้ฟรีแต่จำกัด 500 แถว)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

# ให้ print ภาษาไทยได้บน Windows console (cp1252) โดยไม่ crash
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROC_DIR = PROJECT_ROOT / "data" / "processed"

# --- ค่าคงที่สำหรับ query ---
REPORTER_THAILAND = "764"   # รหัสประเทศไทย (UN M49)
CMD_DRONE = "8806"          # HS 8806 = Unmanned aircraft
PARTNER_WORLD = "0"         # 0 = รวมทุกประเทศ (World)

BASE_AUTH = "https://comtradeapi.un.org/data/v1/get/C/A/HS"
BASE_PREVIEW = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"

# สำคัญมาก! ถ้าไม่ใส่ classic ข้อมูลจะถูกแตกย่อยตาม mode of transport
# (mot 1000=อากาศ, 2000=เรือ, 3000=บก) ปนกับแถวยอดรวม -> เอาไปบวกกันจะ "นับซ้ำ"
# classic = คืนแถวยอดรวมสุทธิแถวเดียวต่อ ปี/flow/คู่ค้า
BREAKDOWN_MODE = "classic"

# ค่า placeholder ที่ถือว่า "ยังไม่ได้ใส่ key จริง"
PLACEHOLDERS = {"", "PASTE_YOUR_KEY_HERE", "your_key_here", "xxxxxxxx"}

FLOW_LABEL = {"M": "import", "X": "export"}


def load_api_key() -> str | None:
    """อ่าน API key จาก environment variable ก่อน แล้ว fallback ไปที่ไฟล์ .env

    ไม่ hardcode key ไว้ในโค้ดเด็ดขาด เพื่อไม่ให้หลุดตอน commit
    """
    key = os.environ.get("COMTRADE_API_KEY", "").strip()
    if key and key not in PLACEHOLDERS:
        return key

    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == "COMTRADE_API_KEY":
                value = value.strip().strip('"').strip("'")
                if value and value not in PLACEHOLDERS:
                    return value
    return None


def comtrade_get(params: dict, api_key: str | None, max_retries: int = 4) -> list[dict]:
    """ยิง request ไป UN Comtrade แล้วคืน list ของ record

    มี key   -> ใช้ endpoint เต็ม (ดึงได้เยอะ, rate limit สูง)
    ไม่มี key -> ใช้ public preview (จำกัด 500 แถว, rate limit ต่ำมาก)

    เจอ 429 จะรอแล้วลองใหม่แบบ exponential backoff
    """
    if api_key:
        url = BASE_AUTH
        # ส่ง key ทาง header ไม่ใส่ใน URL เพื่อไม่ให้ key ไปโผล่ใน log/browser history
        headers = {"Ocp-Apim-Subscription-Key": api_key}
    else:
        url = BASE_PREVIEW
        headers = {}

    for attempt in range(max_retries):
        resp = requests.get(url, params=params, headers=headers, timeout=90)

        if resp.status_code == 401:
            sys.exit("[ERROR] 401 Unauthorized — API key ไม่ถูกต้อง/หมดอายุ "
                     "ตรวจสอบ COMTRADE_API_KEY ในไฟล์ .env")
        if resp.status_code == 429:
            wait = 10 * (2 ** attempt)
            print(f"[WARN] 429 rate limit — รอ {wait}s แล้วลองใหม่ "
                  f"(ครั้งที่ {attempt + 1}/{max_retries})")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json().get("data", [])

    sys.exit("[ERROR] โดน rate limit ต่อเนื่อง — ลองใหม่ภายหลัง "
             "หรือใส่ API key เพื่อเพิ่มโควตา")


def fetch(years: list[str], by_partner: bool, api_key: str | None) -> pd.DataFrame:
    """ดึงข้อมูลการค้าโดรนของไทย คืนเป็น DataFrame ที่จัดระเบียบแล้ว

    ยิงทีละปี เพราะขอหลายปีพร้อมกันจะโดน 400 บน preview endpoint
    (endpoint แบบมี key รับหลายปีได้ แต่วนทีละปีใช้ได้กับทั้งสองแบบ)
    """
    # ไม่มี key = preview endpoint ซึ่ง rate limit ต่ำมาก ต้องเว้นจังหวะนานกว่า
    delay = 1.0 if api_key else 8.0
    all_records: list[dict] = []

    for i, year in enumerate(years):
        params = {
            "reporterCode": REPORTER_THAILAND,
            "period": year,
            "cmdCode": CMD_DRONE,
            "flowCode": "M,X",              # M = นำเข้า, X = ส่งออก
            "includeDesc": "True",          # ถ้าไม่ใส่ ชื่อประเทศจะกลับมาเป็น null
            "breakdownMode": BREAKDOWN_MODE,
        }
        # ไม่ระบุ partnerCode = ได้ผลแยกรายประเทศคู่ค้า
        if not by_partner:
            params["partnerCode"] = PARTNER_WORLD

        records = comtrade_get(params, api_key)
        print(f"  {year}: {len(records)} records")
        all_records.extend(records)

        if i < len(years) - 1:
            time.sleep(delay)

    if not all_records:
        print("[WARN] ไม่พบข้อมูล — HS 8806 มีข้อมูลตั้งแต่ปี 2022 เท่านั้น "
              "และปีล่าสุดอาจยังไม่ถูกรายงาน")
        return pd.DataFrame()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    tag = "partners" if by_partner else "world"
    raw_path = RAW_DIR / f"comtrade_hs8806_thailand_{tag}.json"
    raw_path.write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] saved raw JSON -> {raw_path.relative_to(PROJECT_ROOT)}  ({len(all_records)} records)")

    df = pd.DataFrame(all_records)
    tidy = pd.DataFrame({
        "year": df["refYear"],
        "flow": df["flowCode"].map(FLOW_LABEL).fillna(df["flowCode"]),
        "partner": df.get("partnerDesc"),
        "partner_code": df["partnerCode"],
        "value_usd": df["primaryValue"],
        "qty": df.get("qty"),
        "net_weight_kg": df.get("netWgt"),
    })

    if by_partner:
        # partnerCode 0 = "World" เป็น "ยอดรวม" ไม่ใช่ประเทศหนึ่ง
        # ถ้าปล่อยให้ปนอยู่ในตารางรายประเทศ เวลา groupby().sum() จะได้ยอด 2 เท่า
        # (ยอดรวมทั้งโลกดูได้จากโหมดปกติ ที่ไฟล์ ..._world.csv)
        tidy = tidy[tidy["partner_code"] != 0]
        # หมายเหตุ: partnerCode 764 = ไทยเอง คือการนำกลับเข้า/ส่งกลับ (re-import/re-export)
        # เป็นข้อมูลจริง ไม่ใช่ error จึงเก็บไว้

    return tidy.sort_values(["year", "flow", "value_usd"], ascending=[True, True, False])


def main() -> None:
    ap = argparse.ArgumentParser(description="ดึงข้อมูลการค้าโดรน HS 8806 ของไทยจาก UN Comtrade")
    ap.add_argument("--years", default="2022,2023,2024,2025",
                    help="ปีที่ต้องการ คั่นด้วย comma (HS 8806 มีข้อมูลตั้งแต่ 2022)")
    ap.add_argument("--partners", action="store_true",
                    help="แยกตามประเทศคู่ค้า แทนยอดรวมทั้งโลก")
    args = ap.parse_args()

    years = [y.strip() for y in args.years.split(",") if y.strip()]

    api_key = load_api_key()
    if api_key:
        print(f"[OK] พบ API key (ขึ้นต้นด้วย {api_key[:4]}...) -> ใช้ endpoint เต็ม")
    else:
        print("[WARN] ยังไม่พบ API key -> ใช้ public preview (จำกัด 500 แถว)\n"
              "       ใส่ key ได้ที่ไฟล์ .env :  COMTRADE_API_KEY=xxxxxxxx")

    df = fetch(years, args.partners, api_key)
    if df.empty:
        return

    PROC_DIR.mkdir(parents=True, exist_ok=True)
    tag = "partners" if args.partners else "world"
    csv_path = PROC_DIR / f"comtrade_hs8806_thailand_{tag}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[OK] saved CSV -> {csv_path.relative_to(PROJECT_ROOT)}\n")

    if args.partners:
        latest = df["year"].max()
        print(f"===== Top 15 partner countries ({latest}) =====")
        for flow in ("import", "export"):
            sub = df[(df["year"] == latest) & (df["flow"] == flow)].head(15)
            if sub.empty:
                continue
            print(f"\n-- {flow.upper()} --")
            for _, r in sub.iterrows():
                print(f"  {str(r['partner'])[:28]:<30} {r['value_usd']:>15,.0f} USD")
    else:
        print("===== Thailand drone trade, HS 8806 (USD) =====")
        pivot = df.pivot_table(index="year", columns="flow",
                               values="value_usd", aggfunc="sum").fillna(0)
        for year, row in pivot.iterrows():
            imp = row.get("import", 0)
            exp = row.get("export", 0)
            print(f"  {int(year)}:  import {imp:>15,.0f} | export {exp:>13,.0f} | net {imp - exp:>15,.0f}")


if __name__ == "__main__":
    main()
