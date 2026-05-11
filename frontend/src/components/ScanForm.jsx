import { useState } from "react";

export default function ScanForm({ onScanSite, onScanRepo }) {
  const [url, setUrl] = useState("");
  const [repo, setRepo] = useState("");
  const [pat, setPat] = useState("");
  const isAzureRepo = repo.includes("dev.azure.com");

  return (
    <div style={styles.container}>

      {/* ===================== */}
      {/* 🌐 WEBSITE SCAN CARD */}
      {/* ===================== */}
      <div style={styles.card}>
        <h3 style={styles.title}>🌐 Website Scan</h3>

        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com"
          style={styles.input}
        />

        <button
          style={styles.primaryButton}
          onClick={() => onScanSite(url)}
        >
          Scan Website
        </button>
      </div>

      {/* ===================== */}
      {/* 📦 REPO SCAN CARD */}
      {/* ===================== */}
      <div style={styles.card}>
        <h3 style={styles.title}>📦 Repository Scan</h3>

        <input
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="https://dev.azure.com/org/project/_git/repo"
          style={styles.input}
        />

        {isAzureRepo && (
          <input
            type="password"
            value={pat}
            onChange={(e) => setPat(e.target.value)}
            placeholder="Azure DevOps PAT"
          />
        )}

        <button
          style={styles.secondaryButton}
          onClick={() => onScanRepo(repo, pat)}
        >
          Scan Repository
        </button>
      </div>

    </div>
  );
}

const styles = {
  container: {
    maxWidth: "700px",
    margin: "30px auto",
    display: "flex",
    flexDirection: "column",
    gap: "20px"
  },

  card: {
    background: "#0f172a",
    padding: "20px",
    borderRadius: "12px",
    boxShadow: "0 4px 20px rgba(0,0,0,0.3)",
    display: "flex",
    flexDirection: "column",
    gap: "12px"
  },

  title: {
    color: "white",
    marginBottom: "10px"
  },

  input: {
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #334155",
    background: "#111827",
    color: "white",
    fontSize: "14px"
  },

  primaryButton: {
    padding: "10px",
    background: "#3b82f6",
    color: "white",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    fontWeight: "bold"
  },

  secondaryButton: {
    padding: "10px",
    background: "#10b981",
    color: "white",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    fontWeight: "bold"
  }
};
