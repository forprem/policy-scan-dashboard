import { jsPDF } from "jspdf";

const PAGE_WIDTH = 210;
const PAGE_HEIGHT = 297;
const LEFT_MARGIN = 14;
const RIGHT_MARGIN = 14;
const BOTTOM_MARGIN = 16;
const CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN;

function createDoc() {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  return { doc, y: 18 };
}

function ensureSpace(state, neededHeight = 8) {
  if (state.y + neededHeight <= PAGE_HEIGHT - BOTTOM_MARGIN) return;

  state.doc.addPage();
  state.y = 18;
}

function addSectionTitle(state, text, bgColor = [59, 130, 246]) {
  ensureSpace(state, 10);
  
  state.doc.setFillColor(...bgColor);
  state.doc.rect(LEFT_MARGIN - 1, state.y - 5, CONTENT_WIDTH + 2, 8, "F");
  
  state.doc.setFont("helvetica", "bold");
  state.doc.setFontSize(12);
  state.doc.setTextColor(255, 255, 255);
  state.doc.text(text, LEFT_MARGIN + 1, state.y);
  state.doc.setTextColor(0, 0, 0);
  
  state.y += 8;
}

function addParagraph(state, text, options = {}) {
  const { bullet = false } = options;
  const linePrefix = bullet ? "- " : "";
  const wrapped = state.doc.splitTextToSize(`${linePrefix}${text}`, CONTENT_WIDTH);

  state.doc.setFont("helvetica", "normal");
  state.doc.setFontSize(11);

  wrapped.forEach((line) => {
    ensureSpace(state, 6);
    state.doc.text(line, LEFT_MARGIN, state.y);
    state.y += 5.5;
  });
}

function addHeader(state, title, metaLine = "") {
  const hasMeta = Boolean(metaLine);
  const headerHeight = hasMeta ? 36 : 30;

  state.doc.setFillColor(15, 23, 42);
  state.doc.rect(0, 0, PAGE_WIDTH, headerHeight, "F");

  state.doc.setFont("helvetica", "bold");
  state.doc.setFontSize(18);
  state.doc.setTextColor(255, 255, 255);
  state.doc.text(title, LEFT_MARGIN, 12);

  state.doc.setFont("helvetica", "normal");
  state.doc.setFontSize(10);
  state.doc.setTextColor(180, 180, 180);
  state.doc.text(`Generated: ${new Date().toLocaleString()}`, LEFT_MARGIN, 20);

  if (hasMeta) {
    const displayMeta = state.doc.splitTextToSize(`Repository: ${metaLine}`, PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN);
    state.doc.setFontSize(9);
    state.doc.text(displayMeta[0], LEFT_MARGIN, 28);
  }

  state.doc.setTextColor(0, 0, 0);
  state.y = hasMeta ? 41 : 35;
}

function getRepoUrl(data) {
  return (
    data?.repo_url ||
    data?.repo ||
    data?.repository ||
    data?.repository_url ||
    ""
  );
}

function getSafeValue(value, fallback = "N/A") {
  if (value === undefined || value === null || value === "") return fallback;
  return String(value);
}

function normalizeSeverity(severity) {
  const sev = (severity || "LOW").toString().toUpperCase();
  if (["CRITICAL", "HIGH", "MEDIUM", "LOW"].includes(sev)) return sev;
  return "LOW";
}

function getSeverityRank(severity) {
  const sev = normalizeSeverity(severity);
  if (sev === "CRITICAL") return 4;
  if (sev === "HIGH") return 3;
  if (sev === "MEDIUM") return 2;
  return 1;
}

function getSeverityColor(severity) {
  const sev = normalizeSeverity(severity);
  if (sev === "CRITICAL") return [220, 38, 38];
  if (sev === "HIGH") return [239, 68, 68];
  if (sev === "MEDIUM") return [245, 158, 11];
  return [34, 197, 81];
}

function getSeverityCodeBgColor(severity) {
  const sev = normalizeSeverity(severity);
  if (sev === "CRITICAL") return [254, 226, 226];
  if (sev === "HIGH") return [254, 242, 242];
  if (sev === "MEDIUM") return [255, 247, 237];
  return [240, 253, 244];
}

function makePieImage(high, medium, low) {
  const total = high + medium + low;
  if (total === 0) return null;
  const size = 300;
  const cx = size / 2, cy = size / 2, r = 130, rInner = 52;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");

  const slices = [
    { value: high,   color: "#ef4444" },
    { value: medium, color: "#f59e0b" },
    { value: low,    color: "#22c55e" },
  ];

  let startAngle = -Math.PI / 2;
  slices.forEach(({ value, color }) => {
    if (value === 0) return;
    const sweep = (value / total) * 2 * Math.PI;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, startAngle, startAngle + sweep);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    startAngle += sweep;
  });

  // white donut hole
  ctx.beginPath();
  ctx.arc(cx, cy, rInner, 0, 2 * Math.PI);
  ctx.fillStyle = "#ffffff";
  ctx.fill();

  return canvas.toDataURL("image/png");
}

function getComputedTotalIssues(data, findings) {
  const findingsCount = Array.isArray(findings) ? findings.length : 0;
  const apiTotalIssues = Number(data?.total_issues);

  if (!Number.isFinite(apiTotalIssues)) return findingsCount;
  return Math.max(apiTotalIssues, findingsCount);
}

function addCharts(state, severityCounts) {
  const high = severityCounts.HIGH || 0;
  const medium = severityCounts.MEDIUM || 0;
  const low = severityCounts.LOW || 0;
  const total = high + medium + low;

  const colors = {
    HIGH: [239, 68, 68],
    MEDIUM: [245, 158, 11],
    LOW: [34, 197, 81]
  };

  const severities = [
    { label: "HIGH", count: high, color: colors.HIGH },
    { label: "MEDIUM", count: medium, color: colors.MEDIUM },
    { label: "LOW", count: low, color: colors.LOW }
  ];

  // ===== BAR + PIE CHARTS SIDE BY SIDE =====
  ensureSpace(state, 70);
  state.doc.setFont("helvetica", "bold");
  state.doc.setFontSize(11);
  state.doc.text("Issues by Severity", LEFT_MARGIN, state.y);
  state.doc.text("Severity Distribution", LEFT_MARGIN + 100, state.y);
  state.y += 8;

  const chartStartY = state.y;
  const chartStartX = LEFT_MARGIN + 10;
  const chartWidth = 50;
  const chartHeight = 30;
  const barSpacing = 18;
  const maxCount = Math.max(high, medium, low, 1);

  // Y-axis and X-axis
  state.doc.setDrawColor(0, 0, 0);
  state.doc.setLineWidth(0.5);
  state.doc.line(chartStartX - 2, chartStartY, chartStartX - 2, chartStartY + chartHeight);
  state.doc.line(chartStartX - 2, chartStartY + chartHeight, chartStartX + chartWidth, chartStartY + chartHeight);
  state.doc.setFont("helvetica", "normal");
  state.doc.setFontSize(8);
  state.doc.setTextColor(100, 100, 100);
  state.doc.text("0", chartStartX - 6, chartStartY + chartHeight + 1);
  state.doc.text(String(maxCount), chartStartX - 7, chartStartY - 2);
  state.doc.setDrawColor(220, 220, 220);
  state.doc.setLineWidth(0.2);
  for (let i = 1; i < 4; i++) {
    state.doc.line(chartStartX - 2, chartStartY + (chartHeight / 4) * i, chartStartX + chartWidth, chartStartY + (chartHeight / 4) * i);
  }
  let barX = chartStartX;
  severities.forEach((sev) => {
    const barWidth = 12;
    const barH = (sev.count / maxCount) * chartHeight;
    state.doc.setFillColor(...sev.color);
    state.doc.rect(barX, chartStartY + chartHeight - barH, barWidth, barH, "F");
    state.doc.setFont("helvetica", "bold");
    state.doc.setFontSize(9);
    state.doc.setTextColor(...sev.color);
    state.doc.text(String(sev.count), barX + barWidth / 2 - 1.5, chartStartY + chartHeight - barH - 1.5);
    state.doc.setFont("helvetica", "normal");
    state.doc.setFontSize(8);
    state.doc.setTextColor(0, 0, 0);
    state.doc.text(sev.label, barX - 1, chartStartY + chartHeight + 5);
    barX += barSpacing;
  });

  // Pie chart to the right of bar chart
  const pieImg = makePieImage(high, medium, low);
  if (pieImg) {
    const pieSize = 40;
    const pieX = LEFT_MARGIN + 100;
    const pieY = chartStartY - 4;
    state.doc.addImage(pieImg, "PNG", pieX, pieY, pieSize, pieSize);

    const legendX = pieX + pieSize + 5;
    let legendY = pieY + 8;
    state.doc.setFont("helvetica", "normal");
    state.doc.setFontSize(9);
    severities.forEach((sev) => {
      const percent = total > 0 ? ((sev.count / total) * 100).toFixed(1) : "0";
      state.doc.setFillColor(...sev.color);
      state.doc.rect(legendX, legendY - 2.5, 4, 4, "F");
      state.doc.setTextColor(0, 0, 0);
      state.doc.text(`${sev.label}: ${sev.count} (${percent}%)`, legendX + 6, legendY + 0.5);
      legendY += 7;
    });
  }

  state.y = chartStartY + chartHeight + 16;
}

function buildWebsiteReport(data) {
  const state = createDoc();

  addHeader(state, "Policy Scanner - Website Scan Report");

  addSectionTitle(state, "Risk Summary", [59, 130, 246]);
  
  const score = getSafeValue(data.risk_score);
  state.doc.setFont("helvetica", "bold");
  state.doc.setFontSize(14);
  const scoreColor = data.risk_score > 70 ? [239, 68, 68] :
                     data.risk_score > 40 ? [245, 158, 11] : [34, 197, 81];
  state.doc.setTextColor(...scoreColor);
  addParagraph(state, `Risk Score: ${score}`);
  state.doc.setTextColor(0, 0, 0);

  addSectionTitle(state, "SSL Information", [59, 130, 246]);
  state.doc.setFont("helvetica", "normal");
  addParagraph(state, `Valid: ${data.ssl?.valid ? "Yes" : "No"}`);
  addParagraph(state, `Expiry: ${getSafeValue(data.ssl?.expiry)}`);
  addParagraph(state, `Issuer: ${getSafeValue(data.ssl?.issuer)}`);

  addSectionTitle(state, "Missing Security Headers", [37, 99, 235]);
  const missingHeaders = data.headers?.missing_headers || [];

  if (missingHeaders.length === 0) {
    addParagraph(state, "No missing security headers detected.");
  } else {
    missingHeaders.forEach((header) => addParagraph(state, header, { bullet: true }));
  }

  return state.doc;
}

function buildRepoReport(data) {
  const state = createDoc();

  addHeader(state, "Policy Scanner - Repository Scan Report", getRepoUrl(data));

  const findings = Array.isArray(data.findings) ? data.findings : [];
  const totalIssues = getComputedTotalIssues(data, findings);
  const severityCounts = findings.reduce(
    (acc, item) => {
      const severity = (item.severity || "LOW").toUpperCase();
      if (!acc[severity]) acc[severity] = 0;
      acc[severity] += 1;
      return acc;
    },
    { HIGH: 0, MEDIUM: 0, LOW: 0 }
  );

  addSectionTitle(state, "Scan Summary", [59, 130, 246]);
  
  state.doc.setFont("helvetica", "normal");
  state.doc.setFontSize(11);
  addParagraph(state, `Total Issues: ${totalIssues}`);
  
  state.doc.setTextColor(239, 68, 68);
  addParagraph(state, `High: ${severityCounts.HIGH}`);
  state.doc.setTextColor(245, 158, 11);
  addParagraph(state, `Medium: ${severityCounts.MEDIUM}`);
  state.doc.setTextColor(34, 197, 81);
  addParagraph(state, `Low: ${severityCounts.LOW}`);
  state.doc.setTextColor(0, 0, 0);

  state.y += 3;
  addCharts(state, severityCounts);

  addSectionTitle(state, "Top Risky Files", [37, 99, 235]);

  const fileStats = findings.reduce((acc, item) => {
    const file = getSafeValue(item.file, "Unknown file");
    const severity = normalizeSeverity(item.severity);

    if (!acc[file]) {
      acc[file] = { file, count: 0, maxSeverity: severity };
    }

    acc[file].count += 1;
    if (getSeverityRank(severity) > getSeverityRank(acc[file].maxSeverity)) {
      acc[file].maxSeverity = severity;
    }

    return acc;
  }, {});

  const topRiskyFiles = Object.values(fileStats)
    .sort((a, b) => {
      if (b.count !== a.count) return b.count - a.count;
      if (getSeverityRank(b.maxSeverity) !== getSeverityRank(a.maxSeverity)) {
        return getSeverityRank(b.maxSeverity) - getSeverityRank(a.maxSeverity);
      }
      return a.file.localeCompare(b.file);
    })
    .slice(0, 5);

  if (topRiskyFiles.length === 0) {
    addParagraph(state, "No file-level findings available.");
  } else {
    const fileX = LEFT_MARGIN;
    const issuesX = LEFT_MARGIN + 120;
    const severityX = LEFT_MARGIN + 146;

    ensureSpace(state, 8);
    state.doc.setFont("helvetica", "bold");
    state.doc.setFontSize(10);
    state.doc.setTextColor(60, 60, 60);
    state.doc.text("File", fileX, state.y);
    state.doc.text("Issues", issuesX, state.y);
    state.doc.text("Severity", severityX, state.y);
    state.y += 4;

    state.doc.setDrawColor(220, 220, 220);
    state.doc.setLineWidth(0.3);
    state.doc.line(LEFT_MARGIN, state.y, PAGE_WIDTH - RIGHT_MARGIN, state.y);
    state.y += 3;

    topRiskyFiles.forEach((entry) => {
      const fileLines = state.doc.splitTextToSize(entry.file, 112);
      const rowHeight = Math.max(6, fileLines.length * 4.6);
      ensureSpace(state, rowHeight + 2);

      state.doc.setFont("helvetica", "normal");
      state.doc.setFontSize(9);
      state.doc.setTextColor(30, 30, 30);
      fileLines.forEach((line, idx) => {
        state.doc.text(line, fileX, state.y + idx * 4.4);
      });

      state.doc.setFont("helvetica", "bold");
      state.doc.text(String(entry.count), issuesX, state.y);

      state.doc.setTextColor(...getSeverityColor(entry.maxSeverity));
      state.doc.text(entry.maxSeverity, severityX, state.y);

      state.doc.setDrawColor(235, 235, 235);
      state.doc.setLineWidth(0.2);
      state.doc.line(LEFT_MARGIN, state.y + rowHeight, PAGE_WIDTH - RIGHT_MARGIN, state.y + rowHeight);

      state.y += rowHeight + 2;
    });

    state.doc.setTextColor(0, 0, 0);
    state.y += 2;
  }

  addSectionTitle(state, "Findings", [37, 99, 235]);

  if (findings.length === 0) {
    addParagraph(state, "No repository findings detected.");
    return state.doc;
  }

  findings.forEach((finding, index) => {
    ensureSpace(state, 20);

    state.doc.setDrawColor(220, 220, 220);
    state.doc.setLineWidth(0.3);
    state.doc.line(LEFT_MARGIN, state.y, PAGE_WIDTH - RIGHT_MARGIN, state.y);
    state.y += 4;

    // Build title: cleaned filename (no extension, underscores → spaces)
    const rawFile = finding.file || "";
    const baseName = rawFile.split("/").pop().split("\\").pop();
    const cleanName = baseName.replace(/\.[^.]+$/, "").replace(/_/g, " ");
    const severity = normalizeSeverity(finding.severity);
    const severityColor = getSeverityColor(severity);

    // Finding number + file name
    state.doc.setFont("helvetica", "bold");
    state.doc.setFontSize(11);
    state.doc.setTextColor(60, 60, 60);
    state.doc.text(`#${index + 1}  ${cleanName || "Finding"}`, LEFT_MARGIN, state.y);

    // Severity badge inline (right after name)
    const nameWidth = state.doc.getTextWidth(`#${index + 1}  ${cleanName || "Finding"}`);
    state.doc.setFillColor(...severityColor);
    state.doc.roundedRect(LEFT_MARGIN + nameWidth + 3, state.y - 4, state.doc.getTextWidth(severity) + 6, 5.5, 1, 1, "F");
    state.doc.setTextColor(255, 255, 255);
    state.doc.setFontSize(9);
    state.doc.text(severity, LEFT_MARGIN + nameWidth + 6, state.y);
    state.y += 5.5;

    state.doc.setTextColor(0, 0, 0);
    state.doc.setFont("helvetica", "normal");
    state.doc.setFontSize(10);
    addParagraph(state, `File: ${getSafeValue(finding.file)}`);
    addParagraph(state, `Line: ${getSafeValue(finding.line_number)}`);

    const detail = finding.line_content || finding.message || "";
    if (detail) {
      const codeBg = getSeverityCodeBgColor(severity);
      state.doc.setFont("helvetica", "oblique");
      state.doc.setFontSize(12);
      const codeLines = state.doc.splitTextToSize(detail, CONTENT_WIDTH - 4);
      codeLines.forEach((line) => {
        ensureSpace(state, 7);
        state.doc.setFillColor(...codeBg);
        state.doc.rect(LEFT_MARGIN + 2, state.y - 4.5, CONTENT_WIDTH - 4, 6, "F");
        state.doc.setTextColor(20, 20, 20);
        state.doc.text(line, LEFT_MARGIN + 4, state.y);
        state.y += 6;
      });
      state.doc.setTextColor(0, 0, 0);
      state.doc.setFont("helvetica", "normal");
      state.doc.setFontSize(10);
    }

    state.y += 3;
  });

  return state.doc;
}

export function downloadScanPdf(data) {
  if (!data) return;

  const isWebsiteReport = data.risk_score !== undefined;
  const doc = isWebsiteReport ? buildWebsiteReport(data) : buildRepoReport(data);
  const fileName = isWebsiteReport
    ? `website-scan-report-${Date.now()}.pdf`
    : `repo-scan-report-${Date.now()}.pdf`;

  doc.save(fileName);
}
