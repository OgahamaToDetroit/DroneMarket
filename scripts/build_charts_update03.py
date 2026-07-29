# -*- coding: utf-8 -*-
"""
build_charts_update03.py — สร้าง HTML ของกราฟสำหรับรายงาน Update 03 จาก CSV โดยตรง

เหตุผลที่ต้องมีสคริปต์นี้: ตัวเลขในกราฟต้องมาจากข้อมูลจริง ไม่ใช่พิมพ์มือ
รันแล้วได้ไฟล์ fragment ไปฝังในรายงาน และรันซ้ำได้เมื่อข้อมูลอัปเดต

    python scripts/build_charts_update03.py
    -> data/processed/update03_chart_fragments.html
       data/processed/update03_chart_values.json   (ไว้ตรวจสอบตัวเลข)

แล้วแทรกกราฟลงในรายงานที่มี marker <!--CHART_A--> / <!--CHART_B--> / <!--CHART_C-->
ให้อัตโนมัติ (รันซ้ำได้ เพราะแทรกแล้วครอบด้วย marker เดิมเสมอ)

กราฟที่สร้าง
    A  แท่งซ้อนรายปี  "คงเหลือในประเทศ vs ส่งออกต่อ"
    B  แท่งคู่รายเดือน 48 เดือน (นำเข้า/ส่งออก)
    C  อัตราส่วนส่งออก/นำเข้า รายเดือน — ให้เห็นจุดเปลี่ยน เม.ย. 2023
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV = PROJECT_ROOT / "data" / "processed" / "moc_hs8806_monthly.csv"
OUT_HTML = PROJECT_ROOT / "data" / "processed" / "update03_chart_fragments.html"
OUT_JSON = PROJECT_ROOT / "data" / "processed" / "update03_chart_values.json"

TH_MONTH = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
            "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


REPORT_DIR = PROJECT_ROOT / "reports" / "2026-07-29_update-03"

# ข้อความและตารางในรายงานเขียนไว้บนฐานปีชุดนี้ ถ้าข้อมูลไม่ครบแล้วยังแทรกกราฟ
# รายงานจะขัดแย้งกันเองแบบเงียบ ๆ (กราฟ 2 ปี แต่ตารางข้าง ๆ 4 ปี)
EXPECTED_YEARS = [2022, 2023, 2024, 2025]


def usd(v: float) -> str:
    return f"${v:,.0f}"


def millions(v: float) -> str:
    return f"${v/1e6:,.1f}M"


def inject(charts: dict[str, str], years: list[int]) -> None:
    """แทรกกราฟลงในรายงานที่มี marker

    ครอบด้วย marker เดิมทุกครั้ง จึงรันซ้ำได้เรื่อย ๆ โดยไม่ซ้อนทับ
    แต่จะไม่แทรกถ้าข้อมูลไม่ครบปีที่รายงานอ้างถึง
    """
    if not REPORT_DIR.exists():
        print(f"[SKIP] ยังไม่มี {REPORT_DIR.name} — ข้ามการแทรกกราฟ")
        return

    missing = [y for y in EXPECTED_YEARS if y not in years]
    if missing:
        print(f"[STOP] ข้อมูลขาดปี {missing} — ไม่แทรกกราฟลงรายงาน\n"
              f"       ถ้าแทรกตอนนี้ กราฟจะไม่ตรงกับตารางและข้อความในรายงาน\n"
              f"       ดึงข้อมูลให้ครบก่อน: python scripts/moc_hs_trade.py "
              f"--years {','.join(str(y) for y in EXPECTED_YEARS)}")
        return

    for path in sorted(REPORT_DIR.glob("*.html")):
        html = path.read_text(encoding="utf-8")
        hits = 0
        for key, frag in charts.items():
            marker = f"<!--CHART_{key}-->"
            block = f"{marker}\n{frag}\n{marker}"
            # กรณีเคยแทรกไปแล้ว: แทนที่ทั้งบล็อกระหว่าง marker คู่
            start = html.find(marker)
            if start == -1:
                continue
            end = html.find(marker, start + len(marker))
            if end == -1:
                html = html.replace(marker, block, 1)      # ครั้งแรก
            else:
                html = html[:start] + block + html[end + len(marker):]
            hits += 1
        if hits:
            path.write_text(html, encoding="utf-8")
            print(f"[OK] แทรกกราฟ {hits} ตัวลงใน reports/{REPORT_DIR.name}/{path.name}")


def main() -> None:
    df = pd.read_csv(CSV)
    monthly = (df.groupby(["year", "month", "flow"])["value_usd"].sum()
                 .unstack(fill_value=0).reset_index())
    for col in ("import", "export"):
        if col not in monthly:
            monthly[col] = 0.0
    monthly["net"] = monthly["import"] - monthly["export"]
    monthly["ratio"] = monthly.apply(
        lambda r: r["export"] / r["import"] if r["import"] else 0.0, axis=1)

    annual = monthly.groupby("year")[["import", "export", "net"]].sum().reset_index()
    years = annual["year"].tolist()
    max_total = annual["import"].max()

    parts: list[str] = []
    values: dict = {"annual": [], "monthly": []}

    # ---------- กราฟ A : แท่งซ้อนรายปี ----------
    parts.append('<!-- CHART A: annual stacked -->\n<div class="vchart">')
    for _, r in annual.iterrows():
        total, exp, ret = r["import"], r["export"], r["net"]
        bar_h = total / max_total * 100
        exp_share = exp / total * 100 if total else 0
        ret_share = 100 - exp_share
        tip = (f'{int(r["year"])}: นำเข้า {usd(total)} · '
               f'คงเหลือ {usd(ret)} ({ret_share:.0f}%) · ส่งออกต่อ {usd(exp)}')
        parts.append(
            f'  <div class="vcol"><div class="sbar" tabindex="0" data-tip="{tip}" '
            f'style="height:{bar_h:.2f}%">'
            f'<div class="sseg exp" style="height:{exp_share:.2f}%"></div>'
            f'<div class="sseg ret" style="height:{ret_share:.2f}%"></div>'
            f'</div></div>')
        values["annual"].append({
            "year": int(r["year"]), "import": total, "export": exp, "net": ret,
            "bar_h": round(bar_h, 2), "exp_share": round(exp_share, 2)})
    parts.append("</div>")

    parts.append('<div class="vlabels">')
    for _, r in annual.iterrows():
        parts.append(
            f'  <div>{int(r["year"])}<span class="note">คงเหลือ {millions(r["net"])} · '
            f'จาก {millions(r["import"])}</span></div>')
    parts.append("</div>")

    # ---------- กราฟ B : แท่งคู่รายเดือน ----------
    max_month = max(monthly["import"].max(), monthly["export"].max())
    parts.append('\n<!-- CHART B: monthly paired -->\n<div class="mchart">')
    for _, r in monthly.iterrows():
        y, m = int(r["year"]), int(r["month"])
        hi = r["import"] / max_month * 100
        ho = r["export"] / max_month * 100
        mark = " switch" if (y == 2023 and m == 4) else ""
        tip = (f'{TH_MONTH[m-1]} {y}: เข้า {millions(r["import"])} · '
               f'ออก {millions(r["export"])} · อัตราส่วน {r["ratio"]:.2f}')
        parts.append(
            f'  <div class="mcol{mark}" tabindex="0" data-tip="{tip}">'
            f'<div class="mbar in" style="height:{hi:.2f}%"></div>'
            f'<div class="mbar out" style="height:{ho:.2f}%"></div></div>')
        values["monthly"].append({
            "year": y, "month": m, "import": r["import"], "export": r["export"],
            "ratio": round(r["ratio"], 4)})
    parts.append("</div>")
    parts.append('<div class="mlabels">')
    for y in years:
        parts.append(f'  <div>{y}</div>')
    parts.append("</div>")

    # ---------- กราฟ C : อัตราส่วนรายเดือน ----------
    parts.append('\n<!-- CHART C: ratio -->\n<div class="rchart">')
    parts.append('  <div class="rline" style="bottom:50%"><span>0.50</span></div>')
    for _, r in monthly.iterrows():
        y, m = int(r["year"]), int(r["month"])
        h = min(r["ratio"], 1.0) * 100
        # ก่อน เม.ย. 2023 = ยุคที่ยังไม่มีรูปแบบของผ่าน
        pre = (y < 2023) or (y == 2023 and m < 4)
        cls = "rbar pre" if pre else "rbar"
        tip = f'{TH_MONTH[m-1]} {y}: อัตราส่วน {r["ratio"]:.2f}'
        parts.append(f'  <div class="{cls}" tabindex="0" data-tip="{tip}" '
                     f'style="height:{max(h,1.2):.2f}%"></div>')
    parts.append("</div>")
    parts.append('<div class="mlabels">')
    for y in years:
        parts.append(f'  <div>{y}</div>')
    parts.append("</div>")

    full = "\n".join(parts)
    OUT_HTML.write_text(full, encoding="utf-8")
    OUT_JSON.write_text(json.dumps(values, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"[OK] {OUT_HTML.relative_to(PROJECT_ROOT)}")
    print(f"[OK] {OUT_JSON.relative_to(PROJECT_ROOT)}")

    # แยกเป็นกราฟ A/B/C ด้วยคอมเมนต์คั่น แล้วแทรกลงรายงาน
    chunks = re.split(r"<!-- CHART ([ABC]):[^>]*-->", full)
    charts = {chunks[i]: chunks[i + 1].strip() for i in range(1, len(chunks) - 1, 2)}
    inject(charts, [int(y) for y in years])
    # ---------- สรุปตัวเลขที่รายงานอ้างถึง ----------
    lines: list[str] = []

    def say(s: str = "") -> None:
        lines.append(s)
        print(s)

    say()
    say("===== ตัวเลขที่ใช้ในกราฟ =====")
    for a in values["annual"]:
        say(f'  {a["year"]}: นำเข้า {usd(a["import"]):>14} | ส่งออกต่อ {usd(a["export"]):>14} '
            f'| คงเหลือ {usd(a["net"]):>13} | ส่งออก {a["exp_share"]:>5.1f}%')

    say()
    say("===== จำนวนลำ และราคาต่อลำ =====")
    qty = monthly.groupby("year")[["import", "export"]].sum()
    qcol = (df.groupby(["year", "flow"])["quantity"].sum().unstack(fill_value=0))
    for y in years:
        qi, qe = qcol.loc[y, "import"], qcol.loc[y, "export"]
        vi, ve = qty.loc[y, "import"], qty.loc[y, "export"]
        pi = vi / qi if qi else 0
        pe = ve / qe if qe else 0
        say(f'  {int(y)}: เข้า {qi:>9,.0f} ลำ (${pi:,.0f}/ลำ) | ออก {qe:>9,.0f} ลำ (${pe:,.0f}/ลำ)'
            f' | ออก/เข้า {qe/qi*100 if qi else 0:>5.1f}% (จำนวน) เทียบ {ve/vi*100 if vi else 0:>5.1f}% (มูลค่า)')

    say()
    say("===== ความสัมพันธ์นำเข้า-ส่งออก รายปี =====")
    for y in years:
        s = monthly[monthly["year"] == y]
        corr = s["import"].corr(s["export"])
        say(f'  {int(y)}: correlation {corr:>6.3f} | ratio รายเดือน '
            f'{s["ratio"].min():.2f}-{s["ratio"].max():.2f}')

    say()
    sw = [v for v in values["monthly"] if v["year"] == 2023 and v["month"] in (3, 4)]
    say("  จุดเปลี่ยน: " + " -> ".join(f'{v["month"]}/2023 ratio {v["ratio"]:.2f}' for v in sw))
    top = max(values["monthly"], key=lambda v: v["import"])
    say(f'  เดือนสูงสุด: {top["month"]}/{top["year"]} = {millions(top["import"])}')

    out_txt = PROJECT_ROOT / "scripts" / "build_charts_update03_out.txt"
    out_txt.write_text("\n".join(lines), encoding="utf-8")
    print(f'\n[OK] {out_txt.relative_to(PROJECT_ROOT)}')


if __name__ == "__main__":
    main()
