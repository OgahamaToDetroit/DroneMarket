"""ดึงสถิตินำเข้า-ส่งออกจาก Data Catalog ของกรมศุลกากร (CKAN)

ทำไมต้องมีแหล่งนี้ทั้งที่มี MOC/Comtrade อยู่แล้ว
--------------------------------------------------
MOC กับ Comtrade ให้ HS 8806 เป็นก้อนเดียว แยกไม่ออกว่าเป็นโดรนเล่นหรือโดรนงาน
ศุลกากรให้ถึง **พิกัด 8 หลัก** ซึ่งแยกตามน้ำหนักวิ่งขึ้นสูงสุด (MTOW) และแยก
"บังคับด้วยรีโมตอย่างเดียว" (8806.2x) ออกจาก "อื่น ๆ" (8806.9x) ได้

⚠️ ไม่ใช่แหล่งอิสระ — เป็นข้อมูลชุดเดียวกับที่ MOC/Comtrade รับไปเผยแพร่ต่อ
   ยอดนำเข้าปี 2568 ตรงกับ MOC ทุกบาท (6,804,347,867) → ห้ามใช้ cross-check กันเอง
   คุณค่าอยู่ที่ "ความละเอียด" ไม่ใช่ "การยืนยัน"

กับดักที่เจอจริงตอนใช้งาน
--------------------------
1. **CIF ปะทะ FOB — กับดักที่ร้ายที่สุด**
   ขานำเข้าบันทึกแบบ CIF (รวมค่าขนส่ง+ประกัน) ขาส่งออกบันทึกแบบ FOB (ไม่รวม)
   เอา `นำเข้า − ส่งออก` ตรง ๆ จะได้ส่วนต่างที่จริง ๆ แล้วเป็นแค่ค่าระวาง
   ตัวอย่างจริง: 88069300 ปี 2568 ส่วนต่างมูลค่า **+35.7 ล้านบาท** แต่ส่วนต่าง
   จำนวน **−164 ชิ้น** (ของออกมากกว่าเข้า!) → 35.7 ล้านนั้นไม่ใช่ตลาดในประเทศ
   → สคริปต์นี้จึงรายงานส่วนต่างทั้งมูลค่าและจำนวน แล้วตัดสินด้วย GATE ด้านล่าง

2. **คอลัมน์ TRF ในไฟล์อ้างอิงพิกัด (rtc_03_03) มีช่องว่างนำหน้า**
   `df.TRF.str.startswith("8806")` จะได้ 0 แถวถ้าไม่ .str.strip() ก่อน

3. **ไฟล์อ้างอิงพิกัดให้แต่ข้อความชั้นล่าง ไม่ให้หัวข้อกลุ่ม**
   จะเห็นแค่ "มีน้ำหนักวิ่งขึ้นสูงสุดมากกว่า 7 กก. แต่ไม่มากกว่า 25 กก." เหมือนกัน
   ทั้ง 88062300 และ 88069300 — สิ่งที่แยกสองตัวนี้คือหัวข้อกลุ่มในโครงสร้าง HS2022
   ("Other, for remote-controlled flight only:" กับ "Other:") ซึ่ง **ไม่มีในไฟล์**
   ป้ายกำกับใน GROUP_LABEL จึงมาจากโครงสร้าง HS ทางการ ไม่ได้มาจากข้อมูล

4. **บางปีมีทั้งไฟล์รายปีและไฟล์รายเดือน** — ถ้าเอามารวมกันหมดจะนับซ้ำ
   กติกา: ปีไหนมีไฟล์รายปีให้ใช้รายปี ปีไหนไม่มี (เช่นปีปัจจุบัน) จึงใช้รายเดือน

5. **ปีในชื่อไฟล์เป็น พ.ศ. แต่เป็นปีปฏิทิน ไม่ใช่ปีงบประมาณ**
   ยืนยันแล้วโดยเทียบกับ MOC: ปี 2568 = ปฏิทิน 2025 ตรงกันทุกบาท
   (ต่างจาก e-GP ที่เป็นปีงบประมาณ — อย่าเอามาเทียบปีต่อปีโดยไม่ปรับ)

6. **ยอดส่งออกไม่ตรงกับ MOC −0.2% และต่างผิดทิศ** (MOC ที่ตัด top-10 กลับสูงกว่า
   ตัวเต็มของศุลกากร) ยังอธิบายไม่ได้ ณ 30 ก.ค. 2569 — บันทึกไว้ อย่ากลบ
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CKAN = "https://catalog.customs.go.th/api/3/action/"
ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed"
TMP_DIR = Path(tempfile.gettempdir()) / "customs_cache"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "DroneMarket-research/1.0"

# ชุดข้อมูลที่ใช้ — ดูรายการเต็ม 29 ชุดได้จาก CKAN action/package_list
DATASETS = {
    "by_code": {"import": "ctm_06_09", "export": "ctm_06_10"},      # 8 หลัก + รหัสสถิติ 11 หลัก
    "by_country": {"import": "ctm_06_11", "export": "ctm_06_12"},   # 8 หลัก × ประเทศ (ไม่มีเพดาน)
}
TARIFF_REF = "rtc_03_03"        # ข้อความกำกับพิกัด 8 หลัก

# หัวข้อกลุ่มตามโครงสร้าง HS2022 — ไม่มีในไฟล์ของศุลกากร ต้องกำกับเอง (ดูกับดักข้อ 3)
#   8806.10          = ที่ออกแบบสำหรับการขนส่งผู้โดยสาร
#   8806.21-.29      = "Other, for remote-controlled flight only"  → บังคับด้วยรีโมตอย่างเดียว
#   8806.91-.99      = "Other"                                     → ที่เหลือ (บินตามแผนที่วางไว้ได้)
GROUP_LABEL = {"1": "โดยสาร", "2": "รีโมตอย่างเดียว", "9": "ไม่ใช่รีโมตอย่างเดียว"}
MTOW_LABEL = {
    "1": "≤250g", "2": "250g-7kg", "3": "7-25kg", "4": "25-150kg", "9": "อื่นๆ", "0": "-",
}

# GATE: จะเรียกส่วนต่างว่า "อุปสงค์ในประเทศ" ได้ต่อเมื่อผ่านครบทั้ง 3 ข้อ
#   (1) ส่วนต่างมูลค่าเป็นบวก  (2) ส่วนต่างจำนวนเป็นบวก
#   (3) ส่วนต่างมูลค่า > MIN_RESIDUAL_SHARE ของขานำเข้า — กันไม่ให้ค่าระวาง CIF/FOB
#       ซึ่งอยู่ราว 2-5% ของมูลค่า ถูกอ่านเป็นตลาด
MIN_RESIDUAL_SHARE = 0.10


def ckan(action: str, **params):
    r = SESSION.get(CKAN + action, params=params, timeout=120)
    r.raise_for_status()
    js = r.json()
    if not js.get("success"):
        raise RuntimeError(f"CKAN {action} ไม่สำเร็จ: {js}")
    return js["result"]


def pick_resources(dataset: str, years: list[int]) -> list[tuple[int, str, str]]:
    """เลือกไฟล์ CSV ของปีที่ต้องการ — คืน (ปี, ชื่อ, url)

    ปีไหนมีไฟล์รายปีให้ใช้รายปีอย่างเดียว ปีไหนไม่มีจึงใช้ไฟล์รายเดือนทั้งหมด
    (ดูกับดักข้อ 4 — ถ้าเอามารวมกันหมดจะนับซ้ำ)
    """
    res = [r for r in ckan("package_show", id=dataset)["resources"]
           if (r.get("format") or "").upper() == "CSV"]
    out: list[tuple[int, str, str]] = []
    for y in years:
        tag = str(y)
        same_year = [r for r in res if tag in (r.get("name") or "")]
        annual = [r for r in same_year if "(" not in (r.get("name") or "")]
        chosen = annual if annual else same_year
        if not chosen:
            print(f"   ⚠️  {dataset}: ไม่พบไฟล์ปี {y}")
            continue
        if not annual:
            print(f"   ℹ️  {dataset} ปี {y}: ไม่มีไฟล์รายปี ใช้ไฟล์รายเดือน {len(chosen)} ไฟล์")
        out += [(y, r["name"], r["url"]) for r in chosen]
    return out


def fetch_csv(url: str, name: str) -> pd.DataFrame:
    """โหลดลงไฟล์ชั่วคราวก่อนแล้วค่อยอ่าน

    บทเรียนจาก e-GP: ถ้าแกะข้อมูลไปพร้อมกับที่สตรีมอยู่ แล้วแกะช้ากว่าที่เซิร์ฟเวอร์ส่ง
    ซ็อกเก็ตจะค้างจนโดนตัดกลางคัน — ไฟล์ที่นี่เล็ก (20-120 MB) โหลดก่อนจึงคุ้มกว่า
    """
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    cache = TMP_DIR / (str(abs(hash(url))) + ".csv")
    if not cache.exists() or cache.stat().st_size == 0:
        with SESSION.get(url, timeout=600, stream=True) as r:
            r.raise_for_status()
            with open(cache, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    mb = cache.stat().st_size / 1048576
    print(f"   · {name} ({mb:,.1f} MB)")
    return pd.read_csv(cache, dtype=str, encoding="utf-8-sig")


def normalise(df: pd.DataFrame, flow: str, year: int) -> pd.DataFrame:
    """ปรับชื่อคอลัมน์ให้เหมือนกันทั้งขาเข้าและขาออก

    ไฟล์ขาเข้าใช้ 'รหัสประเทศกำเนิด' ขาออกใช้ 'รหัสประเทศปลายทาง'
    และคอลัมน์มูลค่าก็ชื่อคนละอย่าง — จึงจับจากตำแหน่งสุดท้ายแทนการอ้างชื่อ
    """
    cols = df.columns.tolist()
    ren = {cols[0]: "ปี", cols[1]: "เดือน", cols[2]: "พิกัด8", cols[3]: "รหัสสถิติ",
           cols[4]: "หน่วย", cols[5]: "คำอธิบาย", cols[6]: "คำอธิบาย_en",
           cols[7]: "ปริมาณ", cols[-1]: "มูลค่าบาท"}
    country = [c for c in cols if "ประเทศ" in c]
    if country:
        ren[country[0]] = "ประเทศ"
    df = df.rename(columns=ren)
    keep = [c for c in ["ปี", "เดือน", "พิกัด8", "รหัสสถิติ", "หน่วย", "คำอธิบาย",
                        "ประเทศ", "ปริมาณ", "มูลค่าบาท"] if c in df.columns]
    df = df[keep].copy()
    df["ทิศทาง"] = flow
    df["ปี"] = year
    for c in ("ปริมาณ", "มูลค่าบาท"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["เดือน"] = pd.to_numeric(df["เดือน"], errors="coerce")
    return df


def collect(kind: str, years: list[int], hs: str) -> pd.DataFrame:
    frames = []
    for flow, ds in DATASETS[kind].items():
        print(f"  {kind} / {flow} ({ds})")
        for year, name, url in pick_resources(ds, years):
            raw = fetch_csv(url, name)
            hs_col = raw.columns[2]
            sub = raw[raw[hs_col].astype(str).str.strip().str.startswith(hs, na=False)]
            if len(sub):
                frames.append(normalise(sub, flow, year))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def tariff_labels(hs: str) -> pd.DataFrame:
    res = [r for r in ckan("package_show", id=TARIFF_REF)["resources"]
           if (r.get("format") or "").upper() == "CSV"][0]
    txt = SESSION.get(res["url"], timeout=180).content.decode("utf-8-sig", "replace")
    ref = pd.read_csv(io.StringIO(txt), dtype=str)
    ref["TRF"] = ref["TRF"].str.strip()          # ⚠️ กับดักข้อ 2 — มีช่องว่างนำหน้า
    ref = ref[ref.TRF.str.startswith(hs, na=False)][["TRF", "TRFDSC"]]
    ref.columns = ["พิกัด8", "คำอธิบายทางการ"]
    ref["กลุ่ม"] = [GROUP_LABEL.get(c[4], "?") for c in ref["พิกัด8"]]
    ref["ชั้นน้ำหนัก"] = [MTOW_LABEL.get(c[5], "?") for c in ref["พิกัด8"]]
    ref["ชนิด"] = ref["กลุ่ม"] + " " + ref["ชั้นน้ำหนัก"]
    return ref


def build_balance(by_code: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """ตารางเทียบเข้า-ออกรายพิกัด พร้อมผล GATE"""
    g = (by_code.groupby(["ปี", "พิกัด8", "ทิศทาง"], as_index=False)
                .agg(มูลค่าบาท=("มูลค่าบาท", "sum"), ปริมาณ=("ปริมาณ", "sum")))
    piv = g.pivot_table(index=["ปี", "พิกัด8"], columns="ทิศทาง",
                        values=["มูลค่าบาท", "ปริมาณ"], fill_value=0)
    piv.columns = [f"{a}_{b}" for a, b in piv.columns]
    piv = piv.reset_index()
    for c in ["มูลค่าบาท_import", "มูลค่าบาท_export", "ปริมาณ_import", "ปริมาณ_export"]:
        if c not in piv:
            piv[c] = 0.0
    piv = piv.merge(ref[["พิกัด8", "ชนิด", "คำอธิบายทางการ"]], on="พิกัด8", how="left")

    piv["ส่วนต่างมูลค่า"] = piv["มูลค่าบาท_import"] - piv["มูลค่าบาท_export"]
    piv["ส่วนต่างปริมาณ"] = piv["ปริมาณ_import"] - piv["ปริมาณ_export"]
    piv["ratio_ส่งออกต่อนำเข้า"] = (piv["มูลค่าบาท_export"] /
                                    piv["มูลค่าบาท_import"].replace(0, pd.NA))
    share = piv["ส่วนต่างมูลค่า"] / piv["มูลค่าบาท_import"].replace(0, pd.NA)
    piv["ผ่าน_GATE"] = ((piv["ส่วนต่างมูลค่า"] > 0) & (piv["ส่วนต่างปริมาณ"] > 0)
                        & (share > MIN_RESIDUAL_SHARE))
    # อย่าเขียนคำว่า "อุปสงค์ในประเทศ" ลงในแถวที่ไม่ผ่าน GATE — ดูกับดักข้อ 1
    piv["อุปสงค์ในประเทศ_บาท"] = piv["ส่วนต่างมูลค่า"].where(piv["ผ่าน_GATE"])
    return piv.sort_values(["ปี", "มูลค่าบาท_import"], ascending=[True, False])


def month_coverage(by_code: pd.DataFrame) -> dict[int, int]:
    """ปีไหนมีข้อมูลกี่เดือน — ปีที่ยังไม่ครบ 12 เดือนห้ามเอาไปเทียบกับปีเต็ม"""
    return by_code.groupby("ปี")["เดือน"].nunique().to_dict()


def floor_estimate(bal: pd.DataFrame, year: int) -> dict:
    """ขอบล่างของอุปสงค์ในประเทศ — **ประมาณการ ไม่ใช่การวัด** ต้องเขียนกำกับเสมอ

    ปัญหาที่ฟังก์ชันนี้แก้: บรรทัด "วัดได้" นับพิกัดที่ไม่ผ่าน GATE เป็นศูนย์
    ทั้งที่อุปสงค์ของคลาสนั้นไม่ได้หายไปไหน พอชุดพิกัดที่ผ่าน GATE เปลี่ยนทุกปี
    ตัวเลข "วัดได้" จึงเทียบข้ามปีไม่ได้ ตัวนี้ให้พื้นที่อุดรูบางส่วนคืน

    กติกา — ต้องสม่ำเสมอทุกพิกัด ห้ามหยิบปีมาใช้ตามใจ:
      1. พิกัดที่ไม่ผ่าน GATE ให้ยกค่าที่เคยวัดได้จาก **ปีล่าสุดที่ ≤ ปีเป้าหมาย**
         ⚠️ ห้ามยกจากปีที่ใหม่กว่าปีเป้าหมาย ปีท้าย ๆ ของชุดข้อมูลมักยังไม่ครบ 12 เดือน
         กติกาข้อนี้เคยพลาดมาแล้ว — SOURCES.md เคยเขียน 88062200 = 76.4 ล้าน
         ซึ่งเป็นค่าปี 2569 (มีแค่ ม.ค.-พ.ค.) เอามาเป็นพื้นของปี 2568
      2. ครอบด้วยยอดนำเข้าจริงของพิกัดนั้นในปีเป้าหมาย — ขอบล่างจะโตเกินของที่
         เข้ามาจริงไม่ได้ (88069200 ปี 2568 เคยวัดได้ 7.8 ล้าน แต่ปีนั้นนำเข้าแค่ 7.4)
      3. พิกัดที่ยังไม่เคยผ่าน GATE เลยจนถึงปีนั้น ยกมาไม่ได้ = นับ 0 แล้วรายงานไว้
         ว่าเหลือพิกัดไหน เพื่อให้เห็นว่าขอบล่างนี้ยังอุดรูได้ไม่หมด
    """
    d = bal[bal["ปี"] == year]
    measured = d.loc[d["ผ่าน_GATE"], "อุปสงค์ในประเทศ_บาท"].sum()
    carried, sources, no_basis = 0.0, [], []
    for _, r in d[~d["ผ่าน_GATE"]].iterrows():
        past = bal[(bal["พิกัด8"] == r["พิกัด8"]) & (bal["ปี"] <= year) & bal["ผ่าน_GATE"]]
        if past.empty:
            no_basis.append(str(r["พิกัด8"]))
            continue
        src = past.loc[past["ปี"].idxmax()]
        v = min(src["อุปสงค์ในประเทศ_บาท"], r["มูลค่าบาท_import"])   # กติกาข้อ 2
        carried += v
        sources.append((str(r["พิกัด8"]), int(src["ปี"]), v))
    return {"วัดได้": measured, "ยกมา": carried, "ขอบล่าง": measured + carried,
            "ที่มา": sources, "ยกไม่ได้": no_basis}


def report(bal: pd.DataFrame, years: list[int], months: dict[int, int] | None = None) -> None:
    months = months or {}
    for y in years:
        d = bal[bal["ปี"] == y]
        if d.empty:
            continue
        nm = months.get(y)
        partial = f"  ⚠️ มีข้อมูลแค่ {nm}/12 เดือน" if nm and nm < 12 else ""
        print(f"\n{'='*104}\nปี {y} (ปฏิทิน {y - 543}) — หน่วยล้านบาท{partial}\n{'='*104}")
        show = pd.DataFrame({
            "พิกัด": d["พิกัด8"],
            "ชนิด": d["ชนิด"].fillna("?"),
            "นำเข้า": (d["มูลค่าบาท_import"] / 1e6).round(0),
            "ส่งออก": (d["มูลค่าบาท_export"] / 1e6).round(0),
            "ส่ง/นำ": d["ratio_ส่งออกต่อนำเข้า"].round(2),
            "ชิ้นเข้า": d["ปริมาณ_import"].astype("int64"),
            "ชิ้นออก": d["ปริมาณ_export"].astype("int64"),
            "GATE": d["ผ่าน_GATE"].map({True: "ผ่าน", False: "— ของผ่าน"}),
        })
        print(show.to_string(index=False))
        ok, bad = d[d["ผ่าน_GATE"]], d[~d["ผ่าน_GATE"]]
        total_imp = d["มูลค่าบาท_import"].sum()
        hole = bad["มูลค่าบาท_import"].sum()
        print(f"\n  นำเข้ารวม {total_imp:>18,.0f} บาท")
        print(f"  ส่งออกรวม {d['มูลค่าบาท_export'].sum():>18,.0f} บาท")
        print(f"  อุปสงค์ในประเทศที่ **วัดได้** {ok['อุปสงค์ในประเทศ_บาท'].sum():>15,.0f} บาท"
              f"  [{len(ok)}/{len(d)} พิกัด]")
        print(f"  ยอดนำเข้าที่อยู่ในพิกัด **วัดไม่ได้** {hole:>13,.0f} บาท"
              f"  ({hole / total_imp * 100:.1f}% ของขานำเข้า)")
        if len(bad):
            print(f"  ⚠️ พิกัดที่วัดไม่ได้ (ของผ่าน/ติดค่าระวาง CIF-FOB): "
                  f"{', '.join(str(x) for x in bad['พิกัด8'])}")

        fe = floor_estimate(bal, y)
        if fe["ที่มา"] or fe["ยกไม่ได้"]:
            print(f"\n  ~ ขอบล่าง (ประมาณการ ไม่ใช่การวัด) {fe['ขอบล่าง']:>12,.0f} บาท"
                  f"  = วัดได้ + ยกของเก่ามา {fe['ยกมา']:,.0f}")
            for code, sy, v in fe["ที่มา"]:
                print(f"      · {code} ยกจากปี {sy} = {v:>15,.0f}")
            if fe["ยกไม่ได้"]:
                print(f"      · ยกมาไม่ได้ ไม่เคยผ่าน GATE เลย: {', '.join(fe['ยกไม่ได้'])}")
            if nm and nm < 12:
                print(f"      ⚠️ ปีนี้มีแค่ {nm} เดือน แต่ค่าที่ยกมาเป็นของปีเต็ม → ขอบล่างสูงเกินจริง")


def main() -> None:
    ap = argparse.ArgumentParser(description="ดึงสถิติการค้าจาก Data Catalog กรมศุลกากร")
    ap.add_argument("--years", default="2565,2566,2567,2568,2569",
                    help="ปี พ.ศ. คั่นด้วยคอมมา (ข้อมูลมีตั้งแต่ 2560) — เป็นปีปฏิทิน ไม่ใช่ปีงบ")
    ap.add_argument("--hs", default="8806", help="พิกัดที่ต้องการ (ค่าตั้งต้น 8806 = อากาศยานไร้คนขับ)")
    ap.add_argument("--skip-country", action="store_true",
                    help="ข้ามไฟล์รายประเทศ (ไฟล์ใหญ่ ~120 MB/ปี) เอาแค่รายพิกัด")
    ap.add_argument("--from-cache", action="store_true",
                    help="วิเคราะห์ซ้ำจาก CSV เดิมใน data/processed ไม่โหลดใหม่ "
                         "(ใช้ตอนแก้ส่วนวิเคราะห์/รายงาน — โหลดใหม่กินแบนด์วิดท์ ~2.5 GB)")
    args = ap.parse_args()

    years = [int(y) for y in args.years.split(",")]
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    print(f"กรมศุลกากร · พิกัด {args.hs} · ปี {years}\n")

    if args.from_cache:
        p1 = PROC_DIR / f"customs_hs{args.hs}_by_code.csv"
        p3 = PROC_DIR / f"customs_hs{args.hs}_balance.csv"
        missing = [p for p in (p1, p3) if not p.exists()]
        if missing:
            raise SystemExit("[STOP] --from-cache ต้องมีไฟล์เดิมก่อน ขาด: "
                             + ", ".join(str(p.relative_to(ROOT)) for p in missing))
        by_code = pd.read_csv(p1, encoding="utf-8-sig")
        bal = pd.read_csv(p3, encoding="utf-8-sig")
        # CSV เก็บ GATE เป็นข้อความ "True"/"False" — ถ้าไม่บังคับชนิด ทุกแถวจะกลายเป็นจริง
        bal["ผ่าน_GATE"] = bal["ผ่าน_GATE"].astype(str).str.lower().eq("true")

        # โหมดนี้ไม่ได้แตะกรมศุลกากรเลย จึงไม่มีรายชื่อไฟล์ต้นทางให้พิมพ์เหมือนรันเต็ม
        # ต้องบอกให้ชัดว่าอ่านจากอะไร ลงวันที่ไหน ไม่งั้น _out.txt จะดูเหมือนรันสด
        cov = month_coverage(by_code)
        print("[cache] วิเคราะห์ซ้ำจาก CSV เดิม ไม่ได้โหลดใหม่ "
              "— ตัวเลขเป็นชุดเดียวกับรอบที่ดึงข้อมูลจริงครั้งล่าสุด")
        for p, df in ((p1, by_code), (p3, bal)):
            ts = dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"   · {p.name:<32} {len(df):>4,} แถว · แก้ล่าสุด {ts}")
        print("   · ปีที่มีข้อมูล: "
              + "  ".join(f"{y}({cov.get(y, 0)} ด.)" for y in sorted(cov)))
        print("   ⚠️ รายชื่อไฟล์ต้นทางของกรมศุลกากรอยู่ในผลรันเต็มรอบก่อน (ดู git log ของไฟล์นี้)")
        print("      ถ้าต้องการข้อมูลใหม่จากต้นทาง ให้รันโดยไม่ใส่ --from-cache")
        report(bal, years, cov)
        epilogue()
        return

    print("[1/3] รายพิกัด 8 หลัก + รหัสสถิติ")
    by_code = collect("by_code", years, args.hs)
    if by_code.empty:
        raise SystemExit(f"[STOP] ไม่พบข้อมูลพิกัด {args.hs} เลย — ตรวจว่าพิกัดถูกต้องไหม")
    p1 = PROC_DIR / f"customs_hs{args.hs}_by_code.csv"
    by_code.to_csv(p1, index=False, encoding="utf-8-sig")
    print(f"  → {p1.relative_to(ROOT)} ({len(by_code):,} แถว)")

    print("\n[2/3] ข้อความกำกับพิกัด")
    ref = tariff_labels(args.hs)
    print(f"  → พบ {len(ref)} พิกัด")

    if not args.skip_country:
        print("\n[3/3] รายพิกัด × ประเทศ")
        by_country = collect("by_country", years, args.hs)
        if not by_country.empty:
            p2 = PROC_DIR / f"customs_hs{args.hs}_by_country.csv"
            by_country.to_csv(p2, index=False, encoding="utf-8-sig")
            print(f"  → {p2.relative_to(ROOT)} ({len(by_country):,} แถว)")
    else:
        print("\n[3/3] ข้ามไฟล์รายประเทศ (--skip-country)")

    bal = build_balance(by_code, ref)
    p3 = PROC_DIR / f"customs_hs{args.hs}_balance.csv"
    bal.to_csv(p3, index=False, encoding="utf-8-sig")
    print(f"\n  → {p3.relative_to(ROOT)} (ตารางเทียบเข้า-ออก + ผล GATE)")

    report(bal, years, month_coverage(by_code))
    epilogue()


def epilogue() -> None:
    print(f"""
{'='*104}
⚠️  อ่านตัวเลขข้างบนอย่างไรไม่ให้ผิด
{'='*104}
  · นำเข้าเป็น CIF (รวมค่าขนส่ง+ประกัน) ส่งออกเป็น FOB (ไม่รวม)
    "นำเข้า − ส่งออก" จึงมีค่าระวางปนอยู่เสมอ ~2-5% ของมูลค่า
  · พิกัดที่ไม่ผ่าน GATE = แยกไม่ออกว่าเป็นอุปสงค์จริงหรือค่าระวางของสินค้าผ่าน
    ให้เขียนว่า "วัดไม่ได้" ห้ามเขียนเป็นตัวเลข

  🚨 ห้ามเอาบรรทัด "วัดได้" มาเทียบข้ามปีแล้วสรุปว่าตลาดโตหรือนิ่ง
     เพราะแต่ละปีมีพิกัดหลุด GATE ไม่เท่ากัน = ฐานที่เอามารวมคนละชุด
     ถ้าปีไหนของผ่านลามเข้าไปในพิกัดเพิ่ม ตัวเลข "วัดได้" จะลดลงเองโดยที่
     อุปสงค์จริงไม่ได้ลด ให้ดูบรรทัด "วัดไม่ได้" ควบคู่เสมอ
     ตัวอย่าง: 88062200 (โดรน 250g-7kg ซึ่งเป็นเซกเมนต์ผู้บริโภคที่ใหญ่ที่สุด)
     ผ่าน GATE ปี 2565 แต่หลุดปี 2566-2568 — ไม่ได้แปลว่าอุปสงค์หายไป

  · บรรทัด "ขอบล่าง" เป็น**ประมาณการ ไม่ใช่การวัด** — เอาค่าที่พิกัดนั้นเคยวัดได้
    ครั้งล่าสุด (ในปีที่ไม่ใหม่กว่าปีเป้าหมาย) มาอุดรู แล้วครอบด้วยยอดนำเข้าจริงของปีนั้น
    ถ้าจะอ้างตัวเลขนี้ **ต้องเขียนกำกับว่าเป็นการประมาณทุกครั้ง** และยังเทียบข้ามปีไม่ได้
    เพราะจำนวนพิกัดที่ต้องอุดไม่เท่ากันในแต่ละปี

  · แหล่งนี้เป็นข้อมูลชุดเดียวกับ MOC/Comtrade — ห้ามใช้ยืนยันซึ่งกันและกัน
""")


if __name__ == "__main__":
    main()
