import { useState } from "react";
import Charts from "./Charts";
import TreeNode, { buildTree } from "./TreeView";
import DiffView from "./DiffView";

export default function Results({ data }) {
  const [selectedIssues, setSelectedIssues] = useState([]);

  if (!data) return null;

  const getColor = (level) => {
    if (level === "HIGH") return "red";
    if (level === "MEDIUM") return "orange";
    return "green";
  };

  // =========================
  // 🌐 WEBSITE SCAN
  // =========================
  if (data.risk_score !== undefined) {
    const score = data.risk_score;

    return (
      <div style={{ marginTop: "30px" }}>
        <h2>Website Security Dashboard</h2>

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
    const tree = buildTree(data.findings);

    return (
      <div style={{ marginTop: "30px" }}>
        <h2>Repository Security Dashboard</h2>
        <p style={{
          fontSize: "18px",
          fontWeight: "bold",
          marginTop: "10px"
        }}>
          Total Issues: {data.total_issues}
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