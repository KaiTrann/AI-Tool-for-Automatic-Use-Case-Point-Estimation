// Biểu đồ cột thể hiện phân bố độ phức tạp của actor và use case.
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

function ChartPanel({ extraction }) {
  if (!extraction) {
    return (
      <div className="stack-md">
        <div>
          <h2 className="section-title">Phân Bố Complexity</h2>
          <p className="section-copy">
            Hãy trích xuất dữ liệu trước để hiển thị phân bố Complexity của Actor và Use Case từ Requirements Text.
          </p>
        </div>
        <div className="empty-chart-state">Biểu đồ sẽ xuất hiện sau khi trích xuất dữ liệu.</div>
      </div>
    );
  }

  const actorCounts = countByComplexity(extraction.actors ?? []);
  const useCaseCounts = countByComplexity(extraction.use_cases ?? []);

  const chartData = {
    labels: ["Simple", "Average", "Complex"],
    datasets: [
      {
        label: "Actor",
        data: [actorCounts.simple, actorCounts.average, actorCounts.complex],
        backgroundColor: "#15616d",
        borderRadius: 8,
      },
      {
        label: "Use Case",
        data: [useCaseCounts.simple, useCaseCounts.average, useCaseCounts.complex],
        backgroundColor: "#ff7d00",
        borderRadius: 8,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: "#23303f",
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          precision: 0,
        },
      },
    },
  };

  return (
    <div className="stack-md">
      <div>
        <h2 className="section-title">Phân Bố Complexity</h2>
        <p className="section-copy">
          Biểu đồ này so sánh số lượng Actor và Use Case ở ba mức: Simple, Average và Complex.
        </p>
      </div>

      <div className="chart-card">
        <div className="chart-wrapper">
          <Bar data={chartData} options={chartOptions} />
        </div>
      </div>
    </div>
  );
}

function countByComplexity(items) {
  return items.reduce(
    (counts, item) => {
      const key = item.complexity ?? "simple";
      if (Object.hasOwn(counts, key)) {
        counts[key] += 1;
      }
      return counts;
    },
    { simple: 0, average: 0, complex: 0 }
  );
}

export default ChartPanel;
