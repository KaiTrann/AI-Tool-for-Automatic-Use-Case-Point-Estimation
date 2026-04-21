// Trang chính của hệ thống.
// File này chứa gần như toàn bộ luồng chạy ở frontend:
// 1. Nhận Use Case Document theo template từ người dùng
// 2. Cho phép dán text hoặc upload file .doc/.docx/.txt
// 3. Gọi API backend để trích xuất actor và use case
// 4. Hiển thị bảng và kết quả tính toán UCP

import { useEffect, useState } from "react";

import {
  analyzeAndCalculate,
  calculateUCP,
  checkHealth,
  // Gọi API xóa một run trong lịch sử.
  deleteAnalysisRun,
  extractData,
  // Gọi API lấy chi tiết một run.
  getAnalysisRun,
  // Gọi API lấy danh sách run đã lưu.
  listAnalysisRuns,
} from "../api/client";
import ActorsTable from "../components/ActorsTable";
import ChartPanel from "../components/ChartPanel";
// Component hiển thị bảng lịch sử tính toán từ MySQL.
import HistoryPanel from "../components/HistoryPanel";
import ResultCards from "../components/ResultCards";
import UseCasesTable from "../components/UseCasesTable";
import { buildInputSignature, buildUcpPayload } from "../utils/requestHelpers";

// Mô tả ngắn cho từng chế độ LLM Mode để người dùng demo hiểu rõ sự khác nhau.
const llmModeDescriptions = {
  mock: "Mock Mode: dùng rule-based extractor chạy hoàn toàn local để demo ổn định, không gọi dịch vụ AI bên ngoài.",
  placeholder:
    "Placeholder API Mode: mô phỏng luồng sẽ gọi LLM thật trong tương lai. Hiện tại vẫn dùng extractor nội bộ nhưng backend vẫn build prompt và giữ đúng pipeline để dễ nâng cấp sau này.",
};

const defaultFormValues = {
  text: "",
  llmMode: "mock",
  technicalComplexityFactor: "1.0",
  environmentalComplexityFactor: "1.0",
  productivityFactor: "20",
  teamSize: "3",
};

function HomePage() {
  // Lưu toàn bộ giá trị nhập trên form.
  const [formValues, setFormValues] = useState(defaultFormValues);

  // Lưu file mà người dùng chọn tải lên.
  const [selectedFile, setSelectedFile] = useState(null);

  // Trạng thái kiểm tra backend đang hoạt động hay không.
  const [healthStatus, setHealthStatus] = useState("đang kiểm tra...");

  // loading dùng để khóa nút khi đang gọi API.
  const [loading, setLoading] = useState(false);

  // loadingAction cho biết hiện đang bấm nút nào: extract hay calculate.
  const [loadingAction, setLoadingAction] = useState("");

  // Thông báo thành công để hiển thị trên giao diện.
  const [successMessage, setSuccessMessage] = useState("");

  // Thông báo lỗi từ backend hoặc lỗi kết nối.
  const [errorMessage, setErrorMessage] = useState("");

  // Dữ liệu extract gồm actors và use cases.
  const [extraction, setExtraction] = useState(null);

  // Kết quả tính toán UCP, effort, schedule.
  const [result, setResult] = useState(null);

  // Dùng để biết dữ liệu extract hiện tại có còn khớp với input đang nhập hay không.
  const [extractionSignature, setExtractionSignature] = useState("");

  // Danh sách các lần tính toán đã được lưu trong MySQL.
  const [historyRuns, setHistoryRuns] = useState([]);

  // Run lịch sử đang được chọn để người dùng biết mình đang xem lại lần nào.
  const [selectedHistoryRunId, setSelectedHistoryRunId] = useState(null);

  // Loading riêng cho mục lịch sử, tách khỏi loading của nút Extract/Calculate.
  const [historyLoading, setHistoryLoading] = useState(false);

  // Lỗi riêng của mục lịch sử để không làm mất lỗi chính của form.
  const [historyError, setHistoryError] = useState("");

  useEffect(() => {
    // Hàm nhỏ để gọi API health khi trang vừa mở.
    async function loadHealth() {
      try {
        const data = await checkHealth();
        setHealthStatus(data.status === "ok" ? "đang hoạt động" : data.status);
      } catch (error) {
        setHealthStatus("mất kết nối");
        setErrorMessage(error.message);
      }
    }

    // Kiểm tra backend khi trang vừa mở.
    loadHealth();
    // Tải lịch sử từ MySQL khi trang vừa mở.
    loadHistory();
  }, []);

  // Tải danh sách lịch sử tính toán từ backend.
  async function loadHistory() {
    // Bật loading riêng của lịch sử.
    setHistoryLoading(true);
    // Xóa lỗi lịch sử cũ trước khi gọi API mới.
    setHistoryError("");

    try {
      // Gọi GET /analysis-runs.
      const data = await listAnalysisRuns();

      // Mục lịch sử này chỉ hiển thị run đã có kết quả UCP.
      const calculatedRuns = (data.runs ?? []).filter(
        (run) => run.ucp !== null && run.ucp !== undefined
      );
      // Lưu danh sách đã lọc vào state để HistoryPanel render.
      setHistoryRuns(calculatedRuns);
    } catch (error) {
      // Nếu MySQL/backend lỗi thì hiển thị lỗi trong panel lịch sử.
      setHistoryError(error.message);
    } finally {
      // Tắt loading dù thành công hay thất bại.
      setHistoryLoading(false);
    }
  }

  // Khi bấm "Xem Lại", frontend lấy chi tiết run và đổ lên bảng/card hiện tại.
  async function handleSelectHistoryRun(runId) {
    // Bật loading khi đang lấy chi tiết run.
    setHistoryLoading(true);
    // Xóa lỗi lịch sử cũ.
    setHistoryError("");
    // Xóa message form cũ để tránh gây hiểu nhầm.
    clearMessages();

    try {
      // Gọi GET /analysis-runs/{run_id}.
      const savedRun = await getAnalysisRun(runId);
      // Chuyển data DB về đúng format component hiện tại đang dùng.
      const mappedData = mapSavedRunToCurrentResult(savedRun);

      // Đổ lại actors/use_cases lên bảng hiện tại.
      setExtraction(mappedData.extraction);
      // Đổ lại UCP/Effort/Schedule lên result cards.
      setResult(mappedData.result);
      // Lưu run đang chọn để tô sáng dòng trong lịch sử.
      setSelectedHistoryRunId(runId);
      // Báo cho người dùng biết đã tải lại dữ liệu từ lịch sử.
      setSuccessMessage(`Đã tải lại kết quả từ lịch sử run #${runId}.`);
    } catch (error) {
      // Nếu lỗi thì chỉ hiện lỗi ở panel lịch sử.
      setHistoryError(error.message);
    } finally {
      // Tắt loading.
      setHistoryLoading(false);
    }
  }

  // Xóa một run khỏi lịch sử nếu người dùng thấy danh sách quá nhiều.
  async function handleDeleteHistoryRun(runId) {
    // Hỏi xác nhận để tránh người dùng bấm nhầm xóa lịch sử.
    const confirmed = window.confirm(
      `Bạn có chắc muốn xóa lịch sử run #${runId}? Dữ liệu actor, use case, calculation và log liên quan cũng sẽ bị xóa.`
    );

    // Nếu người dùng bấm Cancel thì dừng lại, không gọi API.
    if (!confirmed) {
      return;
    }

    // Bật loading khi đang xóa.
    setHistoryLoading(true);
    // Xóa lỗi lịch sử cũ.
    setHistoryError("");
    // Xóa message form cũ.
    clearMessages();

    try {
      // Gọi DELETE /analysis-runs/{run_id}.
      await deleteAnalysisRun(runId);

      // Nếu run đang xem bị xóa thì bỏ trạng thái selected.
      if (selectedHistoryRunId === runId) {
        setSelectedHistoryRunId(null);
      }

      // Báo xóa thành công.
      setSuccessMessage(`Đã xóa lịch sử run #${runId}.`);
      // Tải lại danh sách lịch sử sau khi xóa.
      await loadHistory();
    } catch (error) {
      // Nếu xóa lỗi thì hiển thị trong panel lịch sử.
      setHistoryError(error.message);
    } finally {
      // Tắt loading.
      setHistoryLoading(false);
    }
  }

  // Cập nhật state mới khi người dùng thay đổi text hoặc các thông số.
  function handleInputChange(event) {
    const { name, value } = event.target;

    // Khi người dùng đổi dữ liệu đầu vào hoặc đổi mode,
    // mình chỉ cập nhật state form chứ chưa gọi API ngay.
    setFormValues((currentValues) => ({
      ...currentValues,
      [name]: value,
    }));
  }

  // Xóa thông báo cũ trước khi thực hiện hành động mới.
  function clearMessages() {
    setSuccessMessage("");
    setErrorMessage("");
  }

  // Gọi API /extract để lấy actors và use cases từ free-text input.
  async function handleExtract() {
    setLoading(true);
    setLoadingAction("extract");
    clearMessages();

    try {
      const data = await extractData(formValues.text, {
        llmMode: formValues.llmMode,
        file: selectedFile,
      });

      // Lưu dữ liệu extraction để hiển thị ở bảng Actor, Use Case và biểu đồ.
      setExtraction(data);

      // Khi extraction thay đổi thì kết quả tính cũ có thể không còn đúng nữa.
      setResult(null);

      // Lưu "dấu vân tay" của dữ liệu hiện tại để biết
      // extraction này có còn khớp với input đang hiển thị trên form hay không.
      setExtractionSignature(
        buildInputSignature(formValues.text, formValues.llmMode, selectedFile)
      );
      setSuccessMessage("Trích xuất dữ liệu thành công.");
      // Refresh lịch sử vì /extract cũng có lưu run extract_only, dù panel chỉ hiển thị run có calculation.
      loadHistory();
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setLoading(false);
      setLoadingAction("");
    }
  }

  // Gọi API tính UCP.
  async function handleCalculate() {
    setLoading(true);
    setLoadingAction("calculate");
    clearMessages();

    // Tạo dấu vân tay từ dữ liệu hiện tại trên form.
    const currentSignature = buildInputSignature(
      formValues.text,
      formValues.llmMode,
      selectedFile
    );

    try {
      // Nếu extraction hiện tại vẫn đúng với text/file đang nhập,
      // frontend chỉ cần gọi API tính UCP, không cần extract lại lần nữa.
      if (
        extraction?.actors?.length &&
        extraction?.use_cases?.length &&
        extractionSignature === currentSignature
      ) {
        const calculationData = await calculateUCP(
          buildUcpPayload(extraction, formValues)
        );

        setResult(calculationData);
        setSuccessMessage("Tính toán UCP thành công.");
        // Refresh lịch sử để run calculate_only vừa lưu xuất hiện ngay.
        loadHistory();
        return;
      }

      // Nếu người dùng đã sửa text, đổi mode hoặc đổi file,
      // extraction cũ không còn đáng tin nữa.
      // Lúc này frontend gọi API gộp để backend:
      // 1. extract lại dữ liệu mới
      // 2. normalize
      // 3. tính UCP từ dữ liệu mới nhất
      const data = await analyzeAndCalculate(formValues.text, {
        llmMode: formValues.llmMode,
        file: selectedFile,
        technicalComplexityFactor: formValues.technicalComplexityFactor,
        environmentalComplexityFactor: formValues.environmentalComplexityFactor,
        productivityFactor: formValues.productivityFactor,
        teamSize: formValues.teamSize,
      });

      setExtraction(data.extraction);
      setResult({
        ucp: data.ucp,
        effort: data.effort,
        schedule: data.schedule,
      });
      setExtractionSignature(currentSignature);
      setSuccessMessage("Trích xuất và tính toán UCP thành công.");
      // Refresh lịch sử để run analyze_and_calculate vừa lưu xuất hiện ngay.
      loadHistory();
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setLoading(false);
      setLoadingAction("");
    }
  }

  return (
    <div className="page-shell">
      <header className="hero">
        <div className="hero-copy-block">
          <p className="eyebrow">Group 6</p>
          <h1>AI Tool for Automatic Use Case Point Estimation</h1>
        </div>
      </header>

      <main className="layout-grid">
        <section className="panel panel-wide">
          <div className="stack-lg">
            <div>
              <h2 className="section-title">Dữ Liệu Đầu Vào</h2>
              <p className="section-copy">
                Nhập nội dung <strong>Use Case Document</strong> theo template hoặc tải trực tiếp file
                `.doc`, `.docx`, `.txt` để backend tự đọc.
              </p>
              <p className="section-copy">
                Nếu bạn upload file theo mẫu Use Case Document, bạn có thể để trống ô nhập text bên dưới.
              </p>
              <p className="section-copy">
                Trạng thái backend: <strong>{healthStatus}</strong>
              </p>
            </div>

            <label className="field">
              <span>Use Case Document Content (Optional)</span>
              <textarea
                name="text"
                rows="8"
                value={formValues.text}
                onChange={handleInputChange}
                placeholder={"Ví dụ:\nUse Case 1: Register Account\nUse Case ID\nUC-01\nUse Case Name\nRegister Account\nPrimary Actor\nGuest\nDescription\nA guest creates a new account.\nMain Flow\nGuest opens the registration page.\nGuest enters personal information.\nGuest submits the registration form."}
              />
              <small className="field-hint">
                Dùng ô này khi bạn muốn dán trực tiếp nội dung template. Nếu đã upload file Use Case Document thì có thể bỏ trống.
              </small>
            </label>

            <label className="field">
              <span>Use Case Document File</span>
              <input
                type="file"
                accept=".txt,.md,.doc,.docx"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
              <small className="field-hint">
                Hệ thống ưu tiên đọc file `.docx` theo template Use Case Document.
                File `.doc` cũ cũng được hỗ trợ theo cơ chế best-effort để lấy text.
              </small>
              {selectedFile ? (
                <small className="field-hint">Đã chọn file: {selectedFile.name}</small>
              ) : null}
            </label>

            <p className="section-copy">
              Gợi ý demo: upload file Use Case Document theo template, bấm <strong>Trích Xuất</strong> để xem Actor và Use Case,
              sau đó bấm <strong>Tính Toán</strong> để lấy UCP, Effort và Schedule.
            </p>

            <div className="settings-grid">
            <label className="field">
              <span>LLM Mode</span>
              <select
                name="llmMode"
                value={formValues.llmMode}
                onChange={handleInputChange}
              >
                <option value="mock">Mock Mode</option>
                <option value="placeholder">Placeholder API Mode</option>
              </select>
              <small className="field-hint">
                {llmModeDescriptions[formValues.llmMode]}
              </small>
            </label>

              <label className="field">
                <span>TCF</span>
                <input
                  name="technicalComplexityFactor"
                  type="number"
                  step="0.1"
                  value={formValues.technicalComplexityFactor}
                  onChange={handleInputChange}
                />
              </label>

              <label className="field">
                <span>ECF</span>
                <input
                  name="environmentalComplexityFactor"
                  type="number"
                  step="0.1"
                  value={formValues.environmentalComplexityFactor}
                  onChange={handleInputChange}
                />
              </label>

              <label className="field">
                <span>Productivity Factor</span>
                <input
                  name="productivityFactor"
                  type="number"
                  step="1"
                  value={formValues.productivityFactor}
                  onChange={handleInputChange}
                />
              </label>

              <label className="field">
                <span>Team Size</span>
                <input
                  name="teamSize"
                  type="number"
                  min="1"
                  step="1"
                  value={formValues.teamSize}
                  onChange={handleInputChange}
                />
              </label>
            </div>

            <div className="button-row">
              <button
                type="button"
                className="secondary-button"
                onClick={handleExtract}
                disabled={loading}
              >
                {loadingAction === "extract" ? "Đang trích xuất..." : "Trích Xuất"}
              </button>

              <button
                type="button"
                className="primary-button"
                onClick={handleCalculate}
                disabled={loading}
              >
                {loadingAction === "calculate" ? "Đang tính toán..." : "Tính Toán"}
              </button>
            </div>

            {successMessage ? <p className="section-copy">{successMessage}</p> : null}
            {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
          </div>
        </section>

        <section className="panel">
          <ActorsTable actors={extraction?.actors ?? []} />
        </section>

        <section className="panel">
          <UseCasesTable useCases={extraction?.use_cases ?? []} />
        </section>

        <section className="panel">
          <ResultCards result={result} />
        </section>

        <section className="panel panel-wide">
          <ChartPanel extraction={extraction} />
        </section>

        <section className="panel panel-wide">
          {/* HistoryPanel nhận state và handler từ HomePage để hiển thị/xem/xóa lịch sử MySQL. */}
          <HistoryPanel
            runs={historyRuns}
            loading={historyLoading}
            error={historyError}
            selectedRunId={selectedHistoryRunId}
            onRefresh={loadHistory}
            onSelectRun={handleSelectHistoryRun}
            onDeleteRun={handleDeleteHistoryRun}
          />
        </section>
      </main>
    </div>
  );
}

// Chuyển dữ liệu chi tiết từ endpoint /analysis-runs/{run_id}
// về đúng format mà ActorsTable, UseCasesTable và ResultCards đang dùng.
function mapSavedRunToCurrentResult(savedRun) {
  // calculation là object lấy từ bảng calculations.
  const calculation = savedRun.calculation ?? {};
  // run là object lấy từ bảng analysis_runs.
  const run = savedRun.run ?? {};
  // actors là danh sách lấy từ bảng extracted_actors.
  const actors = savedRun.actors ?? [];
  // useCases là danh sách lấy từ bảng extracted_use_cases.
  const useCases = savedRun.use_cases ?? [];

  // Trả về format giống response của /analyze-and-calculate để component cũ dùng lại được.
  return {
    // extraction dùng cho ActorsTable, UseCasesTable và ChartPanel.
    extraction: {
      // Map actor_name trong DB về name trên frontend.
      actors: actors.map((actor) => ({
        name: actor.actor_name,
        complexity: actor.complexity,
      })),
      // Map use_case_name trong DB về name trên frontend.
      use_cases: useCases.map((useCase) => ({
        name: useCase.use_case_name,
        complexity: useCase.complexity,
        description: useCase.description,
      })),
      // Ghi chú để biết dữ liệu đang xem là dữ liệu lịch sử.
      notes: ["Dữ liệu được tải lại từ lịch sử MySQL."],
    },
    // result dùng cho ResultCards.
    result: {
      // Nhóm chỉ số UCP.
      ucp: {
        uaw: calculation.uaw,
        uucw: calculation.uucw,
        uucp: calculation.uucp,
        ucp: calculation.ucp,
        actor_count: actors.length,
        use_case_count: useCases.length,
        technical_complexity_factor: run.technical_complexity_factor,
        environmental_complexity_factor: run.environmental_complexity_factor,
      },
      // Nhóm effort.
      effort: {
        hours: calculation.effort_hours,
        person_days: calculation.person_days,
        productivity_factor: calculation.productivity_factor,
      },
      // Nhóm schedule.
      schedule: {
        months: calculation.schedule_months,
        recommended_team_size: calculation.recommended_team_size,
        sprint_count: calculation.sprint_count,
      },
    },
  };
}

export default HomePage;
