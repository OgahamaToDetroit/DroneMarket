import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
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
    } else if (char === '"') {
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
  const [headers, ...records] = rows.filter((values) => values.some((value) => value !== ""));
  return records.map((record) => Object.fromEntries(headers.map((header, index) => [header, record[index] ?? ""])));
}

function loadCsv(relativePath) {
  return parseCsv(readFileSync(resolve(root, relativePath), "utf8"));
}

function number(value) {
  if (value == null || String(value).trim() === "") return Number.NaN;
  return Number(value);
}

function sum(rows, field) {
  return rows.reduce((total, row) => total + (Number.isFinite(number(row[field])) ? number(row[field]) : 0), 0);
}

function key(...values) {
  return values.map((value) => String(value ?? "")).join("\u0000");
}

function countDuplicateKeys(rows, fields) {
  const counts = new Map();
  for (const row of rows) {
    const rowKey = key(...fields.map((field) => row[field]));
    counts.set(rowKey, (counts.get(rowKey) ?? 0) + 1);
  }
  return [...counts.values()].reduce((total, count) => total + Math.max(0, count - 1), 0);
}

function nearlyEqual(actual, expected, tolerance = 1e-6) {
  return Number.isFinite(actual) && Number.isFinite(expected) && Math.abs(actual - expected) <= tolerance;
}

const checks = [];
function check(id, ok, evidence, severity = "high") {
  checks.push({ id, ok: Boolean(ok), severity, evidence });
}

const files = {
  long: "data/processed/nbtc_pricing/registrations_by_model_year.csv",
  catalog: "data/processed/nbtc_pricing/model_catalog.csv",
  codes: "data/reference/nbtc_code_map.csv",
  prices: "data/reference/nbtc_model_prices.csv",
  tiers: "data/reference/nbtc_model_tiers.csv",
  years: "data/processed/nbtc_pricing/market_value_by_year.csv",
  models: "data/processed/nbtc_pricing/market_value_by_model.csv",
  unpriced: "data/processed/nbtc_pricing/unpriced_models.csv",
  brackets: "data/processed/nbtc_pricing/unpriced_brackets.csv",
  importCheck: "data/processed/nbtc_pricing/import_basis_check.csv",
  yearCoverage: "data/processed/nbtc_pricing/year_coverage.csv",
  customsByCode: "data/processed/customs_hs8806_by_code.csv",
  customsBalance: "data/processed/customs_hs8806_balance.csv",
};

const longRows = loadCsv(files.long);
const catalogRows = loadCsv(files.catalog);
const codeRows = loadCsv(files.codes);
const rawPriceRows = loadCsv(files.prices);
const tierRows = loadCsv(files.tiers);
const reportedYearRows = loadCsv(files.years);
const reportedModelRows = loadCsv(files.models);
const reportedUnpricedRows = loadCsv(files.unpriced);
const bracketRows = loadCsv(files.brackets);
const importRows = loadCsv(files.importCheck);
const yearCoverageRows = loadCsv(files.yearCoverage);
const customsRows = loadCsv(files.customsByCode);
const customsBalanceRows = loadCsv(files.customsBalance);
const artifact = JSON.parse(readFileSync(resolve(here, "artifact.json"), "utf8"));
const html = readFileSync(resolve(here, "report.html"), "utf8");

const codeDuplicateCount = countDuplicateKeys(codeRows, ["brand", "catalog_model"]);
const priceDuplicateCount = countDuplicateKeys(rawPriceRows, ["brand", "model"]);
const tierDuplicateCount = countDuplicateKeys(tierRows, ["brand", "model"]);
check("code-map-keys-unique", codeDuplicateCount === 0, { duplicateRowsBeyondFirst: codeDuplicateCount });
check("price-keys-unique", priceDuplicateCount === 0, { duplicateRowsBeyondFirst: priceDuplicateCount });
check("tier-keys-unique", tierDuplicateCount === 0, { duplicateRowsBeyondFirst: tierDuplicateCount });

const longTotal = sum(longRows, "units");
const catalogTotal = sum(catalogRows, "units");
const invalidLongUnits = longRows.filter((row) => !Number.isInteger(number(row.units)) || number(row.units) <= 0).length;
const invalidYears = longRows.filter((row) => !Number.isInteger(number(row.year)) || number(row.year) < 2017 || number(row.year) > 2026).length;
check("registration-total-is-stable", longTotal === 205_287 && catalogTotal === longTotal, { longTotal, catalogTotal });
check("registration-units-valid", invalidLongUnits === 0, { invalidRows: invalidLongUnits });
check("registration-years-valid", invalidYears === 0, { invalidRows: invalidYears });

const priceRangeFailures = rawPriceRows.filter((row) => {
  const lo = number(row.price_lo_thb);
  const mid = number(row.price_thb);
  const hi = number(row.price_hi_thb);
  return ![lo, mid, hi].every(Number.isFinite) || lo > mid || mid > hi || lo <= 0;
});
const missingPriceSources = rawPriceRows.filter((row) => !row.source.trim() || !row.source_url.trim() || !row.asof.trim()).length;
check("price-ranges-valid", priceRangeFailures.length === 0, { invalidRows: priceRangeFailures.length });
check("price-provenance-complete", missingPriceSources === 0, { missingRows: missingPriceSources });

const codeMap = new Map(codeRows.map((row) => [key(row.brand, row.catalog_model), {
  brand: row.resolved_brand.trim() || row.brand,
  model: row.resolved_model,
}]));
const remap = (brand, model) => codeMap.get(key(brand, model)) ?? { brand, model };

const tierMap = new Map(tierRows.map((row) => [key(row.brand, row.model), { tier: row.tier, gen: number(row.gen) }]));
const prices = rawPriceRows.map((row) => {
  const tier = tierMap.get(key(row.brand, row.model));
  return {
    ...row,
    price: number(row.price_thb),
    priceLo: number(row.price_lo_thb),
    priceHi: number(row.price_hi_thb),
    tier: tier?.tier ?? "",
    gen: tier?.gen ?? Number.NaN,
  };
});
const basePrices = prices.map((row) => row.price);
const capAdjustments = [];
for (let index = 0; index < prices.length; index += 1) {
  const row = prices[index];
  if (!row.tier || !Number.isFinite(row.gen)) continue;
  const newer = prices
    .map((candidate, candidateIndex) => ({ candidate, candidateIndex }))
    .filter(({ candidate }) => candidate.tier === row.tier && Number.isFinite(candidate.gen) && candidate.gen > row.gen);
  if (!newer.length) continue;
  const ceiling = Math.min(...newer.map(({ candidateIndex }) => basePrices[candidateIndex]));
  if (basePrices[index] > ceiling) {
    row.price = ceiling;
    row.priceLo = Math.min(row.priceLo, ceiling);
    row.basis_kind = "อนุมาน";
    capAdjustments.push({ brand: row.brand, model: row.model, from: basePrices[index], to: ceiling });
  }
}
const priceMap = new Map(prices.map((row) => [key(row.brand, row.model), row]));

const classAgg = new Map();
for (const row of catalogRows) {
  const mapped = remap(row.brand, row.model);
  const mappedKey = key(mapped.brand, mapped.model);
  const current = classAgg.get(mappedKey) ?? { units: 0, agriUnits: 0 };
  current.units += number(row.units);
  current.agriUnits += number(row.agri_units);
  classAgg.set(mappedKey, current);
}
const classMap = new Map([...classAgg].map(([mappedKey, value]) => [mappedKey, value.agriUnits / value.units >= 0.6 ? "เกษตร" : "ทั่วไป"]));

const recomputedYears = new Map();
const recomputedModels = new Map();
const recomputedUnpriced = new Map();
const basisTotals = new Map();
const confidenceTotals = new Map();
for (const row of longRows) {
  const mapped = remap(row.brand, row.model);
  const mappedKey = key(mapped.brand, mapped.model);
  const units = number(row.units);
  const year = String(row.year);
  const cls = classMap.get(mappedKey) ?? "ทั่วไป";
  const yearAgg = recomputedYears.get(year) ?? { year, units: 0, val: 0, val_lo: 0, val_hi: 0, units_all: 0 };
  yearAgg.units_all += units;
  const price = priceMap.get(mappedKey);
  if (price) {
    yearAgg.units += units;
    yearAgg.val += units * price.price;
    yearAgg.val_lo += units * price.priceLo;
    yearAgg.val_hi += units * price.priceHi;
    const modelAgg = recomputedModels.get(key(mapped.brand, mapped.model, cls)) ?? {
      brand: mapped.brand,
      model_final: mapped.model,
      class: cls,
      units: 0,
      val: 0,
      val_lo: 0,
      val_hi: 0,
    };
    modelAgg.units += units;
    modelAgg.val += units * price.price;
    modelAgg.val_lo += units * price.priceLo;
    modelAgg.val_hi += units * price.priceHi;
    recomputedModels.set(key(mapped.brand, mapped.model, cls), modelAgg);
    const basis = basisTotals.get(price.basis_kind) ?? { units: 0, value: 0 };
    basis.units += units;
    basis.value += units * price.price;
    basisTotals.set(price.basis_kind, basis);
    const confidence = confidenceTotals.get(price.confidence) ?? { units: 0, value: 0 };
    confidence.units += units;
    confidence.value += units * price.price;
    confidenceTotals.set(price.confidence, confidence);
  } else {
    const group = cls === "ทั่วไป" ? "ทั่วไป" : mapped.brand === "DJI" ? "เกษตร-DJI" : "เกษตร-ไม่ใช่ DJI";
    const unpricedKey = key(mapped.brand, mapped.model, cls, group);
    const current = recomputedUnpriced.get(unpricedKey) ?? { brand: mapped.brand, model_final: mapped.model, class: cls, group, units: 0 };
    current.units += units;
    recomputedUnpriced.set(unpricedKey, current);
  }
  recomputedYears.set(year, yearAgg);
}
for (const row of recomputedYears.values()) {
  row.coverage = row.units / row.units_all;
  row.val_scaled = row.val / row.coverage;
}

const yearDiscrepancies = [];
for (const reported of reportedYearRows) {
  const actual = recomputedYears.get(String(reported.year));
  for (const field of ["units", "val", "val_lo", "val_hi", "units_all", "coverage", "val_scaled"]) {
    const tolerance = field === "coverage" ? 1e-12 : 1;
    if (!actual || !nearlyEqual(actual[field], number(reported[field]), tolerance)) {
      yearDiscrepancies.push({ year: reported.year, field, recomputed: actual?.[field], reported: number(reported[field]) });
    }
  }
}
check("year-output-reconciles", yearDiscrepancies.length === 0, { discrepancies: yearDiscrepancies.slice(0, 10) });

const modelDiscrepancies = [];
for (const reported of reportedModelRows) {
  const actual = recomputedModels.get(key(reported.brand, reported.model_final, reported.class));
  for (const field of ["units", "val", "val_lo", "val_hi"]) {
    if (!actual || !nearlyEqual(actual[field], number(reported[field]), 1)) {
      modelDiscrepancies.push({ brand: reported.brand, model: reported.model_final, field, recomputed: actual?.[field], reported: number(reported[field]) });
    }
  }
}
check(
  "model-output-reconciles",
  modelDiscrepancies.length === 0 && recomputedModels.size === reportedModelRows.length,
  { discrepancies: modelDiscrepancies.slice(0, 10), recomputedRows: recomputedModels.size, reportedRows: reportedModelRows.length },
);

const unpricedDiscrepancies = [];
for (const reported of reportedUnpricedRows) {
  const actual = recomputedUnpriced.get(key(reported.brand, reported.model_final, reported.class, reported.group));
  if (!actual || actual.units !== number(reported.units)) {
    unpricedDiscrepancies.push({ brand: reported.brand, model: reported.model_final, recomputed: actual?.units, reported: number(reported.units) });
  }
}
const recomputedPricedUnits = [...recomputedModels.values()].reduce((total, row) => total + row.units, 0);
const recomputedUnpricedUnits = [...recomputedUnpriced.values()].reduce((total, row) => total + row.units, 0);
check(
  "unpriced-output-reconciles",
  unpricedDiscrepancies.length === 0 && recomputedUnpriced.size === reportedUnpricedRows.length && recomputedPricedUnits + recomputedUnpricedUnits === longTotal,
  {
    discrepancies: unpricedDiscrepancies.slice(0, 10),
    recomputedRows: recomputedUnpriced.size,
    reportedRows: reportedUnpricedRows.length,
    pricedUnits: recomputedPricedUnits,
    unpricedUnits: recomputedUnpricedUnits,
  },
);

const recomputedUnpricedList = [...recomputedUnpriced.values()];
const lowVolumeUnpriced = recomputedUnpricedList.filter((row) => row.units <= 10);
const lowVolumeUnpricedUnits = lowVolumeUnpriced.reduce((total, row) => total + row.units, 0);
const lowVolumeModelShare = lowVolumeUnpriced.length / recomputedUnpricedList.length;
const lowVolumeCoveragePointImpact = lowVolumeUnpricedUnits / longTotal;
check(
  "unpriced-long-tail-claim-reconciles",
  recomputedUnpricedList.length === 1_979
    && lowVolumeUnpriced.length === 1_724
    && lowVolumeUnpricedUnits === 2_984
    && nearlyEqual(lowVolumeModelShare, 0.8711470439615968, 1e-12)
    && nearlyEqual(lowVolumeCoveragePointImpact, 0.014535747514455372, 1e-12),
  {
    unpricedModels: recomputedUnpricedList.length,
    lowVolumeModels: lowVolumeUnpriced.length,
    lowVolumeModelShare,
    lowVolumeUnpricedUnits,
    lowVolumeCoveragePointImpact,
  },
);

const bracketUnits = sum(bracketRows, "units");
check("unpriced-brackets-cover-all-unpriced-units", bracketUnits === recomputedUnpricedUnits, { bracketUnits, recomputedUnpricedUnits });

const year2025 = recomputedYears.get("2025");
const reportedImport2025 = importRows.find((row) => row.year === "2025");
const expectedImportLow = year2025.val / 1.07 / 1.25;
const expectedImportHigh = year2025.val / 1.07 / 1.10;
const customsTotal2025 = customsRows
  .filter((row) => row["ปี"] === "2568" && row["ทิศทาง"] === "import")
  .reduce((total, row) => total + number(row["มูลค่าบาท"]), 0);
const customsFloor2025 = customsBalanceRows
  .filter((row) => row["ปี"] === "2568" && row["ผ่าน_GATE"].toLowerCase() === "true")
  .reduce((total, row) => total + number(row["อุปสงค์ในประเทศ_บาท"]), 0);
check(
  "import-basis-reconciles",
  reportedImport2025
    && nearlyEqual(number(reportedImport2025.imp_lo), expectedImportLow, 1)
    && nearlyEqual(number(reportedImport2025.imp_hi), expectedImportHigh, 1)
    && nearlyEqual(number(reportedImport2025.customs_import), customsTotal2025, 1),
  { expectedImportLow, expectedImportHigh, customsTotal2025, customsFloor2025 },
);

const recomputedModelList = [...recomputedModels.values()];
const totalPricedValue = recomputedModelList.reduce((total, row) => total + row.val, 0);
const agriculture = recomputedModelList.filter((row) => row.class === "เกษตร");
const agricultureUnits = agriculture.reduce((total, row) => total + row.units, 0);
const agricultureValue = agriculture.reduce((total, row) => total + row.val, 0);
const topTen = [...recomputedModelList].sort((a, b) => b.val - a.val).slice(0, 10);
const topTenAgras = topTen.filter((row) => row.brand === "DJI" && /^AGRAS\b/.test(row.model_final)).length;
check("agriculture-composition-reconciles", agricultureUnits === 23_318 && nearlyEqual(agricultureValue, 5_423_565_600, 1), { agricultureUnits, agricultureValue });
check("top-ten-agras-claim", topTenAgras === 8, { topTenAgras, topTen: topTen.map((row) => `${row.brand} ${row.model_final}`) });

const summaryRow = artifact.snapshot.datasets.summary[0];
const artifactTrend = artifact.snapshot.datasets.annual_trend;
const artifactComposition = artifact.snapshot.datasets.segment_composition;
const artifactUnpricedSummary = artifact.snapshot.datasets.unpriced_summary?.[0];
const expectedSummary = {
  measured_m: Math.round(year2025.val / 1e6),
  adjusted_m: Math.round(year2025.val_scaled / 1e6),
  coverage: year2025.coverage,
  priced_units: year2025.units,
  registrations: year2025.units_all,
  agriculture_value_share: agricultureValue / totalPricedValue,
  agriculture_unit_share: agricultureUnits / recomputedPricedUnits,
  top_ten_agriculture_models: topTenAgras,
};
const artifactSummaryDiscrepancies = Object.entries(expectedSummary).filter(([field, value]) => !nearlyEqual(number(summaryRow[field]), value, field.includes("share") || field === "coverage" ? 1e-12 : 1e-9));
check("artifact-summary-reconciles", artifactSummaryDiscrepancies.length === 0, { discrepancies: artifactSummaryDiscrepancies });
const artifactTrendSeriesCounts = Object.fromEntries(
  [...new Set(artifactTrend.map((row) => row.series))].map((series) => [series, artifactTrend.filter((row) => row.series === series).length]),
);
check(
  "artifact-trend-series-complete",
  artifactTrend.length === 16
    && artifactTrendSeriesCounts["มูลค่าที่วัดได้"] === 8
    && artifactTrendSeriesCounts["ค่าปรับ coverage"] === 8,
  { rows: artifactTrend.length, seriesCounts: artifactTrendSeriesCounts },
);
check("artifact-composition-sums-to-one", ["จำนวนลำ", "มูลค่า"].every((measure) => nearlyEqual(artifactComposition.filter((row) => row.measure === measure).reduce((total, row) => total + number(row.share), 0), 1, 1e-12)), { rows: artifactComposition.length });
check(
  "artifact-unpriced-summary-reconciles",
  artifactUnpricedSummary
    && number(artifactUnpricedSummary.unpriced_models) === recomputedUnpricedList.length
    && number(artifactUnpricedSummary.low_volume_models) === lowVolumeUnpriced.length
    && nearlyEqual(number(artifactUnpricedSummary.low_volume_model_share), lowVolumeModelShare, 1e-12)
    && number(artifactUnpricedSummary.low_volume_units) === lowVolumeUnpricedUnits
    && number(artifactUnpricedSummary.registration_units) === longTotal
    && nearlyEqual(number(artifactUnpricedSummary.coverage_point_impact), lowVolumeCoveragePointImpact, 1e-12),
  { artifactUnpricedSummary },
);
check("html-has-two-static-charts", (html.match(/data-static-chart-block-id=/g) ?? []).length === 2, { count: (html.match(/data-static-chart-block-id=/g) ?? []).length }, "medium");
check("html-has-no-mojibake", !/(?:Ã|à¸|â€|�)/.test(html), {}, "medium");
const visibleNarrative = artifact.manifest.blocks
  .filter((block) => block.type === "markdown")
  .map((block) => block.body)
  .join("\n");
check(
  "reader-facing-copy-has-no-process-labels",
  !/(?:ระดับความพร้อม|ฉบับผู้บริหารและพนักงานทั่วไป|ตรวจทาน 10 สิงหาคม 2569|สิ่งที่ควรทำต่อ)/.test(`${artifact.manifest.description}\n${visibleNarrative}`),
  {},
  "medium",
);
const priceBasisKinds = new Set(rawPriceRows.map((row) => row.basis_kind));
const mixedPriceBasisPresent = [
  "ป้ายร้าน-ตัวเปล่า",
  "ป้ายร้าน-ตัวเครื่อง",
  "ป้ายร้าน-ชุดพร้อมบิน",
  "ป้ายร้าน-ชุดคอมโบ",
  "สัญญาภาครัฐ",
  "อนุมาน",
].every((basis) => priceBasisKinds.has(basis));
check(
  "reader-facing-price-basis-is-explicit",
  mixedPriceBasisPresent
    && artifact.manifest.title === "มูลค่าโดรนที่จดทะเบียนในไทย ปี 2568"
    && artifact.manifest.description.includes("ฐานชุดขายต่างกันตามรุ่น")
    && visibleNarrative.includes("ฐานราคาต่างกันตามรุ่น")
    && visibleNarrative.includes("อุปกรณ์ที่รวมอยู่ในชุดขายอาจอยู่ในค่าประมาณแล้ว")
    && !artifact.manifest.description.includes("ไม่รวมซอฟต์แวร์ อุปกรณ์ประกอบ และบริการ"),
  { priceBasisKinds: [...priceBasisKinds].sort((a, b) => a.localeCompare(b, "th")) },
  "medium",
);
check(
  "print-hides-technical-source-inventory",
  /\.portable-sources\s*\{\s*display:\s*none\s*!important;\s*\}/.test(html),
  {},
  "medium",
);

const raw2024 = recomputedYears.get("2024");
const rawGrowth2025 = year2025.val / raw2024.val - 1;
const adjustedGrowth2025 = year2025.val_scaled / raw2024.val_scaled - 1;
const softBasis = new Set(["สัญญาภาครัฐ", "อนุมาน"]);
const softTotals = [...basisTotals]
  .filter(([basis]) => softBasis.has(basis))
  .reduce((result, [, value]) => ({ units: result.units + value.units, value: result.value + value.value }), { units: 0, value: 0 });
const classificationBoundaryModels = recomputedModelList
  .map((row) => {
    const classEvidence = classAgg.get(key(row.brand, row.model_final));
    return {
      brand: row.brand,
      model: row.model_final,
      units: row.units,
      value: row.val,
      agricultureShare: classEvidence ? classEvidence.agriUnits / classEvidence.units : Number.NaN,
    };
  })
  .filter((row) => row.agricultureShare >= 0.4 && row.agricultureShare <= 0.8)
  .sort((a, b) => b.value - a.value);
const priceConfidenceCounts = Object.fromEntries(
  [...new Set(rawPriceRows.map((row) => row.confidence))]
    .sort()
    .map((confidence) => [confidence, rawPriceRows.filter((row) => row.confidence === confidence).length]),
);
const lowConfidenceModels = recomputedModelList
  .filter((row) => priceMap.get(key(row.brand, row.model_final))?.confidence === "ต่ำ")
  .sort((a, b) => b.val - a.val)
  .map((row) => ({ brand: row.brand, model: row.model_final, units: row.units, value: row.val }));

const failed = checks.filter((item) => !item.ok);
const result = {
  generatedAt: new Date().toISOString(),
  sourceSnapshot: {
    registrationRows: longTotal,
    processedYears: reportedYearRows.map((row) => number(row.year)),
    fullYearsUsedInTrend: [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
  },
  headline: {
    year2025: {
      registrations: year2025.units_all,
      pricedUnits: year2025.units,
      unpricedUnits: year2025.units_all - year2025.units,
      coverage: year2025.coverage,
      measuredValue: year2025.val,
      coverageAdjustedValue: year2025.val_scaled,
      coverageAdjustmentGap: year2025.val_scaled - year2025.val,
      rawGrowthVs2024: rawGrowth2025,
      adjustedGrowthVs2024: adjustedGrowth2025,
    },
    cumulative: {
      pricedUnits: recomputedPricedUnits,
      unpricedUnits: recomputedUnpricedUnits,
      measuredValue: totalPricedValue,
      agricultureUnits,
      agricultureValue,
      agricultureUnitShare: agricultureUnits / recomputedPricedUnits,
      agricultureValueShare: agricultureValue / totalPricedValue,
      softBasisUnits: softTotals.units,
      softBasisUnitShare: softTotals.units / recomputedPricedUnits,
      softBasisValue: softTotals.value,
      softBasisValueShare: softTotals.value / totalPricedValue,
      classificationBoundaryPricedModels: classificationBoundaryModels,
      unpricedModels: recomputedUnpricedList.length,
      lowVolumeUnpricedModels: lowVolumeUnpriced.length,
      lowVolumeModelShare,
      lowVolumeUnpricedUnits,
      lowVolumeCoveragePointImpact,
    },
    customsCrossCheck: {
      importBasisLow: expectedImportLow,
      importBasisHigh: expectedImportHigh,
      customsFloor: customsFloor2025,
      customsTotal: customsTotal2025,
      lowVsFloorGap: expectedImportLow / customsFloor2025 - 1,
      highVsFloorGap: expectedImportHigh / customsFloor2025 - 1,
    },
    capAdjustments,
    priceTable: {
      rows: rawPriceRows.length,
      earliestAsOf: [...rawPriceRows.map((row) => row.asof)].sort()[0],
      latestAsOf: [...rawPriceRows.map((row) => row.asof)].sort().at(-1),
      confidenceCounts: priceConfidenceCounts,
      confidenceTotals: Object.fromEntries([...confidenceTotals].sort(([a], [b]) => a.localeCompare(b, "th"))),
      lowConfidenceModels,
      basisTotals: Object.fromEntries([...basisTotals].sort(([a], [b]) => a.localeCompare(b, "th"))),
    },
  },
  checks,
  result: failed.length ? "failed" : "passed",
  failedChecks: failed.map((item) => item.id),
};

writeFileSync(resolve(here, "validation-results.json"), `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ result: result.result, checks: checks.length, failed: result.failedChecks, headline: result.headline }, null, 2));
if (failed.length) process.exitCode = 1;
