# Source notes: NBTC pricing executive report

## Reporting job

- Question: ทะเบียนโดรนของ กสทช. บอกมูลค่าตามราคาต่อลำที่มีหลักฐานในปี 2568 ได้เท่าไร และเซกเมนต์ใดขับมูลค่าหลัก
- Audience: หัวหน้า ผู้บริหาร และพนักงานทั่วไป
- Decision supported: ทำความเข้าใจขนาดและโครงสร้างของมูลค่าโดรน พร้อมแยกค่าที่วัดได้ออกจากค่าปรับ coverage และเห็นขอบเขตงานที่ยังดำเนินต่อ
- Scope: โดรนที่จดทะเบียนในประเทศไทย ปีปฏิทิน 2568 คูณราคาต่อลำที่มีหลักฐาน โดยฐานชุดขายต่างกันตามรุ่น
- Exclusions: ไม่ได้ประเมินตลาดอุปกรณ์เสริมแยกต่างหาก ซอฟต์แวร์ การติดตั้ง การอบรม บริการบิน ลำที่ไม่จดทะเบียน และยอดขายที่ไม่มีหลักฐานจากทะเบียน; อุปกรณ์ที่รวมอยู่ในชุดขายอาจอยู่ในค่าประมาณแล้ว
- Primary comparison: มูลค่าที่วัดได้เทียบกับค่าปรับ coverage และองค์ประกอบจำนวนลำเทียบกับองค์ประกอบมูลค่า

## Report spine

- Decision-useful answer: วัดมูลค่าได้ 1,973 ล้านบาทจาก coverage 76%; ค่าปรับ coverage เท่ากับ 2,594 ล้านบาทและต้องแยกป้ายจากค่าที่วัดได้
- Main driver: บนฐานราคาที่รวบรวมได้ โดรนเกษตร 13.8% ของลำที่ตั้งราคาได้ แต่ 62.1% ของมูลค่าสะสม
- Validation: จำนวน AGRAS เทียบศุลกากร และการแปลงมูลค่าที่ประเมินเป็นฐานเทียบนำเข้า
- Material caveats: ทะเบียนไม่ใช่ยอดขาย, ไม่มีเลขเครื่อง, ฐานชุดขายต่างกันตามรุ่น, ใช้ราคาเดียวต่อรุ่นทุกปี, coverage ต่างกันตามปี, ปี 2560/2569 ไม่ครบปี
- Next action: ขยายหลักฐานราคาทุกกลุ่มแบบค่อยเป็นค่อยไป โดยเริ่มจากรุ่นที่มียอดจดสูงและมีหลักฐานตรวจสอบได้

## Executive structure mapping

| Required role | Visible section |
|---|---|
| Title | มูลค่าโดรนที่จดทะเบียนในไทย ปี 2568 |
| Executive Summary | บทสรุปผู้บริหาร (Executive Summary) |
| Key findings with evidence | ผลปี 2568, แนวโน้มปีเต็ม, องค์ประกอบโดรนเกษตร |
| Recommended next steps | เปลี่ยนเป็น “สิ่งที่ดำเนินต่อ” เพื่อรายงานสถานะงานโดยไม่สั่งการผู้อ่าน |
| Further questions | รวมไว้ใน “สิ่งที่ดำเนินต่อ”: หลักฐานราคาของรุ่นที่ยังขาด, coverage และขอบเขตตลาดรวม |
| Caveats and assumptions | ข้อจำกัดที่ต้องติดไปกับตัวเลข |

## Chart map

| Section | Analytical question | Family / type | Fields | Supported claim | Palette policy |
|---|---|---|---|---|---|
| ผลรายปี | มูลค่าที่วัดได้และค่าปรับ coverage เปลี่ยนอย่างไรในปีเต็ม 2561-2568 | Trend / two-series line | year_be, series, value_m; coverage in tooltip | ปี 2567→2568 เพิ่ม 5.0% บนฐานที่วัดได้ เทียบ 18.2% บนสมมติฐานปรับ coverage จึงห้ามอ้างอัตราเดียว | Blue measured series; gold dashed adjusted series |
| กลุ่มการใช้งาน | จำนวนลำและมูลค่ากระจุกต่างกันอย่างไร | Composition / stackedBar100 | measure, share, segment | โดรนเกษตรมีสัดส่วนมูลค่าสูงกว่าสัดส่วนจำนวนลำมาก | Two categorical roots plus direct percentage tooltips |

## Independent validation spot-checks

- 2568 registrations: 43,129; priced: 32,804; coverage: 0.7606019152
- 2568 measured value: 1,972,726,269 บาท
- 2568 coverage-adjusted value: 2,593,638,314 บาท
- Cumulative priced units: 168,728; cumulative measured value: 8,732,018,078 บาท
- Agriculture: 23,318 units and 5,423,565,600 บาท; shares 13.8199% and 62.1113%
- Top 10 models by cumulative measured value: 8 agriculture models
- 2568 coverage adjustment gap: 620.9 ล้านบาท; 2,593.6 ล้านบาทคือยอดหลังปรับ ไม่ใช่ส่วนต่าง
- 2568 import-equivalent check: 1,474.9-1,676.1 ล้านบาท; ขอบบนต่ำกว่าพื้นศุลกากร 0.06% และขอบล่างต่ำกว่า 12.0% (แก้จาก 0.04% เมื่อ 11 ส.ค. 2569 — ค่าเดิมพิมพ์เอง ไม่ได้ออกจากสคริปต์)
- Price basis sensitivity: 44,577 ลำ หรือ 15.6% ของมูลค่าสะสมที่วัดได้ ใช้ราคาสัญญาภาครัฐหรือกติกาอนุมาน
- รุ่นที่ยังไม่มีราคา 1,979 รุ่น; 1,724 รุ่น (87.1%) มียอดจดไม่เกิน 10 ลำต่อรุ่น รวม 2,984 ลำ หรือเพิ่ม coverage ได้ประมาณ 1.5 จุดเปอร์เซ็นต์หากเติมได้ครบทั้งกลุ่ม

## QA refresh: 10 August 2026

- `validate_report.mjs` คำนวณซ้ำจาก `registrations_by_model_year.csv`, ตารางราคา, code map และ model tiers โดยไม่ใช้ยอดสรุปเดิมเป็นฐาน รวมทั้งตรวจข้อค้นพบเรื่องรุ่นยอดจดต่ำและการเปิดเผยฐานชุดขายที่ต่างกันตามรุ่น
- ยอดรายปี รายรุ่น ส่วนที่ไม่มีราคา สูตร coverage สูตรฐานนำเข้า และข้อมูลใน `artifact.json` รวมกลับตรงกับไฟล์ต้นทาง
- ตาราง code map, ราคา และ tier ไม่มีคีย์ซ้ำ; ราคาทั้ง 52 แถวมี source, URL และวันที่ตรวจครบ
- ไฟล์ทะเบียนดิบมี 205,287 แถว ตรงกับผลประมวลผล; วันที่อนุมัติและ Brand ไม่ขาด ส่วน Purpose ขาด 6,087 แถว (3.0%), Model ขาด 6 แถว และ Frequency ขาด 4,691 แถว
- มี 50,557 แถวที่ข้อมูลเหมือนแถวก่อนหน้าอื่นบน 6 ฟิลด์ที่เปิดเผย แต่ไม่มี serial/registration id จึงแยกไม่ได้ว่าเป็นการจดซ้ำหรือหลายลำที่มีคุณสมบัติเหมือนกัน ประเด็นนี้คงไว้เป็น caveat ไม่ตัดแถวทิ้ง
- ไม่มีรุ่นที่ตั้งราคาได้ซึ่งมีสัดส่วนการใช้งานเกษตรอยู่ใกล้เส้นแบ่ง 60% ในช่วง 40%-80% จึงไม่พบความไวของข้อสรุป segment ต่อ threshold ในชุดราคาปัจจุบัน
- Runtime นี้ไม่มี Python จึงไม่ได้ re-execute notebook/pipeline เดิม; ใช้ Node audit ที่จำลองกติกาเดิมและเทียบผลรายปี/รายรุ่นแทน Notebook ที่บันทึกไว้ไม่มี error output
- ฉบับ PDF แสดงที่มาของข้อมูลในภาษาที่ผู้อ่านทั่วไปเข้าใจได้ และซ่อนเส้นทางไฟล์ คำสั่ง และรายละเอียดระบบซึ่งเก็บไว้ใน HTML/source notes สำหรับการตรวจสอบย้อนหลัง
- PDF ฉบับส่งต่อมี 4 หน้าและผ่าน visual QA ครบทุกหน้าหลังการแก้ไข

## Price-basis clarification: 10 August 2026

- ตัวเลขหลักยังใช้ `price_thb` ของแต่ละรุ่นหลังผ่านกติกากันราคาผกผัน; สูตร มูลค่า coverage และกราฟไม่เปลี่ยน
- `nbtc_model_prices.csv` มีทั้งฐานตัวเปล่า ตัวเครื่อง ชุดพร้อมบิน ชุดคอมโบ สัญญาภาครัฐ และการอนุมาน จึงตัดคำว่า “ไม่รวมอุปกรณ์ประกอบ” ออกจากรายงาน
- รายงานระบุแทนว่าไม่ได้ประเมินตลาดอุปกรณ์เสริมแยกต่างหาก แต่อุปกรณ์ที่ติดอยู่ในชุดขายอาจรวมอยู่ในราคาต่อลำแล้ว
- ตัวตรวจ HS 8806 ถูกลดน้ำหนักเป็นการตรวจระดับคร่าว ๆ เพราะราคาชุดพร้อมบินบางรุ่นอาจรวมอุปกรณ์ที่อยู่คนละพิกัดศุลกากร

## Validation assessment

Share with caveats. The calculations used in the executive report reconcile from registration-level aggregates through the pricing join and into the report artifact. The main remaining risks are lack of a unique aircraft identifier, incomplete price coverage, mixed price evidence, and year-varying coverage rather than arithmetic. The report therefore labels measured value, coverage adjustment, market scope, price-basis sensitivity, and incomplete periods separately.

## สคริปต์ในโฟลเดอร์นี้ — ตัวไหนรันได้เอง ตัวไหนไม่ได้ (บันทึก 11 ส.ค. 2569)

| ไฟล์ | รันหลัง clone ได้ไหม |
|---|---|
| `build_report_artifact.mjs` | ✅ อ่าน CSV ใน `data/processed/nbtc_pricing/` ตรง ๆ |
| `validate_report.mjs` | ✅ ตรวจ 25 จุดจาก CSV ชุดเดียวกัน |
| `audit_raw_registration.mjs` | ✅ |
| `build_static_report.mjs` | ❌ **ต้องมีปลั๊กอินภายนอกก่อน** |

`build_static_report.mjs` บรรทัดที่ 6 ปัก path ไว้ตายตัวที่
`C:/Users/forge/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.8-13ceeea1f599`
แล้ว `import` โมดูล `build_portable_artifact.mjs` กับ `verify_portable_artifact.mjs` จากตรงนั้น
ปลั๊กอินไม่ได้อยู่ใน repo → **clone ไปเครื่องอื่นแล้วรันไม่ได้ และเวอร์ชันปลั๊กอินก็ถูกปักไว้**
ถ้าปลั๊กอินอัปเดตเมื่อไร ต่อให้เครื่องเดิมก็พัง

ผลกระทบจำกัดอยู่แค่ขั้น "แปลง `artifact.json` เป็น `report.html`" เท่านั้น
ตัวเลขทั้งหมดถูกสร้างและตรวจโดยอีก 3 ตัวที่รันได้เอง และ `report.html` กับ PDF
ที่ build ไว้แล้วก็อยู่ในโฟลเดอร์นี้ครบ — ต้องรันตัวนี้ใหม่ก็ต่อเมื่อจะเปลี่ยนหน้าตารายงาน

## Omitted detail

- Code dictionaries, conflicts, monotonic-price rules, capacity-curve coefficients, source URLs by model, and pipeline commands remain in the technical notebook and internal method note.
- A model leaderboard was omitted because the executive report needs the market structure rather than a model-by-model ranking; the verified statement that 8 of the top 10 models are agricultural is sufficient for this version.
- The 2569 partial-year result was omitted from the main visual to avoid comparison with complete calendar years.
