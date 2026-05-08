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
    setLoading(true);
    setData(null);

    try {
      const res = await scanRepo(repo, pat);
      setData(res.data);
    } catch {
      alert("Repo scan failed");
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