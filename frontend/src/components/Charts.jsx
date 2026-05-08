import {
  Chart as ChartJS,
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
} from "chart.js";
import { Pie, Bar } from "react-chartjs-2";

ChartJS.register(
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
);

export default function Charts({ findings }) {
  const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 };

  findings.forEach(f => {
    counts[f.severity] = (counts[f.severity] || 0) + 1;
  });

  const pieData = {
    labels: ["HIGH", "MEDIUM", "LOW"],
    datasets: [
      {
        data: [counts.HIGH, counts.MEDIUM, counts.LOW],
        backgroundColor: [
          "#ef4444",
          "#f59e0b",
          "#22c55e"
        ]
      }
    ]
  };

  const barData = {
    labels: ["HIGH", "MEDIUM", "LOW"],
    datasets: [
      {
        label: "Issues",
        data: [counts.HIGH, counts.MEDIUM, counts.LOW],
        backgroundColor: [
          "#ef4444",
          "#f59e0b",
          "#22c55e"
        ]
      }
    ]
  };

  return (
    <div style={{ display: "flex", gap: "40px", marginTop: "20px" }}>
      <div style={{ width: "300px" }}>
        <Pie data={pieData} />
      </div>

      <div style={{ width: "400px" }}>
        <Bar data={barData} />
      </div>
    </div>
  );
}