"""ตรวจว่าตัวเลขศุลกากรในตารางของเอกสาร ยังตรงกับข้อมูลใน CSV จริงไหม

ทำไมต้องมี
-----------
เอกสารในโปรเจกต์นี้อ้างตัวเลขไว้เยอะมาก (ยอดนำเข้ารายปี · ส่วนที่วัดได้/วัดไม่ได้ ·
ขอบล่าง · สัดส่วนประเทศ) พอดึงข้อมูลรอบใหม่แล้วตัวเลขขยับ เอกสารจะค้านข้อมูลเงียบ ๆ
สคริปต์นี้คำนวณใหม่จาก CSV แล้วเทียบกับ**ช่องในตาราง**ของเอกสารทีละช่อง

⚠️ ตรวจแบบ "มีเลขนี้อยู่ในไฟล์ไหม" ใช้ไม่ได้ — ลองมาแล้วมันไม่จับ
   ตอนทดสอบด้วยการแก้ช่องในตารางจาก 1,830 เป็น 1,999 การตรวจแบบค้นสตริงยัง
   ผ่านฉลุย เพราะเลข 1,830 ไปโผล่ในย่อหน้าอธิบายที่อื่นของไฟล์เดียวกัน
   → ต้องแกะตารางออกมาเทียบเป็นช่อง ๆ เท่านั้น

เคยจับอะไรได้บ้าง
------------------
· ขอบล่างปี 2568 ที่เขียนว่า 1,786 ล้าน — ยก 88062200 มาจากปี 2569 ซึ่งใหม่กว่า
  ปีเป้าหมายและมีข้อมูลแค่ 5 เดือน กติกาที่ถูกให้ 1,830 ล้าน
· ตาราง floor ใน SOURCES.md ปี 2566/2567 กรอกมั่วไป 2 แถว

รันยังไง
---------
    python scripts/verify_customs_docs.py        # exit 1 ถ้ามีช่องไหนไม่ตรง

ตรวจแค่ตัวเลข ไม่ได้ตรวจว่า**ตีความ**ถูกไหม — ข้อความรอบ ๆ ยังต้องอ่านเอง
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from customs_hs_trade import floor_estimate  # noqa: E402

DOCS = ["DATA.md", "SOURCES.md", "README.md", "reports/UPDATES.md"]

# ชื่อหัวคอลัมน์ที่เจอในเอกสาร → ค่าที่ต้องเอาไปเทียบ
# ตรวจด้วย "หัวคอลัมน์ขึ้นต้นด้วยคำนี้" เพราะบางที่เขียน "**วัดได้** (ผ่าน GATE)"
COLUMNS = {
    "นำเข้ารวม": "imp", "ของเข้าไทย": "imp", "นำเข้า": "imp",
    "ส่งออกรวม": "exp", "ส่งออก": "exp",
    "วัดได้": "measured",
    "วัดไม่ได้": "hole",
    "ยกของเก่ามาอุด": "carried",
    "ขอบล่าง": "floor",
    "พิกัดที่ผ่าน": "gate",
}


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def md_tables(txt: str):
    """คืนตารางมาร์กดาวน์ทั้งหมดเป็น (เลขบรรทัดหัว, หัวคอลัมน์, แถว)"""
    lines, out, i = txt.splitlines(), [], 0
    while i < len(lines):
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if lines[i].strip().startswith("|") and re.fullmatch(r"\|[\s:|-]+\|", nxt):
            head, rows, j = cells(lines[i]), [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(cells(lines[j]))
                j += 1
            out.append((i + 1, head, rows))
            i = j
        else:
            i += 1
    return out


def nums(cell: str) -> list[float]:
    """ตัวเลขทั้งหมดในช่อง — ทิ้งมาร์กดาวน์ตัวหนาและเครื่องหมายอื่นทิ้ง"""
    return [float(x.replace(",", ""))
            for x in re.findall(r"\d[\d,]*\.?\d*", cell.replace("*", ""))]


def clean_head(h: str) -> str:
    return h.replace("*", "").strip()


# ---------- คำนวณค่าจริงจาก CSV ----------
bal = pd.read_csv(ROOT / "data/processed/customs_hs8806_balance.csv", encoding="utf-8-sig")
bal["ผ่าน_GATE"] = bal["ผ่าน_GATE"].astype(str).str.lower().eq("true")
ctry = pd.read_csv(ROOT / "data/processed/customs_hs8806_by_country.csv", encoding="utf-8-sig")

truth: dict[int, dict] = {}
for y in sorted(bal["ปี"].unique()):
    d = bal[bal["ปี"] == y]
    imp = d["มูลค่าบาท_import"].sum()
    hole = d[~d["ผ่าน_GATE"]]["มูลค่าบาท_import"].sum()
    fe = floor_estimate(bal, y)
    truth[int(y)] = {
        "imp": imp / 1e6,
        "exp": d["มูลค่าบาท_export"].sum() / 1e6,
        "measured": d.loc[d["ผ่าน_GATE"], "อุปสงค์ในประเทศ_บาท"].sum() / 1e6,
        "hole": hole / 1e6,
        "hole_pct": hole / imp * 100 if imp else 0.0,
        "floor": fe["ขอบล่าง"] / 1e6,
        "carried": fe["ยกมา"] / 1e6,
        "gate": (int(d["ผ่าน_GATE"].sum()), len(d)),
    }

passed, fails = 0, []


def check(ok: bool, msg: str) -> None:
    global passed
    if ok:
        passed += 1
    else:
        fails.append(msg)


# ---------- ตรวจทีละช่องในตาราง ----------
print("=" * 74)
print("ตรวจช่องในตารางของเอกสาร เทียบกับ CSV")
print("=" * 74)
seen_tables = 0
for doc in DOCS:
    txt = (ROOT / doc).read_text(encoding="utf-8")
    for lineno, head, rows in md_tables(txt):
        cols = {}
        for idx, h in enumerate(head):
            for name, key in COLUMNS.items():
                if clean_head(h).startswith(name):
                    cols[idx] = key
                    break
        # ต้องเป็นตารางที่คอลัมน์แรกเป็นปี และมีคอลัมน์ที่เรารู้จักอย่างน้อย 2 ช่อง
        if len(cols) < 2 or not clean_head(head[0]).startswith("ปี"):
            continue
        seen_tables += 1
        print(f"\n{doc}:{lineno}  [{' · '.join(clean_head(h) for h in head)}]")
        n_rows = 0
        for row in rows:
            m = re.match(r"(\d{4})", row[0].replace("*", ""))
            if not m or int(m.group(1)) not in truth:
                continue
            y = int(m.group(1))
            n_rows += 1
            t = truth[y]
            for idx, key in cols.items():
                if idx >= len(row):
                    continue
                got, where = nums(row[idx]), f"{doc}:{lineno} ปี {y} คอลัมน์ '{clean_head(head[idx])}'"
                if key == "gate":
                    want = list(t["gate"])
                    check(got == want, f"  ✗ {where}: เขียน {got} ควรเป็น {want}")
                    continue
                want = t[key]
                tol = 0.05 if key == "carried" else 0.51
                check(any(abs(g - want) <= tol for g in got),
                      f"  ✗ {where}: เขียน {row[idx]!r} ควรมีเลข {want:,.1f}")
                if key == "hole" and len(got) > 1:      # ช่องแบบ "4,763 (70%)"
                    check(any(abs(g - t["hole_pct"]) <= 0.6 for g in got[1:]),
                          f"  ✗ {where}: เปอร์เซ็นต์ในช่องไม่ตรง ควรเป็น {t['hole_pct']:.1f}%")
        print(f"    ตรวจ {n_rows} แถว × {len(cols)} คอลัมน์")
        if n_rows == 0:
            print("      (ไม่มีแถวไหนเป็นปี พ.ศ. ที่มีข้อมูล — ข้ามตารางนี้)")

check(seen_tables >= 4, f"  ✗ หาตารางเจอแค่ {seen_tables} ตาราง — คาดว่าอย่างน้อย 4 "
                        f"(DATA.md · SOURCES.md ×2 · UPDATES.md) เอกสารอาจถูกแก้โครงสร้าง")

# ---------- สัดส่วนประเทศ ----------
print("\n" + "=" * 74)
print("ตรวจสัดส่วนประเทศ ปี 2568")
print("=" * 74)
c68 = ctry[ctry["ปี"] == 2568]
gate_ok = set(bal[(bal["ปี"] == 2568) & bal["ผ่าน_GATE"]]["พิกัด8"])
imp_ok = (c68[(c68["ทิศทาง"] == "import") & c68["พิกัด8"].isin(gate_ok)]
          .groupby("ประเทศ")["มูลค่าบาท"].sum().sort_values(ascending=False))
exp_all = c68[c68["ทิศทาง"] == "export"].groupby("ประเทศ")["มูลค่าบาท"].sum().sort_values(ascending=False)
cn, ru = imp_ok.iloc[0] / imp_ok.sum() * 100, exp_all.iloc[0] / exp_all.sum() * 100
print(f"  ของที่อยู่ในไทย  อันดับ 1 = {imp_ok.index[0]} {cn:.1f}%")
print(f"  ของที่ผ่านออกไป อันดับ 1 = {exp_all.index[0]} {ru:.1f}%")
allmd = "\n".join((ROOT / d).read_text(encoding="utf-8") for d in DOCS)
check(f"จีน {cn:.0f}%" in allmd, f"  ✗ ไม่พบ 'จีน {cn:.0f}%' ในเอกสาร")
check(f"รัสเซีย {ru:.0f}%" in allmd, f"  ✗ ไม่พบ 'รัสเซีย {ru:.0f}%' ในเอกสาร")

# ---------- กติกาขอบล่าง ----------
print("\n" + "=" * 74)
print("ตรวจกติกาขอบล่าง")
print("=" * 74)
bad = []
for y in sorted(bal["ปี"].unique()):
    for code, sy, v in floor_estimate(bal, y)["ที่มา"]:
        if sy > y:
            bad.append(f"ปี {y} พิกัด {code} ยกจากปี {sy} ซึ่งใหม่กว่าปีเป้าหมาย")
        cap = bal[(bal["ปี"] == y) & (bal["พิกัด8"] == int(code))]["มูลค่าบาท_import"].iloc[0]
        if v > cap + 1:
            bad.append(f"ปี {y} พิกัด {code} ยกมา {v:,.0f} เกินยอดนำเข้าจริง {cap:,.0f}")
check(not bad, "  ✗ กติกาขอบล่างผิด:\n" + "\n".join("     " + b for b in bad))
if not bad:
    print("  ✓ ไม่มีพิกัดไหนยกค่าจากปีที่ใหม่กว่าปีเป้าหมาย")
    print("  ✓ ไม่มีพิกัดไหนยกค่าเกินยอดนำเข้าจริงของปีนั้น")

# ---------- เลขเก่าที่ผิดต้องไม่กลับเข้าไปอยู่ในตาราง ----------
print("\n" + "=" * 74)
print("ตรวจว่าเลขเก่าที่ผิด (1,786) ไม่ได้กลับไปอยู่ในช่องตาราง")
print("=" * 74)
stale = [f"{doc}:{ln}" for doc in DOCS
         for ln, _h, rows in md_tables((ROOT / doc).read_text(encoding="utf-8"))
         for r in rows if any(abs(n - 1786) < 0.51 for c in r for n in nums(c))]
check(not stale, f"  ✗ เลข 1,786 กลับไปอยู่ในตารางที่ {', '.join(stale)}")
if not stale:
    print("  ✓ ไม่มีในตาราง (ที่เหลือในย่อหน้าอธิบายกับดัก ตั้งใจให้อยู่)")

print("\n" + "=" * 74)
total = passed + len(fails)
if fails:
    print(f"ผลตรวจ: {passed}/{total} ผ่าน")
    print("\n".join(fails))
    sys.exit(1)
print(f"ผลตรวจ: {passed}/{total} ผ่าน — ทุกช่องในตารางตรงกับข้อมูลจริง")
