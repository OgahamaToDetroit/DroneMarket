# -*- coding: utf-8 -*-
"""
ics_market_position.py — ตำแหน่งของ iCreativeSystems (ICS) ในตลาดโดรนไทย

บริษัท: ICS = บจก.ไอครีเอทีฟซิสเตมส์ (iCreativeSystems) · icsco.ai · โคราช · ตั้งปี 2017

══════════════════════════════════════════════════════════════════════════
ICS ทำอะไร — **ไม่ใช่ร้านขายโดรน**
══════════════════════════════════════════════════════════════════════════
  1. **ผู้ผลิตอากาศยาน VTOL/tiltrotor ของตัวเอง**
     VERTIX VL260 · VERTIX VL240 · VILVERIN VL340 · XTRIX VL390 ·
     VOXEL MX · AVIX GN220 eVTOL · AD200 Transport UAV
  2. **ผู้รับจ้างบินสำรวจ/ทำแผนที่** ความละเอียดระดับเซนติเมตร (photogrammetry)
     ลูกค้าเป้าหมายที่เว็บระบุ: วิศวกรรม · เหมืองแร่ · ผังเมือง · เกษตร · งานตรวจสอบ
  3. **ตัวแทนจำหน่ายอุปกรณ์ทดสอบการบิน — นำเข้ามาขาย ไม่ได้ผลิตเอง**
     อุโมงค์ลม 4 ขนาด · Flight/Thrust Stand 15/50/150/500
     ⚠️ เคยบันทึกผิดไว้ว่า ICS ผลิตอุปกรณ์กลุ่มนี้เอง — **ไม่จริง** เป็นของนำเข้า
     (หน้า About Us ระบุว่าผลิตเฉพาะอากาศยานกับระบบอัตโนมัติ ไม่มีอุปกรณ์ทดสอบ)
  4. คอร์สอบรม / รับเป็นที่ปรึกษา

**ไม่ทำงานพ่นยาเกษตรแล้ว** — หน้า About Us เอ่ยถึงระบบพ่นปุ๋ย/ยาอัตโนมัติในเชิง
ประวัติบริษัท แต่หลักฐาน 4 ทางชี้ว่าเลิกไปแล้ว: หน้าสินค้า 12 รายการไม่มีโดรนพ่นยา ·
ทะเบียน กสทช. ไม่มีมัลติโรเตอร์พ่นยา · สัญญาภาครัฐ 3 งานไม่มีงานพ่นยา ·
หน้าแรกพาดหัวว่า DRONE SURVEYING AND AERIAL MAPPING
→ **จึงตัดสินใจไม่ดึงข้อมูลพื้นที่เพาะปลูกของ สศก.** เพราะเป็นข้อมูลสำหรับ
  ประเมินตลาดพ่นยา ตอบผิดคำถาม (ตัดสินใจ 30 ก.ค. 2569)

⚠️ ข้อมูลข้างบนมาจาก **เว็บของบริษัทเอง** = "สิ่งที่บริษัทพูดถึงตัวเอง"
   ยังไม่ได้ยืนยันกับแหล่งอิสระ สคริปต์นี้จึงตรวจเฉพาะส่วนที่พิสูจน์ได้จาก
   ข้อมูลราชการ คือทะเบียน กสทช. และสัญญาจัดซื้อจัดจ้าง e-GP

══════════════════════════════════════════════════════════════════════════
สิ่งที่ยืนยันได้จากข้อมูลราชการแล้ว (ณ 30 ก.ค. 2569)
══════════════════════════════════════════════════════════════════════════
**ทะเบียน กสทช. — แบรนด์ "ICS" 15 ลำ** (0.0073% ของทะเบียนทั้งประเทศ)
    รุ่น    : Vertix VL260 (5) · Vilverin VL340 (4) · AVIX GN220 eVTOL (3) ·
              Vertix VL240 (2) · Voxel MX (1)
    จังหวัด : โคราช 5 · กรุงเทพฯ 5 · บุรีรัมย์ 2 · ปทุมธานี 2 · นนทบุรี 1

    📌 รุ่นบนเว็บกับรุ่นที่จดทะเบียนไม่ตรงกันทั้งหมด:
       บนเว็บแต่ไม่มีในทะเบียน → XTRIX VL390 · AD200 Transport UAV
       ในทะเบียนแต่ไม่มีบนเว็บ → AVIX GN220 eVTOL · Vertix VL240

**สัญญาภาครัฐ e-GP — ชนะ 3 งาน** จาก 4,266 โครงการโดรนที่ดึงมา (ปีงบ 2558-2568)
    ปีงบ 2564 ·     89,986 บาท · มทส. (โคราช) — อุปกรณ์ประกอบการอบรมหลักสูตรโดรนอัตโนมัติ
    ปีงบ 2566 ·  9,890,000 บาท · มจพ. (กรุงเทพฯ) — ชุดปฏิบัติการระบบอากาศยานไร้คนขับ
                                  (e-bidding แข่งขัน ชนะที่ 99.4% ของงบ)
    ปีงบ 2567 ·    400,000 บาท · กรมชลประทาน — จ้างบินสำรวจ+ทำแผนที่ ที่ลำปาง
                                  (วิธีเฉพาะเจาะจง = มีชื่อในสายตาแล้ว)
    → ครบทั้งสามขา: ขายของ · ขายบริการ · อบรม

--- ต้องมีไฟล์เหล่านี้ก่อน ---
    data/raw/drone_data.xlsx              (กสทช. — ดูลิงก์ใน SOURCES.md)
    data/processed/egp_drone_projects.csv (รันสคริปต์ egp_drone_procurement.py ก่อน)

--- วิธีใช้ ---
    python scripts/ics_market_position.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
NBTC = ROOT / "data" / "raw" / "drone_data.xlsx"
EGP = ROOT / "data" / "processed" / "egp_drone_projects.csv"

# ชื่อบริษัทในทะเบียนราชการสะกดต่างจากชื่อการค้า — ต้องใช้ชื่อไทยที่จดทะเบียนไว้
ICS_WINNER = "ไอครีเอทีฟซิสเตมส์"
ICS_BRAND = "ICS"

# งานสำรวจ/ทำแผนที่ = เนื้อธุรกิจบริการของ ICS
# จับจากชื่อโครงการ ไม่ใช่ช่องวัตถุประสงค์ เพราะช่องนั้นเชื่อไม่ได้ (ดูหมายเหตุท้ายไฟล์)
SURVEY_PAT = ("สำรวจ|แผนที่|รังวัด|ภาพถ่ายทางอากาศ|photogram|orthophoto|"
              "ภูมิสารสนเทศ|ประทานบัตร")

# หน่วยงานความมั่นคง — ต้องแยกออก ไม่งั้นดีลทหารระดับพันล้านจะกลบตลาดพลเรือนหมด
MIL_PAT = ("กองทัพ|กองบัญชาการ|สถาบันเทคโนโลยีป้องกัน|สำนักงานตำรวจ|"
           "ศูนย์อำนวยการรักษาผลประโยชน์")

ISAN = ["นครราชสีมา", "ขอนแก่น", "อุบลราชธานี", "อุดรธานี", "บุรีรัมย์", "สุรินทร์",
        "ศรีสะเกษ", "ร้อยเอ็ด", "ชัยภูมิ", "สกลนคร", "กาฬสินธุ์", "มหาสารคาม", "เลย",
        "หนองคาย", "นครพนม", "ยโสธร", "หนองบัวลำภู", "อำนาจเจริญ", "บึงกาฬ", "มุกดาหาร"]


def section(title: str) -> None:
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


def part_nbtc() -> None:
    section("1) ICS ในทะเบียน กสทช. — อากาศยานที่จดทะเบียนจริง")
    if not NBTC.exists():
        print(f"  [ข้าม] ไม่พบ {NBTC.relative_to(ROOT)} — โหลดจาก datacatalog.nbtc.go.th ก่อน")
        return
    df = pd.read_excel(NBTC)
    brand = df["Brand"].astype(str).str.strip()
    ics = df[brand.str.upper() == ICS_BRAND]
    print(f"  ICS จดทะเบียน {len(ics)} ลำ = {len(ics)/len(df)*100:.4f}% ของทะเบียนทั้งประเทศ "
          f"({len(df):,} ลำ)")
    print(f"\n  รุ่น:")
    for m, n in ics["Model"].value_counts().items():
        print(f"    {str(m)[:34]:<36} {n:>3} ลำ")
    print(f"\n  จังหวัดที่ประจำการ:")
    for p, n in ics["ProvinceName"].value_counts().items():
        print(f"    {str(p)[:22]:<24} {n} ลำ")

    print(f"\n  เทียบกับผู้ผลิตไทยรายอื่น:")
    # NAC สะกด 4 แบบในทะเบียน ถ้าไม่รวมจะนับต่ำไปกว่าครึ่ง จึงต้อง match แบบ substring
    # แต่ "ICS" ห้าม substring เด็ดขาด เพราะไปโดน "Autel RobotICS" / "HG RobotICS"
    for key, exact in [("NAC", False), ("HG ROBOTICS", False), ("KASET GEN", False),
                       ("DRONE THAI", False), (ICS_BRAND, True)]:
        u = brand.str.upper()
        sub = df[u == key] if exact else df[u.str.contains(key, na=False)]
        label = sub["Brand"].mode()[0] if len(sub) else key
        print(f"    {str(label)[:24]:<26} {len(sub):>6,} ลำ")

    print(f"\n  แบรนด์โดรนสำรวจนำเข้าที่กระจุกในงานสำรวจ (คู่แข่งด้านผลิตภัณฑ์):")
    p = df["PurposeOfUseAircraft"].astype(str)
    mask = p.str.contains("สำรวจ|รังวัด|แผนที่|ประทานบัตร|ภูมิสารสนเทศ", na=False)
    for name, n in brand[mask].value_counts().head(10).items():
        share_in = n / mask.sum() * 100
        share_all = brand.value_counts().get(name, 0) / len(df) * 100
        idx = share_in / share_all if share_all else 0
        if idx >= 5:      # เอาเฉพาะที่กระจุกจริง ๆ
            print(f"    {str(name)[:24]:<26} {n:>4} ลำ | กระจุกกว่าปกติ {idx:>5.0f} เท่า")


def part_egp() -> pd.DataFrame | None:
    section("2) ICS ในระบบจัดซื้อจัดจ้างภาครัฐ (e-GP)")
    if not EGP.exists():
        print(f"  [ข้าม] ไม่พบ {EGP.relative_to(ROOT)} — รัน egp_drone_procurement.py ก่อน")
        return None
    df = pd.read_csv(EGP, dtype=str)
    df["ราคา"] = pd.to_numeric(df["ราคาตกลงซื้อ/จ้าง"], errors="coerce")
    d = df[df["_หมวด"] == "โดรน"].copy()
    d["สำรวจ"] = d["ชื่อโครงการ"].astype(str).str.contains(SURVEY_PAT, case=False, na=False)
    d["ทหาร"] = d["ชื่อหน่วยงาน"].astype(str).str.contains(MIL_PAT, na=False)
    d["อีสาน"] = d["จังหวัด"].isin(ISAN)

    ics = d[d["ชื่อผู้ชนะ"].astype(str).str.contains(ICS_WINNER, na=False)]
    print(f"  พบ ICS ชนะ {len(ics)} สัญญา จากทั้งหมด {len(d):,} โครงการ")
    for _, r in ics.sort_values("_ปีงบ").iterrows():
        budget = pd.to_numeric(r["งบประมาณ(บาท)"], errors="coerce")
        pct = r["ราคา"] / budget * 100 if budget else float("nan")
        print(f"\n    ปีงบ {r['_ปีงบ']} · {r['ราคา']:,.0f} บาท · {r['ชื่อประเภทโครงการ']}")
        print(f"      {str(r['ชื่อโครงการ'])[:88]}")
        print(f"      ผู้ซื้อ: {str(r['ชื่อหน่วยงาน'])[:52]}")
        print(f"      งบตั้งไว้ {budget:,.0f} → ชนะที่ {pct:.1f}% ของงบ")
    return d


def part_market(d: pd.DataFrame) -> None:
    section("3) ตลาดที่ ICS แข่งอยู่จริง: งานสำรวจ/ทำแผนที่ด้วยโดรน")
    svc = d[d["สำรวจ"]]
    print(f"  {len(svc)} โครงการ ({len(svc)/len(d)*100:.1f}% ของโครงการโดรนทั้งหมด) "
          f"| รวม {svc['ราคา'].sum():,.0f} บาท")
    print(f"\n  แนวโน้มรายปี:")
    prev = None
    for y, s in svc.groupby("_ปีงบ")["ราคา"]:
        # ใช้ {:+.0f} ไม่ใช่ "+{...}" ไม่งั้นปีที่ลดลงจะขึ้นเป็น "(+-92%)"
        g = f"  ({(s.sum()/prev-1)*100:+.0f}%)" if prev else ""
        print(f"    {y}: {len(s):>3} งาน | {s.sum():>13,.0f} บาท{g:<10} "
              f"| มัธยฐาน {s.median():>9,.0f}")
        prev = s.sum()
    # เตือนไม่ให้อ่านแนวโน้มจากยอดรวมเพียว ๆ เพราะบางปีถูกดีลเดียวลากไป
    big = svc.nlargest(1, "ราคา").iloc[0]
    print(f"\n    ⚠️ ยอดรวมรายปีแกว่งแรงเพราะดีลใหญ่ไม่กี่ดีล — ปี {big['_ปีงบ']} "
          f"มีงานเดียว {big['ราคา']:,.0f} บาท"
          f"\n       ({str(big['ชื่อโครงการ'])[:56]})"
          f"\n       ให้ดู 'จำนวนงาน' กับ 'มัธยฐาน' เป็นหลัก จะเห็นแนวโน้มจริงกว่า")

    print(f"\n  คู่แข่งตรงในตลาดบริการนี้:")
    top = (svc.groupby("_ผู้ชนะ_ปรับชื่อ")["ราคา"].agg(["sum", "count"])
           .sort_values("sum", ascending=False).head(10))
    for k, r in top.iterrows():
        disp = svc[svc["_ผู้ชนะ_ปรับชื่อ"] == k]["ชื่อผู้ชนะ"].iloc[0]
        print(f"    {str(disp)[:40]:<42} {int(r['count']):>3} งาน | {r['sum']:>12,.0f} บาท")

    print(f"\n  ลูกค้าที่จ้างงานสำรวจบ่อยที่สุด (= เป้าหมายการขาย):")
    for ag, c in svc["ชื่อหน่วยงาน"].value_counts().head(8).items():
        v = svc[svc["ชื่อหน่วยงาน"] == ag]["ราคา"].sum()
        print(f"    {str(ag)[:40]:<42} {c:>3} งาน | {v:>12,.0f} บาท")


def part_local(d: pd.DataFrame) -> None:
    section("4) ตลาดบ้านตัวเอง: อีสานและโคราช")
    isan, kr = d[d["อีสาน"]], d[d["จังหวัด"] == "นครราชสีมา"]
    print(f"  อีสาน 20 จังหวัด: {len(isan)} โครงการ ({len(isan)/len(d)*100:.1f}% ของประเทศ) "
          f"| {isan['ราคา'].sum():,.0f} บาท")
    print(f"    ในนั้นเป็นงานสำรวจ {int(isan['สำรวจ'].sum())} โครงการ "
          f"| {isan[isan['สำรวจ']]['ราคา'].sum():,.0f} บาท")
    print(f"\n  จังหวัดอีสานที่ใช้งบโดรนมากสุด:")
    for p, c in isan["จังหวัด"].value_counts().head(6).items():
        sub = isan[isan["จังหวัด"] == p]
        print(f"    {p:<16} {c:>3} โครงการ | {sub['ราคา'].sum():>11,.0f} บาท "
              f"| งานสำรวจ {int(sub['สำรวจ'].sum())}")

    print(f"\n  โคราช: {len(kr)} โครงการ | {kr['ราคา'].sum():,.0f} บาท "
          f"| มัธยฐาน {kr['ราคา'].median():,.0f} บาท")
    # ห้าม hardcode ว่า ICS ชนะหรือไม่ชนะในโคราช — ตอนมีข้อมูลแค่ 4 ปีเคยเขียนตายไว้ว่า
    # "ยังไม่เคยชนะ" แล้วพอขยายเป็น 11 ปีก็พบว่าชนะแล้วในปี 2564 ข้อความเลยกลายเป็นเท็จ
    ics_kr = kr[kr["ชื่อผู้ชนะ"].astype(str).str.contains(ICS_WINNER, na=False)]
    if ics_kr.empty:
        print(f"    ICS ยังไม่มีสัญญาในจังหวัดตัวเอง (จากข้อมูลที่ดึงมา)")
    else:
        print(f"    ICS มีสัญญาในจังหวัดตัวเองแล้ว {len(ics_kr)} งาน "
              f"| {ics_kr['ราคา'].sum():,.0f} บาท:")
        for _, r in ics_kr.iterrows():
            print(f"      ปีงบ {r['_ปีงบ']} · {r['ราคา']:,.0f} บาท · "
                  f"{str(r['ชื่อหน่วยงาน'])[:34]}")
    print(f"    ผู้ชนะรายใหญ่ในพื้นที่:")
    for k, r in (kr.groupby("_ผู้ชนะ_ปรับชื่อ")["ราคา"].agg(["sum", "count"])
                 .sort_values("sum", ascending=False).head(6).iterrows()):
        disp = kr[kr["_ผู้ชนะ_ปรับชื่อ"] == k]["ชื่อผู้ชนะ"].iloc[0]
        print(f"      {str(disp)[:38]:<40} {int(r['count'])} งาน | {r['sum']:>10,.0f} บาท")
    print(f"\n    หน่วยงานในโคราชที่ซื้อโดรน:")
    for a, c in kr["ชื่อหน่วยงาน"].value_counts().head(6).items():
        print(f"      {str(a)[:46]:<48} {c}")


def part_scale(d: pd.DataFrame) -> None:
    section("5) ขนาดตลาดที่เข้าถึงได้จริง — ต้องแยกทหารออกก่อน")
    for lab, sub in [("ทหาร/ความมั่นคง", d[d["ทหาร"]]), ("พลเรือน", d[~d["ทหาร"]])]:
        print(f"  {lab:<18} {len(sub):>5} โครงการ | {sub['ราคา'].sum():>15,.0f} บาท "
              f"| มัธยฐาน {sub['ราคา'].median():>9,.0f}")
    mil_share = d[d['ทหาร']]['ราคา'].sum() / d['ราคา'].sum() * 100
    print(f"\n  ฝั่งทหารคิดเป็น {mil_share:.0f}% ของมูลค่า แต่แค่ "
          f"{len(d[d['ทหาร']])/len(d)*100:.0f}% ของจำนวนโครงการ")
    print(f"  → ถ้าไม่แยกออก 'ขนาดตลาด' จะถูกดีลทหารไม่กี่ดีลลากไปทั้งหมด")

    print(f"\n  ดีลใหญ่สุด 3 รายการ (ตรวจด้วยตาแล้วว่าเป็นโดรนจริง ไม่ใช่สัญญาปนงานอื่น):")
    for _, r in d.nlargest(3, "ราคา").iterrows():
        print(f"    {r['ราคา']:>15,.0f} | {str(r['ชื่อหน่วยงาน'])[:24]:<26} "
              f"| {str(r['ชื่อโครงการ'])[:44]}")


def main() -> None:
    part_nbtc()
    d = part_egp()
    if d is not None:
        part_market(d)
        part_local(d)
        part_scale(d)

    section("ข้อจำกัดที่ต้องอ่านคู่กับตัวเลขข้างบน")
    print("""  1. e-GP เห็นเฉพาะ 'ฝั่งภาครัฐ' ตลาดเอกชนใหญ่กว่ามากและยังไม่มีแหล่งไหนตอบได้
  2. คีย์เวิร์ดจับจากชื่อโครงการ งานที่ตั้งชื่อกว้าง ๆ (เช่น 'จ้างสำรวจภูมิประเทศ'
     โดยไม่เอ่ยว่าใช้โดรน) จะหลุดหมด → ตัวเลขทุกตัวเป็นค่า 'อย่างน้อย'
  3. ช่อง PurposeOfUseAircraft ของ กสทช. เชื่อไม่ได้ — โดรนของ ICS เอง 13 จาก 15 ลำ
     จดว่า 'เพื่อการถ่ายภาพ ถ่ายทำ' ทั้งที่เป็นบริษัทสำรวจ
     สคริปต์นี้จึงนิยาม 'งานสำรวจ' จากชื่อโครงการใน e-GP แทน
  4. เลขนิติบุคคลของปีงบ 2565-2567 ถูก Excel ทำพัง (1.05552E+11) เชื่อมกับ DBD
     ได้เฉพาะปี 2568 — สัญญาทั้งสองของ ICS อยู่ในปีที่เลขเสีย
  5. ข้อมูลธุรกิจของ ICS มาจากเว็บบริษัทเอง ยังไม่ได้ยืนยันกับแหล่งอิสระ""")


if __name__ == "__main__":
    main()
