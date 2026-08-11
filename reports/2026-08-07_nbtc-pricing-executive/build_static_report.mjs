import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const pluginRoot = "C:/Users/forge/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.8-13ceeea1f599";
const builderModule = await import(pathToFileURL(resolve(pluginRoot, "skills/build-report/scripts/build_portable_artifact.mjs")).href);
const verifierModule = await import(pathToFileURL(resolve(pluginRoot, "skills/build-report/scripts/verify_portable_artifact.mjs")).href);

const artifactPath = resolve(here, "artifact.json");
const reportPath = resolve(here, "report.html");
const artifact = JSON.parse(readFileSync(artifactPath, "utf8"));

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatNumber(value, digits = 0) {
  return Number(value).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function annualTrendSvg(rows, theme) {
  const width = 800;
  const height = 360;
  const margin = { top: 30, right: 34, bottom: 58, left: 78 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const measuredRows = rows.filter((row) => row.series === "มูลค่าที่วัดได้");
  const adjustedRows = rows.filter((row) => row.series === "ค่าปรับ coverage");
  if (!measuredRows.length || measuredRows.length !== adjustedRows.length) {
    throw new Error("Annual trend requires matching measured and coverage-adjusted series.");
  }
  const maxY = 2_800;
  const yTicks = [0, 500, 1_000, 1_500, 2_000, 2_500];
  const colors = theme === "dark"
    ? { ink: "rgb(232,234,237)", muted: "rgb(189,193,198)", grid: "rgb(77,81,86)", measured: "rgb(138,180,248)", adjusted: "rgb(253,214,99)" }
    : { ink: "rgb(32,33,36)", muted: "rgb(95,99,104)", grid: "rgb(226,229,233)", measured: "rgb(30,104,204)", adjusted: "rgb(210,138,0)" };
  const x = (index) => margin.left + (index * plotWidth) / (measuredRows.length - 1);
  const y = (value) => margin.top + plotHeight - (Number(value) / maxY) * plotHeight;
  const measuredPoints = measuredRows.map((row, index) => `${x(index).toFixed(1)},${y(row.value_m).toFixed(1)}`).join(" ");
  const adjustedPoints = adjustedRows.map((row, index) => `${x(index).toFixed(1)},${y(row.value_m).toFixed(1)}`).join(" ");
  const parts = [
    `<svg aria-hidden="true" class="portable-static-chart-svg" focusable="false" height="${height}" preserveAspectRatio="xMidYMid meet" viewBox="0 0 ${width} ${height}" width="${width}" xmlns="http://www.w3.org/2000/svg">`,
  ];

  for (const tick of yTicks) {
    const yPos = y(tick);
    parts.push(`<line stroke="${colors.grid}" stroke-width="1" x1="${margin.left}" x2="${width - margin.right}" y1="${yPos}" y2="${yPos}"></line>`);
    parts.push(`<text fill="${colors.muted}" font-family="Tahoma, Arial, sans-serif" font-size="12" text-anchor="end" x="${margin.left - 12}" y="${yPos + 4}">${formatNumber(tick)}</text>`);
  }
  parts.push(`<line stroke="${colors.ink}" stroke-width="1" x1="${margin.left}" x2="${margin.left}" y1="${margin.top}" y2="${margin.top + plotHeight}"></line>`);
  parts.push(`<line stroke="${colors.ink}" stroke-width="1" x1="${margin.left}" x2="${width - margin.right}" y1="${margin.top + plotHeight}" y2="${margin.top + plotHeight}"></line>`);
  parts.push(`<polyline fill="none" points="${adjustedPoints}" stroke="${colors.adjusted}" stroke-dasharray="9 7" stroke-linecap="round" stroke-linejoin="round" stroke-width="3"></polyline>`);
  parts.push(`<polyline fill="none" points="${measuredPoints}" stroke="${colors.measured}" stroke-linecap="round" stroke-linejoin="round" stroke-width="4"></polyline>`);

  adjustedRows.forEach((row, index) => {
    const xPos = x(index);
    const yPos = y(row.value_m);
    parts.push(`<circle cx="${xPos}" cy="${yPos}" fill="white" r="4" stroke="${colors.adjusted}" stroke-width="2"></circle>`);
    if (index === adjustedRows.length - 1) {
      parts.push(`<text fill="${colors.adjusted}" font-family="Tahoma, Arial, sans-serif" font-size="11" font-weight="700" text-anchor="middle" x="${xPos}" y="${Math.max(14, yPos - 12)}">${formatNumber(row.value_m, 0)}</text>`);
    }
  });

  measuredRows.forEach((row, index) => {
    const xPos = x(index);
    const yPos = y(row.value_m);
    parts.push(`<circle cx="${xPos}" cy="${yPos}" fill="${colors.measured}" r="5" stroke="${colors.ink}" stroke-width="1"></circle>`);
    parts.push(`<text fill="${colors.ink}" font-family="Tahoma, Arial, sans-serif" font-size="11" font-weight="600" text-anchor="middle" x="${xPos}" y="${Math.max(14, yPos - 12)}">${formatNumber(row.value_m, 0)}</text>`);
    parts.push(`<text fill="${colors.muted}" font-family="Tahoma, Arial, sans-serif" font-size="12" text-anchor="middle" x="${xPos}" y="${margin.top + plotHeight + 24}">${escapeXml(row.year_be)}</text>`);
  });
  parts.push(`<text fill="${colors.muted}" font-family="Tahoma, Arial, sans-serif" font-size="12" text-anchor="middle" x="${width / 2}" y="${height - 8}">ปี พ.ศ.</text>`);
  parts.push(`<text fill="${colors.muted}" font-family="Tahoma, Arial, sans-serif" font-size="12" text-anchor="middle" transform="rotate(-90 18 ${height / 2})" x="18" y="${height / 2}">ล้านบาท</text>`);
  parts.push("</svg>");
  return parts.join("");
}

function compositionSvg(rows, theme) {
  const width = 800;
  const height = 340;
  const margin = { top: 24, right: 80, bottom: 58, left: 90 };
  const plotHeight = height - margin.top - margin.bottom;
  const colors = theme === "dark"
    ? { ink: "rgb(232,234,237)", muted: "rgb(189,193,198)", grid: "rgb(77,81,86)", general: "rgb(138,180,248)", agriculture: "rgb(253,214,99)" }
    : { ink: "rgb(32,33,36)", muted: "rgb(95,99,104)", grid: "rgb(226,229,233)", general: "rgb(151,194,246)", agriculture: "rgb(226,160,8)" };
  const measures = ["จำนวนลำ", "มูลค่า"];
  const y = (share) => margin.top + plotHeight - Number(share) * plotHeight;
  const parts = [
    `<svg aria-hidden="true" class="portable-static-chart-svg" focusable="false" height="${height}" preserveAspectRatio="xMidYMid meet" viewBox="0 0 ${width} ${height}" width="${width}" xmlns="http://www.w3.org/2000/svg">`,
  ];

  for (const tick of [0, 0.25, 0.5, 0.75, 1]) {
    const yPos = y(tick);
    parts.push(`<line stroke="${colors.grid}" stroke-width="1" x1="${margin.left}" x2="${width - margin.right}" y1="${yPos}" y2="${yPos}"></line>`);
    parts.push(`<text fill="${colors.muted}" font-family="Tahoma, Arial, sans-serif" font-size="12" text-anchor="end" x="${margin.left - 12}" y="${yPos + 4}">${Math.round(tick * 100)}%</text>`);
  }

  measures.forEach((measure, index) => {
    const xPos = margin.left + 120 + index * 310;
    const barWidth = 150;
    const general = rows.find((row) => row.measure === measure && row.segment === "โดรนทั่วไป");
    const agriculture = rows.find((row) => row.measure === measure && row.segment === "โดรนเกษตร");
    if (!general || !agriculture) throw new Error(`Missing composition rows for ${measure}`);
    const generalHeight = Number(general.share) * plotHeight;
    const agricultureHeight = Number(agriculture.share) * plotHeight;
    parts.push(`<rect fill="${colors.agriculture}" height="${agricultureHeight}" rx="3" ry="3" stroke="${colors.ink}" stroke-width="1" width="${barWidth}" x="${xPos}" y="${margin.top}"></rect>`);
    parts.push(`<rect fill="${colors.general}" height="${generalHeight}" rx="3" ry="3" stroke="${colors.ink}" stroke-width="1" width="${barWidth}" x="${xPos}" y="${margin.top + agricultureHeight}"></rect>`);
    parts.push(`<text dominant-baseline="middle" fill="${colors.ink}" font-family="Tahoma, Arial, sans-serif" font-size="14" font-weight="700" text-anchor="middle" x="${xPos + barWidth / 2}" y="${margin.top + agricultureHeight / 2}">${formatNumber(agriculture.share * 100, 1)}%</text>`);
    parts.push(`<text dominant-baseline="middle" fill="${colors.ink}" font-family="Tahoma, Arial, sans-serif" font-size="14" font-weight="700" text-anchor="middle" x="${xPos + barWidth / 2}" y="${margin.top + agricultureHeight + generalHeight / 2}">${formatNumber(general.share * 100, 1)}%</text>`);
    parts.push(`<text fill="${colors.ink}" font-family="Tahoma, Arial, sans-serif" font-size="14" font-weight="600" text-anchor="middle" x="${xPos + barWidth / 2}" y="${margin.top + plotHeight + 28}">${escapeXml(measure)}</text>`);
  });

  parts.push(`<line stroke="${colors.ink}" stroke-width="1" x1="${margin.left}" x2="${width - margin.right}" y1="${margin.top + plotHeight}" y2="${margin.top + plotHeight}"></line>`);
  parts.push("</svg>");
  return parts.join("");
}

const trendRows = artifact.snapshot.datasets.annual_trend;
const compositionRows = artifact.snapshot.datasets.segment_composition;

// The portable builder keys static chart representations by report block id,
// not by the chart id inside that block.
const staticCharts = {
  annual_chart: {
    width: 800,
    height: 360,
    light: {
      svg: annualTrendSvg(trendRows, "light"),
      legend: {
        position: "bottom",
        title: null,
        items: [
          { color: "rgb(30,104,204)", label: "มูลค่าที่วัดได้", marker: "line" },
          { color: "rgb(210,138,0)", label: "ค่าปรับ coverage (สมมติฐาน; เส้นประ)", marker: "line" },
        ],
      },
    },
    dark: {
      svg: annualTrendSvg(trendRows, "dark"),
      legend: {
        position: "bottom",
        title: null,
        items: [
          { color: "rgb(138,180,248)", label: "มูลค่าที่วัดได้", marker: "line" },
          { color: "rgb(253,214,99)", label: "ค่าปรับ coverage (สมมติฐาน; เส้นประ)", marker: "line" },
        ],
      },
    },
  },
  composition_chart: {
    width: 800,
    height: 340,
    light: {
      svg: compositionSvg(compositionRows, "light"),
      legend: {
        position: "bottom",
        title: null,
        items: [
          { color: "rgb(151,194,246)", label: "โดรนทั่วไป", marker: "dot" },
          { color: "rgb(226,160,8)", label: "โดรนเกษตร", marker: "dot" },
        ],
      },
    },
    dark: {
      svg: compositionSvg(compositionRows, "dark"),
      legend: {
        position: "bottom",
        title: null,
        items: [
          { color: "rgb(138,180,248)", label: "โดรนทั่วไป", marker: "dot" },
          { color: "rgb(253,214,99)", label: "โดรนเกษตร", marker: "dot" },
        ],
      },
    },
  },
};

let html = builderModule.buildPortableArtifact(artifact, { staticCharts });
const printFixes = `<style data-nbtc-print-fixes="true">
@media print {
  .portable-surface-label, .portable-page-meta, .portable-inline-source { display: none !important; }
  .portable-block { break-inside: avoid-page; }
  .portable-sources { display: none !important; }
  h1, h2, h3 { break-after: avoid-page; }
}
</style>`;
html = html.replace("</head>", `${printFixes}\n</head>`);
writeFileSync(reportPath, html, "utf8");

const verification = verifierModule.verifyPortableArtifactStructure({
  artifactPath,
  htmlPath: reportPath,
});
console.log(JSON.stringify({
  ok: verification.ok,
  html: verification.html,
  counts: verification.counts,
  staticChartBlocks: Object.keys(staticCharts),
}, null, 2));
