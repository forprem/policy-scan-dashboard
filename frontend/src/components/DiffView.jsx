import { useState } from "react";
import { explainIssue } from "../api";
import "./DiffView.css";

export default function DiffView({ issues }) {
  const [explanations, setExplanations] = useState({});
  const [loadingMap, setLoadingMap] = useState({});

  const getIssueKey = (issue, index) =>
    `${issue.file || "unknown"}-${issue.line_number || "?"}-${index}`;

  const getExplanation = async (issue) => {
    const key = getIssueKey(issue, issue.__index);

    // Toggle open/close if explanation already exists.
    if (explanations[key]?.text && !loadingMap[key]) {
      setExplanations((prev) => ({
        ...prev,
        [key]: {
          ...prev[key],
          open: !prev[key].open,
        },
      }));
      return;
    }

    setLoadingMap((prev) => ({ ...prev, [key]: true }));
    const startedAt = performance.now();

    try {
      const res = await explainIssue(issue);
      const elapsedSeconds = (performance.now() - startedAt) / 1000;
      setExplanations((prev) => ({
        ...prev,
        [key]: {
          text: res.data?.explanation || "No explanation returned.",
          error: false,
          open: true,
          elapsedSeconds,
        },
      }));
    } catch (err) {
      const elapsedSeconds = (performance.now() - startedAt) / 1000;
      setExplanations((prev) => ({
        ...prev,
        [key]: {
          text: "Failed to get explanation.",
          error: true,
          open: true,
          elapsedSeconds,
        },
      }));
    } finally {
      setLoadingMap((prev) => ({ ...prev, [key]: false }));
    }
  };

  const normalizeLine = (line) => line.trim().replace(/^\*+\s*/, "").replace(/\*+\s*$/, "");

  const getSectionFromHeading = (line) => {
    const normalized = normalizeLine(line);

    if (/^1\.\s*/.test(normalized)) return 1;
    if (/^2\.\s*/.test(normalized)) return 2;
    if (/^3\.\s*(secure alternative|secure alternatives)\s*:?.*$/i.test(normalized)) return 3;
    if (/^4\.\s*(best practice|best practices)\s*:?.*$/i.test(normalized)) return 4;
    if (/^5\.\s*(sample code snippet fix|sample code)\s*:?.*$/i.test(normalized)) return 5;

    return null;
  };

  const renderExplanationText = (text) => {
    let inCodeBlock = false;

    return text.split("\n").map((line, index, lines) => {
      const trimmedLine = line.trim();

      if (trimmedLine.startsWith("```")) {
        inCodeBlock = !inCodeBlock;
        return null;
      }

      const isNumberedHeading =
        /^\*\*1\.\s*/.test(trimmedLine) ||
        /^\*\*2\.\s*/.test(trimmedLine) ||
        /^\*\*3\.\s*/.test(trimmedLine) ||
        /^\*\*4\.\s*/.test(trimmedLine) ||
        /^\*\*5\.\s*/.test(trimmedLine);

      const sectionAtLine = (() => {
        let activeSection = null;

        for (let cursor = 0; cursor <= index; cursor += 1) {
          const candidate = lines[cursor];
          const detectedSection = getSectionFromHeading(candidate);

          if (detectedSection !== null) {
            activeSection = detectedSection;
          }
        }

        return activeSection;
      })();

      const isRedSection = sectionAtLine === 1 || sectionAtLine === 2;
      const isGreenSection = sectionAtLine === 3 || sectionAtLine === 4 || sectionAtLine === 5;

      const displayLine = line
        .replace(/^\*\*(.+?)\*\*/, "$1")
        .replace(/^\*\s+/, "");

      return (
        <div
          key={`${index}-${line}`}
          className={
            isNumberedHeading
              ? isRedSection
                ? "explanation-line explanation-line--danger explanation-line--heading"
                : isGreenSection
                ? "explanation-line explanation-line--good explanation-line--heading"
                : "explanation-line explanation-line--heading"
              : isRedSection
              ? inCodeBlock
                ? "explanation-line explanation-line--danger explanation-line--code"
                : "explanation-line explanation-line--danger explanation-line--content"
              : isGreenSection
              ? inCodeBlock
                ? "explanation-line explanation-line--good explanation-line--code"
                : "explanation-line explanation-line--good explanation-line--content"
              : inCodeBlock
              ? "explanation-line explanation-line--code"
              : "explanation-line explanation-line--content"
          }
        >
          {displayLine}
        </div>
      );
    });
  };

  if (!issues || issues.length === 0) {
    return (
      <div style={{ marginTop: "20px" }}>
        <h3>Select a file to view issues</h3>
      </div>
    );
  }

  return (
    <div className="diff-view">
      <h3>Code Issues</h3>

      {issues.map((f, i) => {
        const issue = { ...f, __index: i };
        const key = getIssueKey(issue, i);
        const explanation = explanations[key];
        const isLoading = loadingMap[key];

        return (
        <div key={i} className="issue-card">
          <pre
            style={{
              background: "#111",
              color: "white",
              padding: "10px",
              borderLeft: `5px solid ${
                f.severity === "HIGH"
                  ? "red"
                  : f.severity === "MEDIUM"
                  ? "orange"
                  : "green"
              }`,
            }}
          >
{`${f.line_number || "?"}: ${f.line_content || f.message}`}
          </pre>

          <button
            className="explain-btn"
            onClick={() => getExplanation(issue)}
            disabled={isLoading}
          >
            {isLoading
              ? "Explaining..."
              : explanation?.open
              ? "Hide Explanation"
              : "Explain"}
          </button>

          {explanation?.elapsedSeconds !== undefined && (
            <div className="explain-timing">
              Response time: {explanation.elapsedSeconds.toFixed(2)}s
            </div>
          )}

          {explanation?.open && (
            <div
              className={`explanation-panel ${
                explanation.error ? "is-error" : "is-success"
              }`}
            >
              {renderExplanationText(explanation.text)}
            </div>
          )}
        </div>
      )})}
    </div>
  );
}