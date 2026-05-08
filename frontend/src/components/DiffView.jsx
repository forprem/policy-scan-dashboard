export default function DiffView({ issues }) {
  // 🔥 AI Explain API
  const getExplanation = async (issue) => {
    try {
      const res = await fetch("http://localhost:8000/explain", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(issue),
      });

      const data = await res.json();
      alert(data.explanation);
    } catch (err) {
      alert("Failed to get explanation");
    }
  };

  if (!issues || issues.length === 0) {
    return (
      <div style={{ marginTop: "20px" }}>
        <h3>Select a file to view issues</h3>
      </div>
    );
  }

  return (
    <div style={{ marginTop: "20px" }}>
      <h3>Code Issues</h3>

      {issues.map((f, i) => (
        <div key={i} style={{ marginBottom: "15px" }}>
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

          <button onClick={() => getExplanation(f)}>
            Explain
          </button>
        </div>
      ))}
    </div>
  );
}