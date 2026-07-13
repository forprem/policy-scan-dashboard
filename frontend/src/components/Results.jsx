import { useState } from "react";
import Charts from "./Charts";
import TreeNode, { buildTree } from "./TreeView";
import DiffView from "./DiffView";
import { downloadScanPdf } from "../utils/pdfReport";
import { remediateIssue } from "../api";

export default function Results({ data }) {
  const [selectedIssues, setSelectedIssues] = useState([]);
  const [isGeneratingRemediationPdf, setIsGeneratingRemediationPdf] = useState(false);
  const [remediationProgress, setRemediationProgress] = useState({
    processed: 0,
    total: 0,
    success: 0,
    failed: 0,
  });
  const [cachedRemediationResults, setCachedRemediationResults] = useState(null);

  const downloadButtonStyle = {
    marginTop: "10px",
    marginBottom: "12px",
    padding: "9px 14px",
    borderRadius: "8px",
    border: "1px solid #14532d",
    background: "linear-gradient(180deg, #22c55e 0%, #15803d 100%)",
    color: "#fff",
    fontWeight: "600",
  };

  const remediationButtonStyle = {
    ...downloadButtonStyle,
    marginLeft: "10px",
    border: "1px solid #1e3a8a",
    background: "linear-gradient(180deg, #3b82f6 0%, #1d4ed8 100%)",
    opacity: isGeneratingRemediationPdf ? 0.7 : 1,
    cursor: isGeneratingRemediationPdf ? "not-allowed" : "pointer",
  };

  if (!data) return null;

  const getColor = (level) => {
    if (level === "HIGH") return "red";
    if (level === "MEDIUM") return "orange";
    return "green";
  };

  const toFindingKey = (finding, index) =>
    `${finding?.file || ""}:${finding?.line_number || ""}:${finding?.rule || ""}:${index}`;

  const normalizeRemediationResponse = (raw) => {
    if (!raw) {
      return {
        status: "error",
        explanation: "No remediation response",
        remediation_steps: [],
        fixed_code: "",
        error: "Empty response",
      };
    }

    return {
      status: raw.status || "ok",
      explanation:
        raw.explanation || raw.summary || raw.remediation || raw.message || "No explanation provided",
      remediation_steps:
        Array.isArray(raw.remediation_steps)
          ? raw.remediation_steps
          : raw.remediation_steps
            ? [String(raw.remediation_steps)]
            : [],
      fixed_code: raw.fixed_code || raw.secure_code || raw.code_fix || "",
      risk_summary: raw.risk_summary || "",
      error: raw.error || "",
    };
  };

  const runWithConcurrency = async (tasks, limit) => {
    const results = new Array(tasks.length);
    let cursor = 0;

    const worker = async () => {
      while (true) {
        const index = cursor;
        cursor += 1;
        if (index >= tasks.length) return;
        results[index] = await tasks[index]();
      }
    };

    const workerCount = Math.min(limit, tasks.length);
    await Promise.all(Array.from({ length: workerCount }, () => worker()));
    return results;
  };

  const handleDownloadRemediationPdf = async (findings) => {
    if (!Array.isArray(findings) || findings.length === 0 || isGeneratingRemediationPdf) {
      return;
    }

    // Already generated — skip Ollama calls and just re-download PDF
    if (cachedRemediationResults) {
      downloadScanPdf(data, { mode: "remediation", remediationResults: cachedRemediationResults });
      return;
    }

    await runRemediationBatch(findings, []);
  };

  const handleRetryFailed = async (findings) => {
    if (!cachedRemediationResults || isGeneratingRemediationPdf) return;

    const failedItems = cachedRemediationResults
      .map((r, i) => ({ result: r, finding: findings[i], index: i }))
      .filter(({ result }) => result?.status === "error");

    if (failedItems.length === 0) return;

    await runRemediationBatch(
      failedItems.map(({ finding }) => finding),
      failedItems.map(({ index }) => index),
    );
  };

  const runRemediationBatch = async (findings, originalIndexes) => {
    const isRetry = originalIndexes.length > 0;
    const total = findings.length;
    let processed = 0;
    let success = 0;
    let failed = 0;

    setIsGeneratingRemediationPdf(true);
    setRemediationProgress({ processed: 0, total, success: 0, failed: 0 });

    try {
      const tasks = findings.map((finding, batchIndex) => async () => {
        const index = isRetry ? originalIndexes[batchIndex] : batchIndex;
        const payload = {
          file: finding?.file,
          line_number: finding?.line_number,
          severity: finding?.severity,
          rule: finding?.rule,
          line_content: finding?.line_content,
          message: finding?.message,
        };

        try {
          const response = await remediateIssue(payload);
          const normalized = normalizeRemediationResponse(response?.data);
          if (normalized.status === "error") {
            failed += 1;
          } else {
            success += 1;
          }
          return {
            key: toFindingKey(finding, index),
            ...normalized,
          };
        } catch (err) {
          failed += 1;
          return {
            key: toFindingKey(finding, index),
            status: "error",
            explanation: "Failed to generate remediation",
            remediation_steps: [],
            fixed_code: "",
            error: err?.response?.data?.detail || err?.message || "Unknown error",
          };
        } finally {
          processed += 1;
          setRemediationProgress({ processed, total, success, failed });
        }
      });

      const batchResults = await runWithConcurrency(tasks, 3);

      // Merge retry results over existing cache, keeping successful ones
      const merged = isRetry
        ? cachedRemediationResults.map((existing, i) => {
            const retryIdx = originalIndexes.indexOf(i);
            if (retryIdx !== -1 && batchResults[retryIdx]) {
              return batchResults[retryIdx];
            }
            return existing;
          })
        : batchResults;

      setCachedRemediationResults(merged);

      downloadScanPdf(data, {
        mode: "remediation",
        remediationResults: merged,
      });
    } finally {
      setIsGeneratingRemediationPdf(false);
    }
  };

  // =========================
  // 🌐 WEBSITE SCAN
  // =========================
  if (data.risk_score !== undefined) {
    const score = data.risk_score;

    return (
      <div style={{ marginTop: "30px" }}>
        <h2>Website Security Dashboard</h2>
        <button style={downloadButtonStyle} onClick={() => downloadScanPdf(data)}>
          Download PDF Report
        </button>

        {/* 🔥 Risk Gauge */}
        <div
          style={{
            width: "150px",
            height: "150px",
            borderRadius: "50%",
            border: "10px solid",
            borderColor:
              score > 70 ? "red" : score > 40 ? "orange" : "green",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "24px",
            margin: "20px auto",
          }}
        >
          {score}
        </div>

        <div>
          <h3>SSL Info</h3>
          <p>Valid: {data.ssl?.valid ? "Yes" : "No"}</p>
          <p>Expiry: {data.ssl?.expiry}</p>
          <p>Issuer: {data.ssl?.issuer}</p>
        </div>

        <div>
          <h3>Missing Security Headers</h3>
          <ul>
            {data.headers?.missing_headers?.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  // =========================
  // 📦 REPO SCAN
  // =========================
  if (data.findings && Array.isArray(data.findings)) {
    const findingsCount = data.findings.length;
    const apiTotalIssues = Number(data.total_issues);
    const totalIssues = Number.isFinite(apiTotalIssues)
      ? Math.max(apiTotalIssues, findingsCount)
      : findingsCount;
    const tree = buildTree(data.findings);

    return (
      <div style={{ marginTop: "30px" }}>
        <h2>Repository Security Dashboard</h2>
        <button style={downloadButtonStyle} onClick={() => downloadScanPdf(data)}>
          Download PDF Report
        </button>
        <button
          style={remediationButtonStyle}
          onClick={() => handleDownloadRemediationPdf(data.findings)}
          disabled={isGeneratingRemediationPdf}
        >
          {isGeneratingRemediationPdf
            ? "Generating Remediation PDF..."
            : cachedRemediationResults
              ? "Re-download Remediation PDF"
              : "Download Remediation PDF"}
        </button>
        {isGeneratingRemediationPdf ? (
          <p style={{ marginTop: "8px", color: "#1d4ed8", fontSize: "14px" }}>
            Remediation progress: {remediationProgress.processed}/{remediationProgress.total} | Success: {remediationProgress.success} | Failed: {remediationProgress.failed}
          </p>
        ) : null}
        {!isGeneratingRemediationPdf && cachedRemediationResults && remediationProgress.failed > 0 ? (
          <button
            style={{
              ...remediationButtonStyle,
              marginLeft: "10px",
              border: "1px solid #991b1b",
              background: "linear-gradient(180deg, #ef4444 0%, #b91c1c 100%)",
            }}
            onClick={() => handleRetryFailed(data.findings)}
          >
            Retry Failed ({remediationProgress.failed})
          </button>
        ) : null}
        <p style={{
          fontSize: "18px",
          fontWeight: "bold",
          marginTop: "10px"
        }}>
          Total Issues: {totalIssues}
        </p>
        {/* 📊 Charts */}
        <Charts findings={data.findings} />

        {/* 📁 Tree View */}
        <div style={{
            marginTop: "20px",
            textAlign: "left"
          }}>
          <h3>Files</h3>

          <TreeNode
            node={tree}
            name="repo"
            onSelect={(issues) => setSelectedIssues(issues)}
          />
        </div>

        {/* 🔍 Diff View */}
        <DiffView issues={selectedIssues} />
      </div>
    );
  }

  return null;
}