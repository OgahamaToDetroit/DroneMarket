# -*- coding: utf-8 -*-
"""
egp_drone_procurement.py — โครงการจัดซื้อจัดจ้างโดรนของหน่วยงานรัฐ จากระบบ e-GP

ทำไมแหล่งนี้สำคัญ: เป็นแหล่งเดียวในโปรเจกต์ที่ให้ **ราคาต่อรายการ + ชื่อผู้ขาย +
จังหวัด** พร้อมกัน ศุลกากรให้มูลค่ารวมแต่ไม่บอกว่าใครขาย · กสทช. ให้จำนวนเครื่อง
แต่ไม่บอกราคา · ทะเบียนพาณิชย์ให้ชื่อบริษัทแต่ไม่บอกว่าค้าอะไร

**และให้ `เลขนิติบุคคล` ของผู้ชนะทุกราย** ซึ่งเป็นเลขทะเบียนเดียวกับที่ DBD ใช้
จึงใช้เชื่อมบริษัทกับข้อมูลนิติบุคคลได้ — ปิดช่องว่างที่ทะเบียนพาณิชย์ทำไม่ได้

แหล่ง: data.go.th (CKAN) ชุดข้อมูลของสำนักงานพัฒนารัฐบาลดิจิทัล
       สัญญาอนุญาต Creative Commons Attribution · ไม่ต้องใช้ API key
       มีตั้งแต่ปีงบประมาณ 2558 ถึง 2568

--------------------------------------------------------------------------
กับดักที่เจอจริง (ทั้งสามข้อทำให้ได้ผลผิดแบบเงียบ ๆ ถ้าไม่รู้)
--------------------------------------------------------------------------
1) **full-text search ของ CKAN ตัดคำไทยไม่เป็น — หาเจอแค่ ~15%**
   `datastore_search?q=โดรน` ตอบว่าเจอ 8 แถวในไฟล์ 598 MB
   แต่พอ stream ไฟล์จริงมานับเอง เจอ 7 แถวตั้งแต่ 81 MB แรก (~52 แถวทั้งไฟล์)
   เพราะ PostgreSQL tokenize ภาษาไทยไม่ได้ (ไทยไม่มีช่องว่างระหว่างคำ)
   `q=` จึงเจอเฉพาะที่ "โดรน" มีช่องว่าง/วงเล็บคั่น เช่น "(โดรน)"
   แต่ "ซื้อโดรนถ่ายภาพ" หรือ "โดรนปีกนิ่ง" หาไม่เจอ
   → **ต้อง stream แล้ว match เอง** ห้ามใช้ q= เป็นตัวกรองหลัก

2) **หัวคอลัมน์ไม่ตรงกับข้อมูล และไม่ตรงคนละแบบในไฟล์ชุดเดียวกัน**
   ข้อมูลเป็น **28 ช่องเสมอ** ทุกไฟล์ แต่บรรทัดหัวมี 2 แบบปนกัน:
     · ไฟล์ที่ 1 ของปี 2568 → หัว **26 ช่อง** (ขาด `เขต/อำเภอ`, `แขวง/ตำบล`)
     · ไฟล์ที่ 2-10 ของปีเดียวกัน → หัว **31 ช่อง** (มี `จังหวัด (Eng)`,
       `เขต/อำเภอ (Eng)`, `แขวง/ตำบล (Eng)` ที่**ไม่มีอยู่ในข้อมูลจริง**)
   ถ้า `zip(หัว, ข้อมูล)` ตรง ๆ ทุกช่องตั้งแต่ตำแหน่ง `จังหวัด` เป็นต้นไปจะเลื่อน
   ผลคือ `ชื่อผู้ชนะ` ได้วันที่ และ `เลขนิติบุคคล` ได้พิกัดภูมิศาสตร์ —
   **ผิดแบบดูเผิน ๆ ไม่ออก เพราะทุกช่องยังมีค่าอยู่**
   → สคริปต์นี้จึงยึด `SCHEMA` ที่ตรวจทีละช่องแล้ว ไม่อ่านหัวมาใช้
     แต่ยัง**เช็คว่าหัวเป็นหนึ่งในสองแบบที่รู้จัก** เผื่อต้นทางเปลี่ยนรูปแบบวันหน้า

   ⚠️ ถ้าเข้าผ่าน `datastore_search` API ของ data.go.th แทนการโหลดไฟล์
   CKAN จะประกาศคอลัมน์ 33 ช่อง การเลื่อน**ไม่เหมือนกับไฟล์ดิบ**
   อย่าเอา mapping ของสองทางมาใช้แทนกัน

3) **ชื่อชุดข้อมูลสะกดไม่คงที่** ปี 2558-2563 = `cgd-`, ปี 2564-2567 = `cdg-`
   (สลับตัวอักษร) ส่วนปี 2568 = `egp-contact-2568` (สะกด contact ไม่ใช่ contract)
   → ต้อง map ชื่อไว้ตายตัว เดาจากรูปแบบไม่ได้

4) **ห้าม parse ไปพร้อมกับที่ดาวน์โหลด** — ต้องโหลดลงดิสก์ให้จบก่อนแล้วค่อยอ่าน
   ถ้าเอา `csv.reader` คร่อม response stream ตรง ๆ จะพังกลางไฟล์ 590 MB ด้วย
   `ValueError: I/O operation on closed file` เพราะการ parse ช้ากว่าที่เซิร์ฟเวอร์ส่ง
   เราเลยหยุดอ่าน socket เป็นช่วง ๆ แล้วปลายทางตัดทิ้ง
   **กับดักนี้หลอกที่สุดในชุดนี้** เพราะทดสอบสั้น ๆ (อ่านไม่กี่หมื่นแถวแล้วหยุด)
   ไม่มีวันเจอ ต้องอ่านจนจบไฟล์เท่านั้นถึงจะโผล่

--------------------------------------------------------------------------
วิธีใช้
--------------------------------------------------------------------------
    python scripts/egp_drone_procurement.py                  # ปีงบ 2565-2568
    python scripts/egp_drone_procurement.py --years 2568
    python scripts/egp_drone_procurement.py --years 2568 --max-mb 100   # ทดสอบเร็ว

โหลดทีละไฟล์ลงที่พักชั่วคราวแล้วลบทันทีหลังอ่านจบ — ใช้พื้นที่สูงสุด ~600 MB
ไม่ใช่ 19.6 GB ที่เป็นขนาดรวมของทุกไฟล์
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import shutil
import sys
import tempfile
import time
from collections import Counter
from itertools import chain
from pathlib import Path

import pandas as pd
import requests

# ต้องตั้งทั้ง stdout และ stderr — ข้อความ [STOP] ออกทาง stderr
# ถ้าตั้งแค่ stdout ข้อความเตือนที่สำคัญที่สุดจะกลายเป็น \uXXXX อ่านไม่ออก
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

csv.field_size_limit(1 << 24)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = PROJECT_ROOT / "data" / "processed"

PKG_SHOW = "https://data.go.th/api/3/action/package_show"

# Session สำหรับ call เล็ก ๆ ที่อ่าน body จบในทีเดียว (ถามรายชื่อไฟล์)
# ส่วนการสตรีมไฟล์ใหญ่ใช้ Session ใหม่ต่อไฟล์ — ดูเหตุผลใน scan_file()
SESSION = requests.Session()

# ที่พักไฟล์ CSV ต้นทางระหว่างประมวลผล — โหลดทีละไฟล์แล้วลบทันที ใช้พื้นที่สูงสุด ~600 MB
TMP_DIR = Path(tempfile.gettempdir()) / "egp_drone_cache"

# checkpoint รายไฟล์ — งานนี้กินเวลา 2 ชั่วโมงครึ่ง ถ้าไม่บันทึกความคืบหน้าไว้
# หยุดกลางทางแล้วต้องเริ่มใหม่จากศูนย์ทั้งหมด
PARTS_DIR = PROC_DIR / "egp_parts"
FINGERPRINT = PARTS_DIR / "_keywords.txt"

# ชื่อชุดข้อมูลสะกดไม่คงที่ (กับดักข้อ 3) ต้องระบุตายตัว
PACKAGES = {
    2558: "cgd-contract-2558", 2559: "cgd-contract-2559", 2560: "cgd-contract-2560",
    2561: "cgd-contract-2561", 2562: "cgd-contract-2562", 2563: "cgd-contract-2563",
    2564: "cdg-contract-2564", 2565: "cdg-contract-2565", 2566: "cdg-contract-2566",
    2567: "cdg-contract-2567", 2568: "egp-contact-2568",
}

# โครงสร้างจริงของ "ข้อมูล" ซึ่งเป็น 28 ช่องเสมอทุกไฟล์ — หัวคอลัมน์ต่างหากที่ผิด
# (ตรวจสอบทีละช่องกับข้อมูลจริงแล้วทั้งไฟล์แบบหัว 26 และหัว 31)
SCHEMA = [
    "ลำดับ", "รหัสโครงการ", "ชื่อโครงการ", "ชื่อประเภทโครงการ", "ชื่อหน่วยงาน",
    "ชื่อหน่วยงานย่อย", "วิธีจัดซื้อฯ", "กลุ่มวิธีจัดซื้อฯ", "วันที่ประกาศ",
    "งบประมาณ(บาท)", "ราคากลาง(บาท)", "ราคาตกลงซื้อ/จ้าง", "ปีงบประมาณ",
    "วันที่เกิดรายการ", "จังหวัด", "เขต/อำเภอ", "แขวง/ตำบล", "สถานะโครงการ",
    "พิกัดของโครงการ", "ละติจูดโครงการ", "ลองจิจูดโครงการ", "เลขนิติบุคคล",
    "ชื่อผู้ชนะ", "เลขที่สัญญา", "วันที่ลงนามสัญญา", "วันที่สิ้นสุดสัญญา",
    "งบสัญญา(บาท)", "สถานะสัญญา",
]
MISSING_AFTER = "จังหวัด"
MISSING_COLS = ["เขต/อำเภอ", "แขวง/ตำบล"]
NAME_IDX = SCHEMA.index("ชื่อโครงการ")

# คำค้น — match แบบ substring บนชื่อโครงการ ราคาถูกมาก จึงกวาดให้กว้างไว้ก่อน
# "ซึ่งไม่มีนักบิน" เป็นสำนวนราชการที่คีย์เวิร์ดทั่วไปจับไม่ได้ แต่พบจริงในข้อมูล
DRONE_KEYWORDS = [
    "โดรน", "drone",
    "อากาศยานไร้คนขับ", "อากาศยานไร้นักบิน",
    "ไม่มีนักบิน",          # "อากาศยานซึ่งไม่มีนักบิน"
    "ยูเอวี", "uav",
    "มัลติโรเตอร์", "multirotor", "quadcopter",
    "อากาศยานบังคับ",
]

# "ไร้คนขับ" ใช้กับรถและเรือด้วย ถ้าเจอคำเหล่านี้แปลว่าไม่ใช่โดรน
NOT_DRONE = ["รถไร้คนขับ", "เรือไร้คนขับ", "ยานยนต์ไร้คนขับ", "รถยนต์ไร้คนขับ"]

# ระบบต่อต้านโดรนเป็นตลาดคนละฝั่ง ถ้านับรวมจะทำให้ตลาด "ขายโดรน" ดูใหญ่เกินจริง
COUNTER_PATTERNS = ["ต่อต้าน", "ต้านอากาศยาน", "anti-drone", "antidrone",
                    "ตรวจจับและทำลาย", "รบกวนสัญญาณ"]

# ─── งานสำรวจทางอากาศที่ "ไม่เอ่ยคำว่าโดรน" ───────────────────────────────
# ตลาดบริการสำรวจส่วนใหญ่ตั้งชื่อโครงการตามผลลัพธ์ ไม่ใช่ตามเครื่องมือ เช่น
# "จ้างจัดทำแผนที่ภาพถ่ายทางอากาศออร์โธ มาตราส่วน 1:4000" — ไม่มีคำว่าโดรนเลย
# คีย์เวิร์ดชุด DRONE_KEYWORDS จับไม่ได้ ทั้งที่เป็นตลาดเดียวกัน
#
# ⚠️ ห้ามใส่คำว่า "สำรวจ" ลอย ๆ จะโดนงานรังวัดที่ดินแบบเดินเท้าเป็นหมื่นรายการ
# ⚠️ ห้ามใส่ "ออร์โธ" ลอย ๆ จะโดนออร์โธปิดิกส์กับทันตกรรมจัดฟัน
AERIAL_KEYWORDS = [
    "ภาพถ่ายทางอากาศ", "แผนที่ภาพถ่าย",
    "ออร์โธโฟโต", "orthophoto", "ortho-photo",
    "โฟโตแกรมเมตรี", "photogramme",       # ครอบ photogrammetry / photogrammetric
    "บินสำรวจ", "สำรวจทางอากาศ",
    "ไลดาร์", "lidar",
]

# อุปกรณ์ทดสอบการบิน — อีกขาธุรกิจของ ICS (เป็นตัวแทนจำหน่าย ไม่ได้ผลิตเอง)
# ลูกค้าคือมหาวิทยาลัยและสถาบันวิจัย ซึ่งซื้อผ่าน e-GP ทั้งนั้น
TEST_EQUIP_KEYWORDS = [
    "อุโมงค์ลม", "wind tunnel", "windtunnel",
    "thrust stand", "flight stand",
    "ชุดทดสอบแรงขับ", "แท่นทดสอบแรงขับ", "ทดสอบแรงขับ",
]


def keyword_fingerprint() -> str:
    """ลายนิ้วมือของกติกาการคัดกรอง — ใช้กันไม่ให้ resume ทับกติกาที่เปลี่ยนไปแล้ว

    ถ้าแก้คีย์เวิร์ดแล้วยัง resume ต่อ จะได้ผลลัพธ์ปนกันสองกติกาโดยไม่มีอะไรเตือน
    """
    blob = json.dumps([DRONE_KEYWORDS, NOT_DRONE, COUNTER_PATTERNS,
                       AERIAL_KEYWORDS, TEST_EQUIP_KEYWORDS],
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def part_path(year_be: int, fname: str) -> Path:
    """ตั้งชื่อ checkpoint จาก 'ชื่อไฟล์ต้นทาง' ไม่ใช่ลำดับที่
    เพราะถ้าต้นทางสลับลำดับไฟล์วันหน้า การใช้ลำดับจะจับคู่ผิด"""
    return PARTS_DIR / f"{year_be}_{fname}.jsonl"


def write_part(pp: Path, rows: list[dict]) -> None:
    """เขียนแบบ atomic — เขียนไฟล์ชั่วคราวก่อนแล้วค่อย rename

    ถ้าเขียนตรง ๆ แล้วถูกฆ่ากลางทาง จะเหลือไฟล์ที่ไม่ครบแต่ 'มีอยู่'
    รอบหน้า resume จะเชื่อว่าไฟล์นั้นอ่านจบแล้ว → ข้อมูลหายเงียบ ๆ
    ใช้ jsonl ไม่ใช่ csv เพราะแต่ละปี schema ไม่เหมือนกัน คอลัมน์จึงไม่ตรงกัน
    """
    tmp = pp.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(pp)


def read_part(pp: Path) -> list[dict]:
    rows = []
    with open(pp, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def resources_for(year_be: int) -> list[str]:
    """ดึง URL ของไฟล์ CSV ทุกไฟล์ในปีงบประมาณนั้น"""
    pkg = PACKAGES.get(year_be)
    if not pkg:
        raise SystemExit(f"[STOP] ไม่รู้จักปีงบประมาณ {year_be} "
                         f"(มีให้เลือก {min(PACKAGES)}-{max(PACKAGES)})")
    r = SESSION.get(PKG_SHOW, params={"id": pkg}, timeout=60)
    r.raise_for_status()
    return [res["url"] for res in r.json()["result"]["resources"]
            if (res.get("format") or "").upper() == "CSV"]


def resolve_schema(header: list[str], n_data: int) -> tuple[list[str] | None, str]:
    """หาว่าไฟล์นี้ควรอ่านด้วยชื่อคอลัมน์ชุดไหน คืน (schema, คำอธิบาย)

    ไฟล์ e-GP มีอย่างน้อย 2 รุ่นที่โครงสร้างไม่เหมือนกัน จึงต้องเลือกตามไฟล์
    ถ้าจับคู่ไม่ได้ให้คืน None แล้วข้ามไฟล์ — ดีกว่าอ่านเลื่อนช่องแบบไม่มีใครรู้
    """
    head = [h.strip().lstrip("﻿") for h in header]

    # รุ่น A (พบในปีงบ 2565-2567): หัวตรงกับข้อมูล 31 ช่อง มีคอลัมน์ (Eng) ที่มีค่าจริง
    if len(head) == n_data:
        return head, f"หัวตรงข้อมูล ({n_data} ช่อง)"

    # รุ่น B (พบในปีงบ 2568): ข้อมูล 28 ช่อง แต่บรรทัดหัวเพี้ยนได้ 2 แบบ
    if n_data == len(SCHEMA):
        trimmed = [h for h in head if "(eng)" not in h.replace(" ", "").lower()]
        if trimmed == SCHEMA:
            return SCHEMA, f"หัวเกิน (Eng) {len(head)}→{n_data} ช่อง"
        if MISSING_AFTER in trimmed:
            i = trimmed.index(MISSING_AFTER) + 1
            if trimmed[:i] + MISSING_COLS + trimmed[i:] == SCHEMA:
                return SCHEMA, f"หัวขาด 2 ช่อง {len(head)}→{n_data}"

    return None, f"รูปแบบใหม่ที่ยังไม่รู้จัก (หัว {len(head)} · ข้อมูล {n_data})"


def classify(name: str) -> tuple[str, str] | None:
    """คืน (หมวด, คำที่ทำให้ match) หรือ None ถ้าไม่เกี่ยว

    ลำดับการตัดสินสำคัญ: เช็คคำว่าโดรนก่อนเสมอ เพื่อให้หมวด "โดรน" มีความหมาย
    เดิมไม่เปลี่ยน (เทียบตัวเลขกับรอบก่อนได้) ส่วนหมวด "สำรวจทางอากาศ" จึงหมายถึง
    **งานที่เราเคยมองไม่เห็นเพราะไม่มีคำว่าโดรนอยู่ในชื่อ** ซึ่งเป็นตัวเลขที่อยากรู้
    """
    low = name.lower()

    hit = next((k for k in DRONE_KEYWORDS if k in low), None)
    if hit and not any(p in low for p in NOT_DRONE):
        kind = "ต่อต้านโดรน" if any(p in low for p in COUNTER_PATTERNS) else "โดรน"
        return kind, hit

    hit = next((k for k in TEST_EQUIP_KEYWORDS if k in low), None)
    if hit:
        return "อุปกรณ์ทดสอบการบิน", hit

    hit = next((k for k in AERIAL_KEYWORDS if k in low), None)
    if hit:
        return "สำรวจทางอากาศ", hit

    return None


PROBE_ROWS = 300        # จำนวนแถวที่ดูเพื่อหาความยาวแถวที่แท้จริงของไฟล์


def download(url: str, dest: Path, tries: int = 3) -> None:
    """โหลดไฟล์ลงดิสก์ก่อน แล้วค่อยเปิดอ่าน — **ห้าม parse ตรงจาก response**

    เคยทำแบบ parse ไปพร้อมกับที่โหลด (csv.reader คร่อม r.raw) แล้วพังเป็นประจำด้วย
    `ValueError: I/O operation on closed file` กลางไฟล์ 590 MB
    สาเหตุ: การ parse ช้ากว่าความเร็วที่เซิร์ฟเวอร์ส่ง เราจึงหยุดอ่าน socket เป็นช่วง ๆ
    แล้วปลายทางตัด connection ทิ้ง
    กับดักนี้หลอกมากเพราะ**ทดสอบสั้น ๆ ไม่มีวันเจอ** ต้องอ่านจนจบไฟล์ถึงจะโผล่
    """
    for attempt in range(1, tries + 1):
        try:
            with SESSION.get(url, timeout=(30, 120), stream=True) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            return
        except Exception:
            dest.unlink(missing_ok=True)
            if attempt == tries:
                raise
            time.sleep(3 * attempt)


def scan_local(path: Path, year_be: int, fname: str,
               max_mb: int | None) -> tuple[list[dict], int, str]:
    """อ่านไฟล์ที่โหลดมาแล้ว คืน (แถวที่ match, จำนวนแถวที่อ่าน, สถานะ)"""
    out: list[dict] = []
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.reader(fh)
        try:
            raw_header = next(reader)
        except StopIteration:
            return [], 0, "ไฟล์ว่าง"

        # ดูหลายแถวก่อนตัดสินว่าไฟล์นี้กี่ช่อง — แถวแรกแถวเดียวเชื่อไม่ได้
        # (บางไฟล์แถวแรกมี comma ในข้อความจนนับได้ 45 ช่อง ทั้งที่ไฟล์เป็น 31)
        probe: list[list[str]] = []
        for row in reader:
            probe.append(row)
            if len(probe) >= PROBE_ROWS:
                break
        if not probe:
            return [], 0, "ไม่มีข้อมูล"
        n_data = Counter(len(x) for x in probe).most_common(1)[0][0]

        schema, note = resolve_schema(raw_header, n_data)
        if schema is None:
            return [], len(probe), note
        name_idx = schema.index("ชื่อโครงการ") if "ชื่อโครงการ" in schema else NAME_IDX

        n = 0
        for row in chain(probe, reader):
            n += 1
            if len(row) != len(schema):
                continue                   # แถวเพี้ยน ข้ามไป ไม่เดา
            # เช็คชื่อโครงการก่อนสร้าง dict — เร็วกว่ามากเมื่อต้องอ่านหลายสิบล้านแถว
            got = classify(row[name_idx])
            if got:
                rec = dict(zip(schema, row))
                rec["_ปีงบ"], rec["_หมวด"], rec["_คำที่พบ"] = year_be, got[0], got[1]
                rec["_ไฟล์"] = fname
                out.append(rec)
            if max_mb and n >= max_mb * 700:   # ประมาณ 700 แถว/MB ใช้ตอนทดสอบ
                break
    return out, n, f"ok · {note}"


def scan_file(url: str, year_be: int, max_mb: int | None) -> tuple[list[dict], int, str]:
    """โหลดไฟล์ลงที่พักชั่วคราว อ่าน แล้วลบทิ้ง (ไม่เก็บสะสม — รวมทุกปี ~19.6 GB)"""
    fname = url.rsplit("/", 1)[-1]
    tmp = TMP_DIR / fname
    try:
        download(url, tmp)
        return scan_local(tmp, year_be, fname, max_mb)
    finally:
        tmp.unlink(missing_ok=True)


KEEP = ["_ปีงบ", "_หมวด", "รหัสโครงการ", "ชื่อโครงการ", "ชื่อประเภทโครงการ",
        "ชื่อหน่วยงาน", "ชื่อหน่วยงานย่อย", "กลุ่มวิธีจัดซื้อฯ", "วันที่ประกาศ",
        "งบประมาณ(บาท)", "ราคากลาง(บาท)", "ราคาตกลงซื้อ/จ้าง", "จังหวัด",
        "เขต/อำเภอ", "สถานะโครงการ", "เลขนิติบุคคล", "ชื่อผู้ชนะ",
        "งบสัญญา(บาท)", "สถานะสัญญา", "_คำที่พบ", "_ไฟล์"]
KEEP_OUT = KEEP[:KEEP.index("ชื่อผู้ชนะ") + 1] + ["เลขนิติบุคคล_ใช้ได้", "_ผู้ชนะ_ปรับชื่อ"] \
    + KEEP[KEEP.index("ชื่อผู้ชนะ") + 1:]

# คำนำหน้า/ต่อท้ายที่เขียนได้หลายแบบ ถ้าไม่ปรับให้ตรงกัน groupby จะแยกบริษัทเดียวเป็นหลายราย
# ⚠️ ต้องเรียง "คำยาวก่อนคำสั้น" เสมอ — ถ้าตัด "จำกัด" ก่อน "ห้างหุ้นส่วนจำกัด"
#    คำยาวจะเหลือ "ห้างหุ้นส่วน" แล้วแมตช์ไม่ได้อีก ทำให้ หจก. เดียวถูกนับเป็น 2 ราย
NAME_NOISE = [("ห้างหุ้นส่วนจำกัด", ""), ("ห้างหุ้นส่วนสามัญ", ""),
              ("จำกัด (มหาชน)", ""), ("บริษัท", ""), ("บจก.", ""), ("บมจ.", ""),
              ("หจก.", ""), ("(มหาชน)", ""), ("จำกัด", ""), ("　", " ")]


def norm_name(s: str) -> str:
    """ปรับชื่อบริษัทให้เทียบกันได้ — ปีงบ 2565-2567 ใช้ชื่อเป็น key เดียวที่เหลือ
    เพราะเลขนิติบุคคลถูก Excel ทำพัง จึงต้องรวมชื่อที่เขียนต่างกันให้เป็นรายเดียว"""
    s = str(s or "")
    for a, b in NAME_NOISE:
        s = s.replace(a, b)
    return " ".join(s.split()).lower()


# ช่วงราคาที่แยกตลาดคนละแบบออกจากกัน — ระบบ UAV ทางทหารกับโดรนสำรวจของ อบต.
# ไม่ใช่ตลาดเดียวกัน ถ้าใช้มัธยฐานตัวเดียวคร่อมทั้งสองกลุ่มจะไม่ได้ตัวเลขที่ใช้ได้จริง
BANDS = [(0, 100_000, "< 1 แสน"), (100_000, 500_000, "1-5 แสน"),
         (500_000, 2_000_000, "5 แสน-2 ล้าน"), (2_000_000, 20_000_000, "2-20 ล้าน"),
         (20_000_000, float("inf"), "> 20 ล้าน")]


# ─── ของปนในหมวดใหม่ ที่พบตอนไล่ดูดีลใหญ่ด้วยตา ────────────────────────────
# บทเรียน: คีย์เวิร์ดที่ดู "เฉพาะทาง" ก็ยังกวาดของผิดประเภทมาได้ ต้องเปิดดูจริง
#
# 1) "อุโมงค์ลม" ดีลใหญ่สุด 3 อันดับแรกเป็น **อุโมงค์ลมฝึกกระโดดร่ม** ของกองทัพ
#    (369 + 203 + 190 ล้านบาท) ไม่ใช่อุโมงค์ลมทดสอบอากาศพลศาสตร์แบบที่ ICS ขาย
#    ถ้าไม่ตัดออก ตัวเลขหมวดนี้จะเกินจริงราว 3 ใน 4
# 2) "lidar" ดีลใหญ่อันดับ 2 ของหมวดสำรวจคือ **LiDAR ติดตั้งบนรถยนต์** (80 ล้าน)
#    เป็นการสำรวจภาคพื้น ไม่ใช่ทางอากาศเลย
EXCLUDE_RULES = [
    ("อุโมงค์ลมฝึกกระโดดร่ม ไม่ใช่ทดสอบอากาศพลศาสตร์",
     ["ทางดิ่ง", "แนวดิ่ง", "กระโดดร่ม"]),
    ("สำรวจภาคพื้น ไม่ใช่ทางอากาศ",
     ["ติดตั้งบนรถ", "บนรถยนต์", "ติดรถยนต์", "mobile mapping"]),
]


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """แปลงชนิดข้อมูลและเพิ่มคอลัมน์ช่วยวิเคราะห์ (ใช้ทั้งตอนดึงสดและตอนอ่านจาก cache)"""
    for c in ["งบประมาณ(บาท)", "ราคากลาง(บาท)", "ราคาตกลงซื้อ/จ้าง"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["_ปีงบ"] = pd.to_numeric(df["_ปีงบ"], errors="coerce").astype("Int64")
    # ไฟล์ปีงบ 2565-2567 ถูกเปิดผ่าน Excel ก่อนเผยแพร่ เลขนิติบุคคล 13 หลัก
    # จึงกลายเป็น scientific notation (0105552xxxxx → "1.05552E+11") กู้คืนไม่ได้
    # ต้องทำเครื่องหมายไว้ ไม่งั้นจะเอาไปเชื่อมกับ DBD แล้วได้บริษัทผิด
    df["เลขนิติบุคคล_ใช้ได้"] = (df["เลขนิติบุคคล"].astype(str)
                                  .str.match(r"^[0-9xX]{10,17}$").fillna(False))
    df["_ผู้ชนะ_ปรับชื่อ"] = df["ชื่อผู้ชนะ"].map(norm_name)

    # ทำเครื่องหมายของปน แต่**ไม่ลบทิ้ง** เพื่อให้ตรวจย้อนได้ว่าตัดอะไรออกไปเพราะอะไร
    low = df["ชื่อโครงการ"].astype(str).str.lower()
    df["_ตัดออกเพราะ"] = ""
    for reason, pats in EXCLUDE_RULES:
        hit = low.str.contains("|".join(pats), na=False) & (df["_ตัดออกเพราะ"] == "")
        df.loc[hit, "_ตัดออกเพราะ"] = reason

    # แยก "ขายของ" กับ "ขายบริการ" ด้วยฟิลด์ของราชการเอง ไม่ใช่เดาจากคีย์เวิร์ด
    # สำคัญเพราะตลาดสองอันนี้คนละอันกัน: ซื้อกล้อง/ซอฟต์แวร์ ≠ จ้างคนไปบินสำรวจ
    df["_ชนิดงาน"] = df["ชื่อประเภทโครงการ"].map(
        lambda s: "ขายของ" if str(s).strip() == "ซื้อ" else "ขายบริการ")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(
        description="ดึงโครงการจัดซื้อโดรนของภาครัฐจากระบบ e-GP")
    # default = ทุกปีที่ต้นทางมี (2558-2568) เพื่อดูว่าตลาดเริ่มโตตอนไหน
    # ใช้เวลา ~75 นาที · ถ้าจะเอาเร็วให้ระบุปีเอง เช่น --years 2565,2566,2567,2568
    ap.add_argument("--years", default=",".join(str(y) for y in sorted(PACKAGES)),
                    help="ปีงบประมาณ พ.ศ. คั่นด้วย comma")
    ap.add_argument("--max-mb", type=int, default=None,
                    help="จำกัดปริมาณที่อ่านต่อไฟล์ (ใช้ทดสอบเท่านั้น)")
    ap.add_argument("--from-cache", action="store_true",
                    help="วิเคราะห์จาก CSV ที่ดึงไว้แล้ว ไม่ต้องโหลดใหม่")
    ap.add_argument("--fresh", action="store_true",
                    help="ลบ checkpoint แล้วเริ่มดึงใหม่ทั้งหมด")
    args = ap.parse_args()

    if args.from_cache:
        cache = PROC_DIR / "egp_drone_projects.csv"
        if not cache.exists():
            raise SystemExit(f"[STOP] ยังไม่มี {cache.relative_to(PROJECT_ROOT)} "
                             f"— ต้องรันแบบดึงข้อมูลจริงก่อนหนึ่งครั้ง")
        print(f"[cache] อ่านจาก {cache.relative_to(PROJECT_ROOT)} (ไม่ได้ดึงข้อมูลใหม่)")
        df = prepare(pd.read_csv(cache, dtype=str))
        # คอลัมน์ที่คำนวณได้ (_ผู้ชนะ_ปรับชื่อ, เลขนิติบุคคล_ใช้ได้) ต้องเขียนกลับด้วย
        # ไม่งั้นถ้าแก้กติกาการปรับชื่อ ไฟล์ CSV จะค้างค่าเก่าไว้ทั้งที่รายงานใช้ค่าใหม่
        df[KEEP_OUT].to_csv(cache, index=False, encoding="utf-8-sig")
        summarize(df, [])
        return

    years = [int(y.strip()) for y in args.years.split(",") if y.strip()]
    if args.max_mb:
        print(f"⚠️  โหมดทดสอบ: อ่านแค่ ~{args.max_mb} MB ต่อไฟล์ "
              f"ผลลัพธ์ไม่ครบ ห้ามเอาไปใช้จริง\n")

    rows: list[dict] = []
    problems: list[str] = []
    t0 = time.time()
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- จัดการ checkpoint ----------
    use_ckpt = not args.max_mb          # โหมดทดสอบไม่ใช้ checkpoint (ข้อมูลไม่ครบ)
    fp = keyword_fingerprint()
    if args.fresh and PARTS_DIR.exists():
        shutil.rmtree(PARTS_DIR)
        print("[fresh] ลบ checkpoint เดิมทั้งหมดแล้ว เริ่มนับหนึ่งใหม่\n")
    if use_ckpt:
        PARTS_DIR.mkdir(parents=True, exist_ok=True)
        old = FINGERPRINT.read_text(encoding="utf-8").strip() if FINGERPRINT.exists() else None
        if old and old != fp:
            # ยอมหยุดดีกว่าเอาผลของสองกติกามาปนกันแบบไม่มีใครรู้
            raise SystemExit(
                f"[STOP] คีย์เวิร์ดเปลี่ยนไปจากตอนที่สร้าง checkpoint ไว้ "
                f"({old} → {fp})\n"
                f"        ถ้า resume ต่อจะได้ผลปนกันสองกติกา เลือกทางใดทางหนึ่ง:\n"
                f"          · รันใหม่ทั้งหมดด้วยกติกาใหม่  → เพิ่ม --fresh\n"
                f"          · ย้อนคีย์เวิร์ดกลับเป็นชุดเดิม → แล้วรันซ้ำได้เลย")
        FINGERPRINT.write_text(fp, encoding="utf-8")
        done = len(list(PARTS_DIR.glob("*.jsonl")))
        if done:
            print(f"[resume] พบ checkpoint {done} ไฟล์ — จะข้ามไฟล์เหล่านั้นไป\n")

    for year in years:
        urls = resources_for(year)
        print(f"\n=== ปีงบประมาณ {year} — {len(urls)} ไฟล์ ===")
        for i, url in enumerate(urls, 1):
            fname = url.rsplit("/", 1)[-1]
            pp = part_path(year, fname)
            if use_ckpt and pp.exists():
                got = read_part(pp)
                rows.extend(got)
                print(f"  ไฟล์ {i:>2}/{len(urls)}: ข้าม — มี checkpoint แล้ว "
                      f"({len(got)} รายการ)")
                continue
            try:
                got, n, status = scan_file(url, year, args.max_mb)
            except Exception as e:
                msg = f"{year} ไฟล์ {i}: {type(e).__name__}: {e}"
                print(f"  [WARN] {msg}")
                problems.append(msg)
                continue
            if not status.startswith("ok"):
                msg = f"{year} ไฟล์ {i}: {status}"
                print(f"  [WARN] {msg}")
                problems.append(msg)
                continue
            rows.extend(got)
            # เขียน checkpoint ทันทีที่อ่านไฟล์จบ แม้จะพบ 0 รายการ
            # (ไฟล์เปล่าคือหลักฐานว่า "อ่านแล้ว ไม่มีอะไร" ต่างจาก "ยังไม่ได้อ่าน")
            # โหมด --max-mb ห้ามเขียน เพราะข้อมูลไม่ครบจะไปปนกับของจริงรอบหน้า
            if use_ckpt:
                write_part(pp, got)
            print(f"  ไฟล์ {i:>2}/{len(urls)}: อ่าน {n:>8,} แถว → พบ {len(got):>3} "
                  f"| {status[5:]} ({time.time()-t0:>5.0f} วิ)")

    if not rows:
        print("\n[WARN] ไม่พบรายการโดรนเลย — ตรวจสอบปีและคีย์เวิร์ด")
        return

    df = pd.DataFrame(rows)
    for c in KEEP:
        if c not in df.columns:
            df[c] = None
    df = df[KEEP]

    # 1 โครงการอาจมีหลายสัญญา/หลายแถว ถ้าไม่ dedup ยอดรวมจะนับซ้ำ
    before = len(df)
    df = df.drop_duplicates(subset=["รหัสโครงการ"], keep="first")
    print(f"\n[dedup] {before} แถว → {len(df)} โครงการ (ตัดซ้ำ {before - len(df)})")

    df = prepare(df)

    PROC_DIR.mkdir(parents=True, exist_ok=True)
    # โหมดทดสอบต้องเขียนคนละไฟล์ ไม่งั้นผลที่อ่านมาไม่ครบจะไปทับของจริง
    # แล้วไม่มีอะไรบอกภายหลังว่าตัวเลขในไฟล์นั้นขาด (เคยพลาดแบบนี้มาแล้วกับ moc_hs_trade)
    out_csv = PROC_DIR / ("egp_drone_projects_partial.csv" if args.max_mb
                          else "egp_drone_projects.csv")
    df[KEEP_OUT].to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"[OK] saved -> {out_csv.relative_to(PROJECT_ROOT)}  ({len(df)} โครงการ)")
    summarize(df, problems)
    print(f"\nใช้เวลาดึงข้อมูลทั้งหมด {time.time()-t0:.0f} วินาที")


def summarize(df: pd.DataFrame, problems: list[str]) -> None:
    drone = df[df["_หมวด"] == "โดรน"]
    counter = df[df["_หมวด"] == "ต่อต้านโดรน"]
    # ราคาตกลง = 0/ว่าง แปลว่ายังไม่ได้ผู้ชนะ ถ้าเอามาเฉลี่ยด้วยค่าเฉลี่ยจะต่ำผิด
    awarded = drone[drone["ราคาตกลงซื้อ/จ้าง"].fillna(0) > 0]

    print(f"\n===== ภาพรวมแยกหมวด =====")
    NOTE = {
        "โดรน": "ชื่อโครงการเอ่ยคำว่าโดรน/UAV ตรง ๆ",
        "สำรวจทางอากาศ": "งานสำรวจที่ไม่เอ่ยคำว่าโดรน ← เคยมองไม่เห็น",
        "อุปกรณ์ทดสอบการบิน": "อุโมงค์ลม / แท่นทดสอบแรงขับ",
        "ต่อต้านโดรน": "คนละตลาดกับการขายโดรน",
    }
    for kind, sub in df.groupby("_หมวด"):
        v = sub[sub["ราคาตกลงซื้อ/จ้าง"].fillna(0) > 0]["ราคาตกลงซื้อ/จ้าง"]
        print(f"  {kind:<20} {len(sub):>5} โครงการ | {v.sum():>15,.0f} บาท"
              f"  ← {NOTE.get(kind, '')}")
    print(f"\n  หมายเหตุ: ตัวเลขวิเคราะห์ละเอียดด้านล่างใช้เฉพาะหมวด 'โดรน' "
          f"({len(drone)} โครงการ)\n  เพื่อให้เทียบกับรอบก่อนได้ "
          f"ส่วนหมวดใหม่ดูที่ท้ายรายงาน")

    print(f"\n===== มูลค่าจัดซื้อโดรนรายปีงบประมาณ (เฉพาะที่ได้ผู้ชนะแล้ว) =====")
    g = awarded.groupby("_ปีงบ")["ราคาตกลงซื้อ/จ้าง"]
    for year, s in g:
        print(f"  {year}: {len(s):>4} โครงการ | รวม {s.sum():>15,.0f} บาท | "
              f"มัธยฐาน {s.median():>11,.0f} | สูงสุด {s.max():>14,.0f}")

    print(f"\n===== แยกตามช่วงราคา — สำคัญกว่ามัธยฐานตัวเดียว =====")
    print(f"  ระบบ UAV ทางทหารกับโดรนสำรวจของ อบต. ไม่ใช่ตลาดเดียวกัน")
    tot = awarded["ราคาตกลงซื้อ/จ้าง"].sum()
    for lo, hi, label in BANDS:
        s = awarded[(awarded["ราคาตกลงซื้อ/จ้าง"] >= lo)
                    & (awarded["ราคาตกลงซื้อ/จ้าง"] < hi)]["ราคาตกลงซื้อ/จ้าง"]
        if s.empty:
            continue
        print(f"  {label:<14} {len(s):>4} โครงการ ({len(s)/len(awarded)*100:>4.1f}%) | "
              f"รวม {s.sum():>14,.0f} บาท ({s.sum()/tot*100:>4.1f}% ของมูลค่า)")

    print(f"\n===== ประเภทโครงการ =====")
    for kind, c in drone["ชื่อประเภทโครงการ"].value_counts().head(6).items():
        sub = awarded[awarded["ชื่อประเภทโครงการ"] == kind]["ราคาตกลงซื้อ/จ้าง"]
        print(f"  {str(kind)[:30]:<32} {c:>4} โครงการ | {sub.sum():>14,.0f} บาท")

    print(f"\n===== 10 จังหวัดที่จัดซื้อโดรนมากที่สุด =====")
    for prov, c in drone["จังหวัด"].value_counts().head(10).items():
        v = awarded[awarded["จังหวัด"] == prov]["ราคาตกลงซื้อ/จ้าง"].sum()
        print(f"  {str(prov)[:22]:<24} {c:>4} โครงการ | {v:>14,.0f} บาท")

    print(f"\n===== คุณภาพ 'เลขนิติบุคคล' (ตัวที่ใช้เชื่อมกับ DBD) =====")
    for year, sub in df.groupby("_ปีงบ"):
        ok = int(sub["เลขนิติบุคคล_ใช้ได้"].sum())
        mark = "✅" if ok == len(sub) else "❌"
        print(f"  {mark} {year}: ใช้ได้ {ok}/{len(sub)}"
              + ("" if ok == len(sub) else "  ← Excel แปลงเป็น scientific notation กู้ไม่ได้"))

    print(f"\n===== 15 ผู้ขายรายใหญ่ (รวมชื่อที่เขียนต่างกันแล้ว) =====")
    top = (awarded.groupby("_ผู้ชนะ_ปรับชื่อ")["ราคาตกลงซื้อ/จ้าง"]
           .agg(["sum", "count"]).sort_values("sum", ascending=False).head(15))
    for key, r in top.iterrows():
        sub = awarded[awarded["_ผู้ชนะ_ปรับชื่อ"] == key]
        disp = sub["ชื่อผู้ชนะ"].iloc[0]
        ids = sub[sub["เลขนิติบุคคล_ใช้ได้"]]["เลขนิติบุคคล"].unique()
        jid = ids[0] if len(ids) else "— (เลขเสีย)"
        print(f"  {str(disp)[:36]:<38} {r['count']:>3} งาน | "
              f"{r['sum']:>14,.0f} บาท | {jid}")
    merged = len(awarded["ชื่อผู้ชนะ"].unique()) - len(awarded["_ผู้ชนะ_ปรับชื่อ"].unique())
    print(f"  (การปรับชื่อรวมผู้ขายที่เขียนต่างกันได้ {merged} ราย)")

    print(f"\n===== 10 หน่วยงานที่ซื้อมากที่สุด =====")
    for ag, c in drone["ชื่อหน่วยงาน"].value_counts().head(10).items():
        print(f"  {str(ag)[:40]:<42} {c:>4} โครงการ")

    print(f"\n===== คำที่ทำให้ match (ดูว่าคีย์เวิร์ดไหนได้ผล) =====")
    for kw, c in df["_คำที่พบ"].value_counts().items():
        print(f"  {kw:<22} {c:>4}")

    if problems:
        print(f"\n⚠️  มีไฟล์ที่อ่านไม่สำเร็จ {len(problems)} ไฟล์ — ตัวเลขข้างบนยังไม่ครบ:")
        for p in problems:
            print(f"    · {p}")

    # ---------- หมวดใหม่: ตลาดที่คีย์เวิร์ดชุดเดิมมองไม่เห็น ----------
    for kind in ["สำรวจทางอากาศ", "อุปกรณ์ทดสอบการบิน"]:
        raw = df[df["_หมวด"] == kind]
        if raw.empty:
            continue
        cut = raw[raw["_ตัดออกเพราะ"] != ""]
        sub = raw[raw["_ตัดออกเพราะ"] == ""]
        aw = sub[sub["ราคาตกลงซื้อ/จ้าง"].fillna(0) > 0]
        print(f"\n===== [หมวดใหม่] {kind} =====")
        print(f"  ก่อนคัดของปน {len(raw)} โครงการ | "
              f"{raw['ราคาตกลงซื้อ/จ้าง'].sum():,.0f} บาท")
        if len(cut):
            print(f"  ตัดของปนออก {len(cut)} โครงการ | "
                  f"{cut['ราคาตกลงซื้อ/จ้าง'].sum():,.0f} บาท:")
            for reason, g in cut.groupby("_ตัดออกเพราะ"):
                print(f"    - {reason}: {len(g)} โครงการ "
                      f"{g['ราคาตกลงซื้อ/จ้าง'].sum():,.0f} บาท")
        print(f"  **เหลือใช้ได้ {len(sub)} โครงการ | "
              f"{aw['ราคาตกลงซื้อ/จ้าง'].sum():,.0f} บาท** | "
              f"มัธยฐาน {aw['ราคาตกลงซื้อ/จ้าง'].median():,.0f} | "
              f"สูงสุด {aw['ราคาตกลงซื้อ/จ้าง'].max():,.0f}")
        print(f"\n  แยกขายของ/ขายบริการ (ใช้ฟิลด์ประเภทโครงการของราชการเอง):")
        for t, g in aw.groupby("_ชนิดงาน"):
            print(f"    {t:<12} {len(g):>4} โครงการ | {g['ราคาตกลงซื้อ/จ้าง'].sum():>14,.0f} บาท"
                  f" | มัธยฐาน {g['ราคาตกลงซื้อ/จ้าง'].median():>10,.0f}")
        print(f"\n  รายปี (หลังคัดของปนแล้ว):")
        for y, s in aw.groupby("_ปีงบ")["ราคาตกลงซื้อ/จ้าง"]:
            print(f"    {y}: {len(s):>4} งาน | {s.sum():>14,.0f} บาท")
        print(f"  ผู้ชนะรายใหญ่:")
        for k, r in (aw.groupby("_ผู้ชนะ_ปรับชื่อ")["ราคาตกลงซื้อ/จ้าง"]
                     .agg(["sum", "count"]).sort_values("sum", ascending=False)
                     .head(8).iterrows()):
            disp = aw[aw["_ผู้ชนะ_ปรับชื่อ"] == k]["ชื่อผู้ชนะ"].iloc[0]
            print(f"    {str(disp)[:38]:<40} {int(r['count']):>3} งาน | {r['sum']:>13,.0f}")
        print(f"  คำที่ทำให้ match:")
        for kw, c in sub["_คำที่พบ"].value_counts().items():
            print(f"    {kw:<22} {c:>4}")

    print(f"\n⚠️  ข้อจำกัด: จับคำจากชื่อโครงการเท่านั้น โครงการที่ซื้อโดรนแต่ตั้งชื่อ"
          f"\n    กว้าง ๆ (เช่น 'ครุภัณฑ์สำรวจ') จะไม่ถูกนับ → ตัวเลขเป็นค่า 'อย่างน้อย'")
    print(f"\n⚠️  หมวด 'สำรวจทางอากาศ' อาจมีงานที่ใช้เครื่องบินมีคนขับหรือภาพดาวเทียม"
          f"\n    ปนอยู่ (คีย์เวิร์ดบอกไม่ได้ว่าถ่ายจากอะไร) และ 'ไลดาร์' บางงาน"
          f"\n    เป็นแบบติดรถ ไม่ใช่ทางอากาศ → ถือเป็น 'ตลาดข้างเคียง' ไม่ใช่ตลาดโดรนล้วน")


if __name__ == "__main__":
    main()
