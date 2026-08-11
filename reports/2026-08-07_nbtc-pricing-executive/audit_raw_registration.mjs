import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");
const workbookPath = resolve(root, "data/raw/drone_data.xlsx");
const extractionDir = resolve(root, "tmp/raw-xlsx-audit");
const sharedStringsPath = resolve(extractionDir, "xl/sharedStrings.xml");
const worksheetPath = resolve(extractionDir, "xl/worksheets/sheet1.xml");
const outputPath = resolve(here, "raw-registration-audit.json");

mkdirSync(extractionDir, { recursive: true });
if (!existsSync(sharedStringsPath) || !existsSync(worksheetPath)) {
  execFileSync("tar.exe", ["-xf", workbookPath, "-C", extractionDir], { stdio: "inherit" });
}

function decodeXml(value) {
  return value
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&apos;", "'")
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) => String.fromCodePoint(Number.parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, decimal) => String.fromCodePoint(Number(decimal)))
    .replaceAll("&amp;", "&");
}

const sharedXml = readFileSync(sharedStringsPath, "utf8");
const sharedStrings = [];
for (const item of sharedXml.matchAll(/<si>([\s\S]*?)<\/si>/g)) {
  const parts = [...item[1].matchAll(/<t(?:\s[^>]*)?>([\s\S]*?)<\/t>/g)].map((match) => decodeXml(match[1]));
  sharedStrings.push(parts.join(""));
}

const sheetXml = readFileSync(worksheetPath, "utf8");
const dimension = sheetXml.match(/<dimension ref="([^"]+)"/)?.[1] ?? null;
const missingByField = {};
const yearCounts = new Map();
const signatureCounts = new Map();
let headers = [];
let dataRows = 0;
let invalidDateRows = 0;
let identicalRowsBeyondFirst = 0;

for (const rowMatch of sheetXml.matchAll(/<row\b([^>]*)>([\s\S]*?)<\/row>/g)) {
  const rowNumber = Number(rowMatch[1].match(/\br="(\d+)"/)?.[1] ?? 0);
  const values = Array(6).fill("");
  for (const cellMatch of rowMatch[2].matchAll(/<c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
    const attributes = cellMatch[1];
    const body = cellMatch[2] ?? "";
    const reference = attributes.match(/\br="([A-Z]+)\d+"/)?.[1] ?? "";
    if (reference.length !== 1) continue;
    const columnIndex = reference.charCodeAt(0) - 65;
    if (columnIndex < 0 || columnIndex >= 6) continue;
    const raw = body.match(/<v>([\s\S]*?)<\/v>/)?.[1] ?? "";
    const type = attributes.match(/\bt="([^"]+)"/)?.[1] ?? "";
    values[columnIndex] = type === "s" ? (sharedStrings[Number(raw)] ?? "") : decodeXml(raw);
  }

  if (rowNumber === 1) {
    headers = values;
    for (const header of headers) missingByField[header] = 0;
    continue;
  }

  dataRows += 1;
  values.forEach((value, index) => {
    if (!String(value).trim()) missingByField[headers[index]] += 1;
  });

  const yearMatch = values[0].match(/(\d{4})$/);
  if (!yearMatch) {
    invalidDateRows += 1;
  } else {
    const calendarYear = Number(yearMatch[1]) - 543;
    yearCounts.set(calendarYear, (yearCounts.get(calendarYear) ?? 0) + 1);
  }

  const signature = values.join("\u001f");
  const prior = signatureCounts.get(signature) ?? 0;
  if (prior > 0) identicalRowsBeyondFirst += 1;
  signatureCounts.set(signature, prior + 1);
}

const identicalRowSignatureGroups = [...signatureCounts.values()].filter((count) => count > 1).length;
const result = {
  generatedAt: new Date().toISOString(),
  workbook: "data/raw/drone_data.xlsx",
  worksheetDimension: dimension,
  headers,
  dataRows,
  missingByField,
  invalidDateRows,
  yearCounts: Object.fromEntries([...yearCounts].sort(([a], [b]) => a - b)),
  identicalRowSignatureGroups,
  identicalRowsBeyondFirst,
  duplicateInterpretation: "Rows match on the six available fields only. With no serial or registration id, they cannot be confirmed as duplicate aircraft.",
};

writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
console.log(JSON.stringify(result, null, 2));
