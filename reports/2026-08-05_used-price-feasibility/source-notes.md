# Source notes — ความเป็นไปได้ของราคามือสอง

วันที่ตรวจ: 5 สิงหาคม 2569

> ⚠️ **ตัวเลขในรายงานนี้เป็นสถานะของ pipeline ณ เช้าวันที่ 5 ส.ค. 2569** หลังจากนั้น
> `nbtc_pricing` ถูกทำต่ออีกสองรอบ (แก้ยี่ห้อที่กรอกมั่วชุด MG/DJT/3WWDSZ · เก็บราคาโดรนเกษตร
> เพิ่ม · เพิ่มเส้นราคาต่อความจุถัง) ตัวเลขปัจจุบันจึงต่างออกไป
>
> | | ในรายงานนี้ | ปัจจุบัน |
> |---|---:|---:|
> | ตั้งราคาได้ | 166,977 ลำ (81.34%) | **168,728 ลำ (82.2%)** |
> | ยังไม่มีราคา | 38,310 ลำ | **36,559 ลำ** |
>
> ข้อสรุปหลักของรายงาน (47 รูปเขียน = 1,129 ลำ ที่จับคู่ราคาเดิมได้โดยไม่ต้องหาราคาใหม่)
> **ยังไม่ได้ตรวจซ้ำกับสถานะใหม่** — บางส่วนถูกดูดไปแล้วด้วยตาราง `nbtc_code_map.csv`
> ที่เพิ่มเข้ามาทีหลัง ตัวเลขจริงที่เหลือน่าจะน้อยกว่านี้
>
> สถานะล่าสุดดูที่ [`reports/2026-08-04_nbtc-unit-value/README.md`](../2026-08-04_nbtc-unit-value/README.md)

## คำถามและขอบเขต

ประเมินว่าราคามือสองช่วยเติมราคาของรุ่นที่ยังไม่มีราคาใน pipeline `nbtc_pricing` ได้หรือไม่ โดยสแกนทั้งโปรเจกต์ก่อน และไม่แก้ข้อมูลอ้างอิงหรือสคริปต์เดิมในรอบนี้

## แหล่งข้อมูลในโปรเจกต์

- `data/processed/nbtc_pricing/unpriced_models.csv` — 1,996 คู่ brand-model รวม 38,310 ลำ
- `data/reference/nbtc_model_prices.csv` — ราคาอ้างอิง 47 รุ่น
- `data/reference/nbtc_code_map.csv` — การแก้รหัส/ยี่ห้อด้วยหลักฐานภายนอก
- `data/processed/nbtc_pricing/model_catalog.csv` — แคตตาล็อก 2,070 คู่ brand-model
- `scripts/nbtc_pricing/01_build_model_catalog.py` — กติกาแยกชื่อรุ่นและชุดขาย
- `scripts/nbtc_pricing/03_estimate_market_value.py` และ `03_estimate_market_value_out.txt` — การจับคู่ราคาและผลล่าสุด
- `reports/2026-08-04_nbtc-unit-value/README.md` — รายงานเดิมและข้อจำกัด

## ตัวเลขที่คำนวณซ้ำ

- จำนวนทะเบียนทั้งหมด: 205,287 ลำ
- ตั้งราคาได้ตาม output ล่าสุด: 166,977 ลำ หรือ 81.34%
- ยังไม่มีราคา: 38,310 ลำ หรือ 18.66%
- `README.md` เดิมมี headline ค้างจากรอบก่อนที่ 165,459 ลำและ 39,828 ลำ ขณะที่ตารางภายในและ output ล่าสุดเป็น 166,977/38,310 ลำ

## การตรวจ alias ที่ยังจับคู่ราคาไม่ติด

เปรียบเทียบชื่อรุ่นใน `unpriced_models.csv` กับ `nbtc_model_prices.csv` ภายในยี่ห้อเดียวกัน หลังแปลงเป็นตัวพิมพ์ใหญ่ ตัดช่องว่าง/เครื่องหมาย และตัดคำชุดขาย เช่น `FLY MORE COMBO`, `FLYMORE`, `COMBO`, `MOTION` พบ 47 รูปเขียน รวม 1,129 ลำ ที่จับคู่กับราคาเดิมได้โดยไม่ต้องหาราคาใหม่

ตัวอย่างที่มีผลสูง:

- DJI NEO MOTION → NEO: 324 ลำ
- DJI NEO 2 MOTION → NEO 2: 86 ลำ
- MINI3 PRO / MINI 3PRO / MINI3PRO → MINI 3 PRO: หลายรูปเขียนรวมมากกว่า 160 ลำ
- MAVIC PRO FLYMORE → MAVIC PRO: 64 ลำ

การตรวจนี้เป็น candidate generation ไม่ใช่การอนุมัติ alias อัตโนมัติ ต้อง review รายการก่อนเพิ่มกติกาใน `MODEL_ALIAS`/การตัดคำชุดขาย

## รุ่นปัจจุบันที่ควรใช้ราคาป้ายใหม่ก่อนราคามือสอง

ห้ารุ่นรวม 7,740 ลำ:

- DJI AIR 3S: 3,861 ลำ — ราคาไทย 34,990 บาท (RC-N3)
- DJI MAVIC 3 CLASSIC: 1,132 ลำ — ราคาตัวลำไทย 50,500 บาท; มีชุด DJI RC ที่ 59,100 บาท จึงต้องยึดนิยาม bundle เดียวกับตารางราคา
- DJI AVATA: 1,175 ลำ — แหล่งไทยพบ 19,300–32,900 บาท แต่ชุดขายไม่เหมือนกัน ต้อง normalize ก่อนเลือกค่า
- DJI AVATA 360: 818 ลำ — ราคาไทย 20,290 บาทในหน้าร้านที่ตรวจ
- DJI MAVIC 4 PRO: 754 ลำ — ราคาไทย 73,990 บาท

ถ้าแก้ alias 1,129 ลำและเติมราคาป้ายห้ารุ่นนี้ coverage จะขยับจาก 81.34% เป็น 85.66% โดยยังไม่ใช้ราคามือสอง

## กลุ่มทดลองราคามือสอง

เลือก pilot รุ่นเก่าที่เลิกขาย/หาป้ายใหม่ที่เทียบกันยากและมีจำนวนจดทะเบียนสูง:

- DJI PHANTOM 3 PRO: 699 ลำ
- DJI PHANTOM 3 ADV: 462 ลำ
- DJI MAVIC PRO PLATINUM: 640 ลำ

รวม 1,801 ลำ หากตั้งราคาได้ครบ coverage เชิงศักยภาพจะเป็น 86.54% แต่อย่าเพิ่มเข้าตัวเลขหลักจนกว่าจะมีตัวอย่างประกาศที่ผ่านกติกาอย่างน้อย 3 รายการต่อรุ่นจากอย่างน้อย 2 แหล่ง

หลักฐานออนไลน์ยืนยันว่าตลาดมือสองมีจริง แต่ผลค้นหาปนอะไหล่ ชุดขาย และประกาศเก่าอย่างมาก:

- Priceza พบ Phantom 3 Professional มือสองครบชุด 16,500 บาท พร้อมรายละเอียดแบตเตอรี่ 3 ก้อน
- Kaidee พบ Avata 2 FPV Set มือสอง 11,900 บาท เป็นตัวอย่างว่าประกาศไทยมีราคาและ bundle แต่รุ่นนี้มีราคาอ้างอิงอยู่แล้ว
- Leboncoin มี Phantom 3 Advanced หลายสิบประกาศ แต่เป็นตลาดฝรั่งเศส จึงใช้ตรวจความพร้อมของตลาดรองได้ ไม่ควรย้ายราคาเป็นบาทตรง ๆ

## กติกาที่ควรใช้กับข้อมูลมือสอง

หน่วยมาตรฐาน: ตัวเครื่อง + รีโมต + แบตเตอรี่ใช้งานได้ 1 ก้อน

ตัดออก:

- อะไหล่ ตัวลำเปล่า เครื่องเสีย หรือประกาศรับซื้อ
- ชุดที่รวมแบตเตอรี่/แว่น/กระเป๋า/เซนเซอร์จำนวนมากแต่แยกมูลค่าไม่ได้
- cross-post หรือประกาศซ้ำ
- ประกาศไม่มีวันที่ ไม่มีสถานะ หรือราคาที่เป็นมัดจำ/ผ่อนต่อเดือน

ฟิลด์ขั้นต่ำ:

- brand, model, asking_price, currency, country
- listing_url, listing_date, captured_at, listing_status
- condition_grade, bundle_type, battery_count, battery_cycles
- seller_type, source, duplicate_group, inclusion_reason

สรุปราคาต่อรุ่นด้วย median และช่วง IQR; เก็บจำนวนประกาศและจำนวนแหล่งไว้ด้วย ราคาประกาศเป็น asking price ไม่ใช่ราคาปิดการขาย จึงให้ confidence ต่ำกว่าราคาป้ายร้านและควรอยู่ใน sensitivity/ช่วงประมาณการก่อน

## แหล่งออนไลน์ที่ตรวจ

- DJI Air 3S, JIB: https://www.jib.co.th/web/product/readProduct/71287/951/DRONE--%E0%B9%82%E0%B8%94%E0%B8%A3%E0%B8%99--DJI-AIR-3S--DJI-RC-N3-
- DJI Mavic 3 Classic, KRCSHOP: https://krcshop.net/main/product-detail.asp?productid=73
- DJI Mavic 4 Pro, DJI Store Thailand: https://djistore-thailand.com/products/dji-mavic-4-pro
- DJI Avata, BIGCamera: https://www.bigcamera.co.th/dji-avata
- DJI Avata, Aquapro: https://www.aquapro.co.th/product/dji-avata/
- DJI Avata 360, BIGCamera: https://www.bigcamera.co.th/dji-avata-360
- DJI MG-1P, DJI Reseller: https://www.toon-ocean.com/shop/dji-mg-1p/
- NAC Drone EASY family, R3solarcell: https://www.r3solarcell.com/category/10/%E0%B9%82%E0%B8%94%E0%B8%A3%E0%B8%99%E0%B9%80%E0%B8%81%E0%B8%A9%E0%B8%95%E0%B8%A3
- DJI Phantom 3 Professional มือสอง, Priceza: https://www.priceza.com/s/%E0%B8%A3%E0%B8%B2%E0%B8%84%E0%B8%B2/dji-phantom-3-professional
- DJI Phantom 3 Advanced มือสอง, Leboncoin: https://www.leboncoin.fr/ck/photo_audio_video/phantom-3-advanced
- ตัวอย่างประกาศมือสอง Kaidee: https://www.kaidee.com/c28-cameras/p-17?condition=2

## Chart map

- ส่วน: ผลกระทบต่อ coverage
- คำถาม: แต่ละลำดับงานเพิ่มสัดส่วนลำที่มีราคาได้เท่าไร
- รูปแบบ: bar, single series
- fields: stage, coverage_pct; เก็บ priced_units และ remaining_units ใน dataset เพื่อ audit
- palette: single-root blue
- caveat: ขั้นราคามือสองเป็นศักยภาพของ pilot 3 รุ่น ไม่ใช่ราคาที่อนุมัติแล้ว

## Validation

- `market_value_by_model.csv` รวม 166,977 ลำ และ `unpriced_models.csv` รวม 38,310 ลำ; รวมกลับได้ 205,287 ลำตรงกับฐานทะเบียน
- ก้อนงาน 1,129 + 7,740 + 1,801 + 27,640 รวม 38,310 ลำพอดี
- คำนวณ coverage ซ้ำได้ 81.34%, 81.89%, 85.66% และ 86.54% ตามลำดับ
- ตารางราคา 47 แถวไม่มี key `(brand, model)` ซ้ำ และไม่มีแถวที่ขาด source, URL, as-of หรือ confidence
- `report.html` ผ่าน validation และ packaging; verification เป็น `structural_only` เพราะไม่พบ Chromium ที่ติดตั้งไว้ จึงไม่ได้ตรวจ interaction/viewport ของ enhanced reader แต่ payload equality, semantic fallback และ self-contained packaging ผ่าน

## การแมปโครงสร้างรายงาน

- Title → ชื่อรายงาน
- Executive Summary → สรุปคำตอบ
- Key findings with visual evidence → ส่วน coverage และตารางลำดับงาน
- Recommended next steps → ลำดับทดลอง 4 ขั้น
- Further questions → คำถามที่เปลี่ยนข้อสรุปได้
- Caveats and assumptions → ข้อจำกัดของ asking price, bundle, condition และฐานราคาปัจจุบัน
