import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");

function parseCsv(text) {
  text = text.replace(/^\uFEFF/, "");
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"' && text[index + 1] === '"') {
        cell += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        cell += char;
      }
      continue;
    }
    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      row.push(cell.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (cell.length || row.length) {
    row.push(cell.replace(/\r$/, ""));
    rows.push(row);
  }

  const [headers, ...records] = rows.filter((item) => item.some((value) => value !== ""));
  return records.map((record) => Object.fromEntries(headers.map((header, index) => [header, record[index] ?? ""])));
}

function loadCsv(relativePath) {
  return parseCsv(readFileSync(resolve(root, relativePath), "utf8"));
}

function quoteIdentifier(value) {
  return `"${String(value).replaceAll('"', '""')}"`;
}

function loadTable(database, tableName, rows) {
  const columns = Object.keys(rows[0] ?? {});
  if (!columns.length) throw new Error(`Cannot load empty table ${tableName}`);
  database.exec(`CREATE TABLE ${quoteIdentifier(tableName)} (${columns.map((column) => `${quoteIdentifier(column)} TEXT`).join(", ")});`);
  const insert = database.prepare(`INSERT INTO ${quoteIdentifier(tableName)} (${columns.map(quoteIdentifier).join(", ")}) VALUES (${columns.map(() => "?").join(", ")});`);
  database.exec("BEGIN");
  try {
    for (const row of rows) insert.run(...columns.map((column) => row[column]));
    database.exec("COMMIT");
  } catch (error) {
    database.exec("ROLLBACK");
    throw error;
  }
}

function sum(rows, field) {
  return rows.reduce((total, row) => total + Number(row[field] || 0), 0);
}

function approximately(actual, expected, tolerance = 0.5) {
  if (Math.abs(actual - expected) > tolerance) {
    throw new Error(`Validation failed: expected ${expected}, received ${actual}`);
  }
}

const database = new DatabaseSync(":memory:");
loadTable(database, "market_value_by_year", loadCsv("data/processed/nbtc_pricing/market_value_by_year.csv"));
loadTable(database, "market_value_by_model", loadCsv("data/processed/nbtc_pricing/market_value_by_model.csv"));
loadTable(database, "unpriced_models", loadCsv("data/processed/nbtc_pricing/unpriced_models.csv"));
loadTable(database, "import_basis_check", loadCsv("data/processed/nbtc_pricing/import_basis_check.csv"));

const annualSql = "SELECT * FROM market_value_by_year;";
const modelSql = "SELECT * FROM market_value_by_model;";
const unpricedSql = "SELECT * FROM unpriced_models;";
const importSql = "SELECT * FROM import_basis_check;";
const yearRows = database.prepare(annualSql).all();
const modelRows = database.prepare(modelSql).all();
const unpricedRows = database.prepare(unpricedSql).all();
const importRows = database.prepare(importSql).all();

const year2025 = yearRows.find((row) => row.year === "2025");
if (!year2025) throw new Error("The 2025 market-value row is missing.");

const agricultureRows = modelRows.filter((row) => row.class === "เกษตร");
const generalRows = modelRows.filter((row) => row.class === "ทั่วไป");
const pricedUnits = sum(modelRows, "units");
const pricedValue = sum(modelRows, "val");
const agricultureUnits = sum(agricultureRows, "units");
const agricultureValue = sum(agricultureRows, "val");
const generalUnits = sum(generalRows, "units");
const generalValue = sum(generalRows, "val");
const topTen = [...modelRows].sort((a, b) => Number(b.val) - Number(a.val)).slice(0, 10);
const topTenAgriculture = topTen.filter((row) => row.class === "เกษตร").length;
const unpricedUnits = sum(unpricedRows, "units");
const lowVolumeUnpricedRows = unpricedRows.filter((row) => Number(row.units) <= 10);
const lowVolumeUnpricedUnits = sum(lowVolumeUnpricedRows, "units");
const registrationUnits = pricedUnits + unpricedUnits;

approximately(Number(year2025.units_all), 43129);
approximately(Number(year2025.units), 32804);
approximately(Number(year2025.coverage), 0.7606019151846786, 0.0000001);
approximately(Number(year2025.val), 1972726269);
approximately(Number(year2025.val_scaled), 2593638314.098921, 1);
approximately(pricedUnits, 168728);
approximately(pricedValue, 8732018078);
approximately(agricultureUnits / pricedUnits, 0.138198757763975, 0.0000001);
approximately(agricultureValue / pricedValue, 0.621112502465435, 0.0000001);
approximately(topTenAgriculture, 8);
approximately(unpricedRows.length, 1979);
approximately(lowVolumeUnpricedRows.length, 1724);
approximately(lowVolumeUnpricedUnits, 2984);

const fullYearTrend = yearRows
  .filter((row) => Number(row.year) >= 2018 && Number(row.year) <= 2025)
  .map((row) => ({
    year_be: String(Number(row.year) + 543),
    measured_m: Number((Number(row.val) / 1_000_000).toFixed(1)),
    adjusted_m: Number((Number(row.val_scaled) / 1_000_000).toFixed(1)),
    coverage: Number(row.coverage),
    registrations: Number(row.units_all),
    priced_units: Number(row.units),
  }));

const fullYearTrendSeries = fullYearTrend.flatMap((row) => [
  {
    year_be: row.year_be,
    series: "มูลค่าที่วัดได้",
    value_m: row.measured_m,
    coverage: row.coverage,
    registrations: row.registrations,
    priced_units: row.priced_units,
  },
  {
    year_be: row.year_be,
    series: "ค่าปรับ coverage",
    value_m: row.adjusted_m,
    coverage: row.coverage,
    registrations: row.registrations,
    priced_units: row.priced_units,
  },
]);

const composition = [
  { measure: "จำนวนลำ", segment: "โดรนทั่วไป", share: generalUnits / pricedUnits, units: generalUnits, value_m: generalValue / 1_000_000 },
  { measure: "จำนวนลำ", segment: "โดรนเกษตร", share: agricultureUnits / pricedUnits, units: agricultureUnits, value_m: agricultureValue / 1_000_000 },
  { measure: "มูลค่า", segment: "โดรนทั่วไป", share: generalValue / pricedValue, units: generalUnits, value_m: generalValue / 1_000_000 },
  { measure: "มูลค่า", segment: "โดรนเกษตร", share: agricultureValue / pricedValue, units: agricultureUnits, value_m: agricultureValue / 1_000_000 },
];

const import2025 = importRows.find((row) => row.year === "2025");
if (!import2025) throw new Error("The 2025 import-basis validation row is missing.");

const summary = [{
  measured_m: Number((Number(year2025.val) / 1_000_000).toFixed(0)),
  adjusted_m: Number((Number(year2025.val_scaled) / 1_000_000).toFixed(0)),
  coverage: Number(year2025.coverage),
  priced_units: Number(year2025.units),
  registrations: Number(year2025.units_all),
  agriculture_value_share: agricultureValue / pricedValue,
  agriculture_unit_share: agricultureUnits / pricedUnits,
  top_ten_agriculture_models: topTenAgriculture,
}];

const validation = [{
  retail_m: Number((Number(import2025.retail) / 1_000_000).toFixed(1)),
  import_basis_low_m: Number((Number(import2025.imp_lo) / 1_000_000).toFixed(1)),
  import_basis_high_m: Number((Number(import2025.imp_hi) / 1_000_000).toFixed(1)),
  customs_total_m: Number((Number(import2025.customs_import) / 1_000_000).toFixed(1)),
}];

const unpricedSummary = [{
  unpriced_models: unpricedRows.length,
  low_volume_models: lowVolumeUnpricedRows.length,
  low_volume_model_share: lowVolumeUnpricedRows.length / unpricedRows.length,
  low_volume_units: lowVolumeUnpricedUnits,
  registration_units: registrationUnits,
  coverage_point_impact: lowVolumeUnpricedUnits / registrationUnits,
}];

const generatedAt = "2026-08-10T09:00:00+07:00";
const title = "มูลค่าโดรนที่จดทะเบียนในไทย ปี 2568";

const manifestSources = [
  { id: "annual_value", label: "มูลค่ารายปีจากทะเบียน กสทช. และราคาต่อลำ", path: "data/processed/nbtc_pricing/market_value_by_year.csv" },
  { id: "model_value", label: "มูลค่าและจำนวนลำแยกรายรุ่น", path: "data/processed/nbtc_pricing/market_value_by_model.csv" },
  { id: "unpriced_models", label: "รุ่นที่ยังไม่มีหลักฐานราคาและจำนวนลำจดทะเบียน", path: "data/processed/nbtc_pricing/unpriced_models.csv" },
  { id: "price_evidence", label: "ราคาต่อลำและฐานชุดขายรายรุ่น", path: "data/reference/nbtc_model_prices.csv" },
  { id: "import_check", label: "ผลแปลงมูลค่าที่ประเมินเป็นฐานเทียบนำเข้า", path: "data/processed/nbtc_pricing/import_basis_check.csv" },
  { id: "method_note", label: "หลักการ วิธีคำนวณ และข้อจำกัดของ NBTC pricing", path: "reports/2026-08-04_nbtc-unit-value/README.md" },
];

const sources = [
  {
    id: "annual_value",
    label: "มูลค่ารายปีจากทะเบียน กสทช. และราคาต่อลำ",
    path: "data/processed/nbtc_pricing/market_value_by_year.csv",
    query: {
      engine: "sqlite",
      language: "sql",
      sql: annualSql,
      executed_at: generatedAt,
      description: "สรุปจำนวนลำ มูลค่าที่ตั้งราคาได้ coverage และค่าปรับ coverage รายปี",
      tables_used: ["data/processed/nbtc_pricing/market_value_by_year.csv"],
      filters: ["รายงานหลักใช้ปีปฏิทิน 2568 ซึ่งมีข้อมูลครบ 12 เดือน", "กราฟแนวโน้มใช้เฉพาะปีเต็ม 2561-2568"],
      metric_definitions: [
        "มูลค่าที่วัดได้ = ผลรวมจำนวนลำที่จับคู่ราคาได้ คูณราคาต่อลำของแต่ละรุ่น",
        "coverage = จำนวนลำที่จับคู่ราคาได้ หารด้วยจำนวนลำจดทะเบียนทั้งหมดของปี",
        "ค่าปรับ coverage = มูลค่าที่วัดได้ หารด้วย coverage; เป็นสมมติฐาน ไม่ใช่ช่วงความเชื่อมั่น",
      ],
    },
  },
  {
    id: "model_value",
    label: "มูลค่าและจำนวนลำแยกรายรุ่น",
    path: "data/processed/nbtc_pricing/market_value_by_model.csv",
    query: {
      engine: "sqlite",
      language: "sql",
      sql: modelSql,
      executed_at: generatedAt,
      description: "สรุปจำนวนลำและมูลค่าที่ตั้งราคาได้ แยกตามรุ่นและกลุ่มการใช้งาน",
      tables_used: ["data/processed/nbtc_pricing/market_value_by_model.csv"],
      filters: ["รวมทะเบียนปี 2560-2569", "นับเฉพาะลำที่จับคู่ราคาได้"],
      metric_definitions: [
        "สัดส่วนจำนวนลำ = จำนวนลำของกลุ่ม หารด้วยจำนวนลำที่จับคู่ราคาได้ทั้งหมด",
        "สัดส่วนมูลค่า = มูลค่าของกลุ่ม หารด้วยมูลค่าที่จับคู่ราคาได้ทั้งหมด",
      ],
    },
  },
  {
    id: "unpriced_models",
    label: "รุ่นที่ยังไม่มีหลักฐานราคาและจำนวนลำจดทะเบียน",
    path: "data/processed/nbtc_pricing/unpriced_models.csv",
    query: {
      engine: "sqlite",
      language: "sql",
      sql: unpricedSql,
      executed_at: generatedAt,
      description: "สรุปจำนวนลำของแต่ละรุ่นที่ยังจับคู่กับหลักฐานราคาไม่ได้",
      tables_used: ["data/processed/nbtc_pricing/unpriced_models.csv"],
      filters: ["รวมทะเบียนปี 2560-2569", "กลุ่มรุ่นยอดจดต่ำหมายถึงไม่เกิน 10 ลำต่อรุ่น"],
      metric_definitions: [
        "สัดส่วนรุ่นยอดจดต่ำ = จำนวนรุ่นที่จดไม่เกิน 10 ลำ หารด้วยจำนวนรุ่นที่ยังไม่มีราคาทั้งหมด",
        "ผลต่อ coverage = จำนวนลำในกลุ่มรุ่นยอดจดต่ำ หารด้วยทะเบียนสะสมทั้งหมด",
      ],
    },
  },
  {
    id: "price_evidence",
    label: "ราคาต่อลำและฐานชุดขายรายรุ่น",
    path: "data/reference/nbtc_model_prices.csv",
    query: {
      engine: "local-file",
      language: "csv",
      executed_at: generatedAt,
      description: "ราคาต่ำ ราคาที่ใช้ ราคาสูง ฐานชุดขาย แหล่งอ้างอิง วันที่ตรวจ และระดับความมั่นใจของแต่ละรุ่น",
      tables_used: ["data/reference/nbtc_model_prices.csv"],
      filters: ["ใช้ราคาไทยต่ำสุดที่มีหลักฐานและไม่ใช่ราคาล้างสต๊อกเป็นหลัก", "หากไม่มีราคาตัวเครื่องหรือชุดพื้นฐาน ใช้ชุดพร้อมบิน สัญญาภาครัฐ หรือการอนุมานพร้อมติดป้ายฐานราคา"],
      metric_definitions: [
        "price_thb = ราคาหลักที่ใช้คูณจำนวนลำ",
        "basis_kind = ประเภทของฐานราคา เช่น ตัวเปล่า ตัวเครื่อง ชุดพร้อมบิน ชุดคอมโบ สัญญาภาครัฐ หรือการอนุมาน",
      ],
    },
  },
  {
    id: "import_check",
    label: "ผลแปลงมูลค่าที่ประเมินเป็นฐานเทียบนำเข้า",
    path: "data/processed/nbtc_pricing/import_basis_check.csv",
    query: {
      engine: "sqlite",
      language: "sql",
      sql: importSql,
      executed_at: generatedAt,
      description: "หัก VAT และช่วงกำไรตัวแทนออกจากมูลค่าที่ประเมินเพื่อใช้เป็นตัวตรวจระดับกับข้อมูลศุลกากร",
      tables_used: ["data/processed/nbtc_pricing/import_basis_check.csv"],
      filters: ["ปีปฏิทิน 2568"],
      metric_definitions: ["ฐานเทียบนำเข้า = มูลค่าที่ประเมิน หาร VAT 7% และหารช่วงกำไรตัวแทน 10%-25%"],
    },
  },
  {
    id: "method_note",
    label: "หลักการ วิธีคำนวณ และข้อจำกัดของ NBTC pricing",
    path: "reports/2026-08-04_nbtc-unit-value/README.md",
    query: {
      engine: "local-document",
      language: "markdown",
      executed_at: generatedAt,
      description: "เอกสารอธิบายวิธีถอดรหัสรุ่น จับคู่ราคา ตรวจสอบข้ามแหล่ง และข้อจำกัดที่ต้องกำกับ",
      tables_used: ["reports/2026-08-04_nbtc-unit-value/README.md"],
    },
  },
];

const artifact = {
  surface: "report",
  manifest: {
    version: 1,
    surface: "report",
    title,
    description: "ประเมินจากจำนวนลำและราคาต่อลำที่มีหลักฐาน โดยฐานชุดขายต่างกันตามรุ่น",
    generatedAt,
    cards: [
      {
        id: "value_2025",
        description: "มูลค่าของลำที่จับคู่ราคาได้ พร้อมค่าปรับตาม coverage",
        dataset: "summary",
        sourceId: "annual_value",
        metrics: [
          { label: "มูลค่าที่วัดได้ ปี 2568 (ลบ.)", field: "measured_m", format: "number" },
          { label: "ค่าปรับ coverage (ลบ.)", field: "adjusted_m", format: "number" },
        ],
      },
      {
        id: "coverage_2025",
        description: "สัดส่วนทะเบียนปี 2568 ที่จับคู่ราคาได้",
        dataset: "summary",
        sourceId: "annual_value",
        metrics: [{ label: "Coverage ปี 2568", field: "coverage", format: "percent" }],
      },
      {
        id: "agriculture_share",
        description: "สัดส่วนสะสมของลำที่จับคู่ราคาได้ แยกตามกลุ่มการใช้งาน",
        dataset: "summary",
        sourceId: "model_value",
        metrics: [
          { label: "สัดส่วนมูลค่าโดรนเกษตร", field: "agriculture_value_share", format: "percent" },
          { label: "สัดส่วนจำนวนลำ", field: "agriculture_unit_share", format: "percent" },
        ],
      },
    ],
    charts: [
      {
        id: "annual_measured_value",
        title: "มูลค่าที่วัดได้และค่าปรับ coverage รายปี",
        subtitle: "ปีเต็ม 2561-2568; เส้นค่าปรับเป็นสมมติฐาน ไม่ใช่ค่าที่วัดได้",
        showDescription: true,
        intent: "trend",
        question: "มูลค่าที่วัดได้และค่าปรับ coverage เปลี่ยนไปอย่างไรในปีเต็ม",
        rationale: "ใช้กราฟเส้นสองชุดเพื่อให้ผู้อ่านเห็นผลของ coverage ที่ต่างกันในแต่ละปี โดยแยกค่าที่วัดได้ออกจากสมมติฐานอย่างชัดเจน",
        type: "line",
        dataset: "annual_trend",
        sourceId: "annual_value",
        encodings: {
          x: { field: "year_be", type: "ordinal", label: "ปี พ.ศ." },
          y: { field: "value_m", type: "quantitative", label: "มูลค่า", format: "number", unit: "ล้านบาท" },
          color: { field: "series", type: "nominal", label: "ฐานตัวเลข" },
          tooltip: [
            { field: "series", type: "nominal", label: "ฐานตัวเลข" },
            { field: "coverage", type: "quantitative", label: "Coverage", format: "percent" },
            { field: "registrations", type: "quantitative", label: "ลำจดทะเบียน", format: "number" },
            { field: "priced_units", type: "quantitative", label: "ลำที่ตั้งราคาได้", format: "number" },
          ],
        },
        xAxisTitle: "ปี พ.ศ.",
        yAxisTitle: "ล้านบาท",
        valueFormat: "number",
        unit: "ล้านบาท",
        layout: "full",
      },
      {
        id: "segment_composition",
        title: "สัดส่วนจำนวนลำและมูลค่า แยกตามการใช้งาน",
        subtitle: "เฉพาะ 168,728 ลำที่จับคู่ราคาได้สะสมปี 2560-2569",
        showDescription: true,
        intent: "composition",
        question: "โดรนทั่วไปและโดรนเกษตรมีสัดส่วนจำนวนลำและมูลค่าต่างกันเพียงใด",
        rationale: "ใช้กราฟแท่งซ้อน 100% เพื่อเปรียบเทียบองค์ประกอบบนฐานเดียวกันสองชุด",
        type: "stackedBar100",
        dataset: "segment_composition",
        sourceId: "model_value",
        encodings: {
          x: { field: "measure", type: "ordinal", label: "ฐานเปรียบเทียบ" },
          y: { field: "share", type: "quantitative", label: "สัดส่วน", format: "percent" },
          color: { field: "segment", type: "nominal", label: "กลุ่ม" },
          tooltip: [
            { field: "share", type: "quantitative", label: "สัดส่วน", format: "percent" },
            { field: "units", type: "quantitative", label: "จำนวนลำ", format: "number" },
            { field: "value_m", type: "quantitative", label: "มูลค่า", format: "number", unit: "ล้านบาท" },
          ],
        },
        xAxisTitle: "ฐานเปรียบเทียบ",
        yAxisTitle: "สัดส่วน",
        valueFormat: "percent",
        layout: "full",
      },
    ],
    tables: [],
    sources: manifestSources,
    blocks: [
      { id: "title", type: "markdown", body: `# ${title}` },
      {
        id: "executive_summary",
        type: "markdown",
        body: [
          "## บทสรุปผู้บริหาร (Executive Summary)",
          "",
          "- **ปี 2568 ประเมินมูลค่าจาก 32,804 ลำที่จับคู่ราคาได้ รวม 1,973 ล้านบาท** จากทะเบียนทั้งหมด 43,129 ลำ หรือ coverage 76.1% ส่วนค่าปรับ coverage เท่ากับ 2,594 ล้านบาท ซึ่งเป็นสมมติฐาน ไม่ใช่ช่วงความเชื่อมั่น",
          "- **บนฐานราคาที่รวบรวมได้ โดรนเกษตรเป็นตัวขับมูลค่าหลัก** แม้มีเพียง 13.8% ของลำที่ตั้งราคาได้ แต่คิดเป็น 62.1% ของมูลค่าสะสม และ 8 ใน 10 รุ่นที่มีมูลค่าสูงสุดเป็น DJI AGRAS",
          "- **รายงานนี้ใช้ประเมินทิศทางและโครงสร้างของมูลค่าโดรน** แต่ไม่ใช่ยอดขายจริง ราคาบางรุ่นเป็นตัวเครื่องหรือชุดพื้นฐาน บางรุ่นเป็นชุดพร้อมบิน และไม่ได้ประเมินรายได้จากซอฟต์แวร์ การติดตั้ง การอบรม หรือบริการบิน",
        ].join("\n"),
      },
      { id: "headline_metrics", type: "metric-strip", cardIds: ["value_2025", "coverage_2025", "agriculture_share"] },
      {
        id: "year_finding",
        type: "markdown",
        sourceId: "annual_value",
        body: [
          "## ปี 2568 วัดได้ 1,973 ล้านบาท; เมื่อปรับ coverage เป็น 2,594 ล้านบาท",
          "",
          "ส่วนต่างระหว่างสองฐานเท่ากับ 621 ล้านบาท กราฟจึงแสดงทั้ง **มูลค่าที่วัดได้** และ **ค่าปรับ coverage** ควบคู่กัน ปี 2568 มีทะเบียน 10,325 ลำที่ยังจับคู่ราคาไม่ได้ ทำให้ coverage ลดจาก 85.7% ในปีก่อนเหลือ 76.1%",
          "",
          "เมื่อเทียบปี 2567 กับ 2568 ค่าที่วัดได้เพิ่ม 5.0% แต่ค่าปรับ coverage เพิ่ม 18.2% ค่าจริงจึงยังไม่ควรถูกสรุปเป็นอัตราเติบโตจุดเดียว ค่าปรับใช้สมมติฐานว่าลำที่ยังไม่มีราคามีราคาเฉลี่ยใกล้เคียงกับลำที่มีราคา และไม่ใช่ช่วงความเชื่อมั่น",
        ].join("\n"),
      },
      { id: "annual_chart", type: "chart", chartId: "annual_measured_value", layout: "full" },
      {
        id: "agriculture_finding",
        type: "markdown",
        sourceId: "model_value",
        body: [
          "## บนฐานราคาที่รวบรวมได้ โดรนเกษตรมีจำนวนไม่มาก แต่สร้างมูลค่าส่วนใหญ่",
          "",
          "ในทะเบียนสะสมส่วนที่จับคู่ราคาได้ โดรนทั่วไปคิดเป็น 86.2% ของจำนวนลำ แต่สร้างมูลค่า 37.9% ขณะที่โดรนเกษตรมีเพียง 13.8% ของจำนวนลำ แต่สร้างมูลค่า 62.1%",
        ].join("\n"),
      },
      {
        id: "coverage_expansion",
        type: "markdown",
        sourceId: "unpriced_models",
        body: [
          "**การเพิ่ม coverage จะเกิดแบบค่อยเป็นค่อยไป** ใน 1,979 รุ่นที่ยังไม่มีหลักฐานราคา มี 87.1% ที่จดไม่เกิน 10 ลำต่อรุ่น แม้เติมราคาได้ครบทั้งกลุ่มนี้ coverage จะเพิ่มประมาณ 1.5 จุดเปอร์เซ็นต์ การสำรวจจึงยังดำเนินต่อทุกกลุ่มอย่างเป็นกลาง โดยเริ่มจากรุ่นที่มียอดจดสูงและมีหลักฐานราคาตรวจสอบได้ แล้วค่อยเติมรุ่นหางยาวที่มีผลต่อ coverage ทีละน้อย",
        ].join("\n"),
      },
      { id: "composition_chart", type: "chart", chartId: "segment_composition", layout: "full" },
      {
        id: "method_and_confidence",
        type: "markdown",
        body: [
          "## ตัวเลขมาจากทะเบียนรายลำ และราคาต่อลำที่มีหลักฐาน",
          "",
          "ทะเบียน กสทช. ถูกนำมารวมชื่อที่เขียนต่างกัน ถอดรหัสโรงงานกลับเป็นชื่อรุ่น แล้วจับคู่กับราคาที่มีแหล่งอ้างอิง ก่อนคำนวณจำนวนลำคูณราคาต่อลำ วิธีนี้ลดปัญหาสินค้าที่ผ่านประเทศไทยแล้วส่งออกต่อ ซึ่งปะปนอยู่ในยอดนำเข้ารวม",
          "",
          "**ฐานราคาต่างกันตามรุ่น** โดยใช้ราคาไทยต่ำสุดที่มีหลักฐานและไม่ใช่ราคาล้างสต๊อกเป็นหลัก บางรุ่นเป็นตัวเครื่องหรือชุดพื้นฐาน ขณะที่บางรุ่นเป็นชุดพร้อมบิน ชุดคอมโบ สัญญาภาครัฐ หรือการอนุมานตามหลักฐานที่หาได้ จึงไม่ได้ประเมินตลาดอุปกรณ์เสริมแยกต่างหาก แต่อุปกรณ์ที่รวมอยู่ในชุดขายอาจอยู่ในค่าประมาณแล้ว",
          "",
          "### ที่มาของข้อมูล",
          "",
          "การวิเคราะห์ใช้ข้อมูลทะเบียนโดรนของ กสทช. เป็นฐานจำนวนลำ ใช้ราคาจากผู้ผลิต ตัวแทนจำหน่าย และเอกสารจัดซื้อภาครัฐเพื่อกำหนดราคาต่อลำ และใช้สถิติการนำเข้า HS 8806 ของกรมศุลกากรเป็นตัวตรวจความสมเหตุสมผล ตัวเลขจึงเป็นค่าประมาณจากทะเบียนและหลักฐานราคา ไม่ใช่ยอดขายจากใบเสร็จ",
          "",
          "### ตัวตรวจความสมเหตุสมผล",
          "",
          "- จำนวน DJI AGRAS ที่จดทะเบียนอยู่ในระดับสอดคล้องกับจำนวนชิ้นในพิกัดศุลกากรที่เกี่ยวข้อง",
          "- เมื่อนำมูลค่าที่ประเมินได้ปี 2568 มาแปลงเป็นฐานเทียบนำเข้า โดยหัก VAT 7% และสมมติอัตรากำไรตัวแทน 10%-25% จะได้ประมาณ 1,475-1,676 ล้านบาท ขอบบนอยู่ใกล้มูลค่าขั้นต่ำจากข้อมูลศุลกากร 1,677 ล้านบาท ส่วนขอบล่างต่ำกว่าประมาณ 12% อย่างไรก็ตาม ราคาบางรุ่นรวมอุปกรณ์ที่ไม่ได้อยู่ในพิกัด HS 8806 การเทียบนี้จึงใช้ตรวจระดับคร่าว ๆ เท่านั้น ไม่ใช้ยืนยันหรือปรับค่าประมาณให้ตรงกัน",
          "",
          "ผลตรวจทั้งสองทางยังไม่พบความขัดแย้งระดับขนาด แต่ฐานข้อมูลและฐานชุดขายไม่ตรงกันทั้งหมด จึงใช้เป็นเพียงตัวตรวจคร่าว ๆ และไม่ได้เปลี่ยนประมาณการให้เป็นยอดขายจริง",
        ].join("\n"),
      },
      {
        id: "recommendations",
        type: "markdown",
        body: [
          "## สิ่งที่ดำเนินต่อ",
          "",
          "1. **แสดงตัวเลขสองฐานแยกกัน:** 1,973 ล้านบาทเป็นค่าที่วัดได้ และ 2,594 ล้านบาทเป็นค่าปรับ coverage",
          "2. **ทยอยเพิ่มหลักฐานราคาทุกรุ่น:** เริ่มจากรุ่นที่มียอดจดสูงในทุกกลุ่ม แล้วค่อยเติมรุ่นหางยาว เพื่อให้ coverage เพิ่มตามผลกระทบที่มีต่อฐานทะเบียน",
          "3. **ติดตาม coverage พร้อมมูลค่าทุกครั้งที่อัปเดต:** เพื่อแยกการเปลี่ยนของตลาดออกจากการเปลี่ยนของความครบถ้วนข้อมูล",
          "4. **คงรายงานนี้แยกจากตลาดรวม:** ตัวเลขจากรายงานอื่นที่รวมตลาดอุปกรณ์เสริม ซอฟต์แวร์ การติดตั้ง หรือบริการ ไม่สามารถเปรียบเทียบกับรายงานนี้โดยตรง",
        ].join("\n"),
      },
      {
        id: "caveats",
        type: "markdown",
        body: [
          "## ข้อจำกัดที่ต้องติดไปกับตัวเลข",
          "",
          "- ทะเบียน กสทช. เป็นตัวแทนของการนำโดรนมาใช้งาน ไม่ใช่ใบเสร็จยอดขาย และไม่ครอบคลุมลำที่ไม่จดทะเบียน",
          "- ไม่มีเลขเครื่องสำหรับตรวจการเปลี่ยนมือ จึงไม่สามารถยืนยันการนับซ้ำได้ทุกกรณี",
          "- ใช้ราคาเดียวต่อรุ่นกับทุกปี และราคาที่รวบรวมไม่ได้อยู่ในช่วงเวลาเดียวกันทั้งหมด",
          "- ฐานราคาต่างกันตามรุ่น บางรุ่นเป็นตัวเครื่องหรือชุดพื้นฐาน บางรุ่นเป็นชุดพร้อมบินหรือชุดคอมโบ จึงไม่ควรเปรียบเทียบราคารายรุ่นโดยไม่ตรวจฐานชุดขาย",
          "- 15.6% ของมูลค่าสะสมที่วัดได้อาศัยราคาจากสัญญาภาครัฐหรือกติกาอนุมาน ไม่ใช่ราคาป้ายร้านโดยตรง",
          "- ปี 2560 มีข้อมูล 3 เดือน และปี 2569 มีข้อมูล 6 เดือน จึงไม่ใช้สองปีนี้เปรียบเทียบกับปีเต็ม",
          "- ยังจับคู่ราคาไม่ได้ 17.8% ของทะเบียนสะสม และ 23.9% ของทะเบียนปี 2568",
        ].join("\n"),
      },
    ],
  },
  snapshot: {
    version: 1,
    generatedAt,
    status: "ready",
    datasets: {
      summary,
      annual_trend: fullYearTrendSeries,
      segment_composition: composition,
      unpriced_summary: unpricedSummary,
      validation,
    },
  },
  sources,
};

database.close();
writeFileSync(resolve(here, "artifact.json"), `${JSON.stringify(artifact, null, 2)}\n`, "utf8");
console.log(JSON.stringify({
  output: resolve(here, "artifact.json"),
  year2025: summary[0],
  rows: {
    annual_trend: fullYearTrendSeries.length,
    segment_composition: composition.length,
  },
}, null, 2));
