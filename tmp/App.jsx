import { useState } from "react";
import ScanForm from "./components/ScanForm";
import Results from "./components/Results";
import { scanSite, scanRepo } from "./api";

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleScanSite = async (url) => {
    setLoading(true);
    setData(null);

    try {
      const res = await scanSite(url);
      setData(res.data);
    } catch {
      alert("Site scan failed");
    }

    setLoading(false);
  };

  const handleScanRepo = async (repo, pat) => {
    const trimmedRepo = repo?.trim();
    if (!trimmedRepo) {
      alert("Please enter a repository URL");
      return;
    }

    setLoading(true);
    setData(null);

    try {
      const res = await scanRepo(trimmedRepo, pat);
      setData({
        ...res.data,
        repo_url: res?.data?.repo_url || trimmedRepo,
      });
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        err?.message ||
        "Repo scan failed";
      alert(`Repo scan failed: ${message}`);
    }

    setLoading(false);
  };

  return (
    <div style={{ padding: "30px" }}>
      <h1 style={{
        textAlign: "center",
        color: "#3b82f6",
        fontSize: "28px",
        marginBottom: "20px"
      }}>
        Policy Scanner
      </h1>

      <ScanForm
        onScanSite={handleScanSite}
        onScanRepo={handleScanRepo}
      />

      {loading && <p>Scanning...</p>}

      <Results data={data} />
    </div>
  );
}

export default App;