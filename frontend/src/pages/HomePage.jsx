// Trang chính của hệ thống.
// File này chứa gần như toàn bộ luồng chạy ở frontend:
// 1. Nhận Requirements Text / Use Case Description từ người dùng
// 2. Gọi API backend để trích xuất actor và use case
// 3. Nhận kết quả trả về
// 4. Hiển thị bảng và kết quả tính toán UCP

import { useEffect, useState } from "react";

import {
  analyzeAndCalculate,
  calculateUCP,
  checkHealth,
  extractData,
} from "../api/client";
import ActorsTable from "../components/ActorsTable";
import ChartPanel from "../components/ChartPanel";
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

    loadHealth();
  }, []);

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
                Nhập Requirements Text hoặc Use Case Description ở dạng plain text.
                Bạn cũng có thể tải lên file text để backend đọc như nguồn dữ liệu bổ sung.
              </p>
              <p className="section-copy">
                Trạng thái backend: <strong>{healthStatus}</strong>
              </p>
            </div>

            <label className="field">
              <span>Requirements Text / Use Case Description</span>
              <textarea
                name="text"
                rows="8"
                value={formValues.text}
                onChange={handleInputChange}
                placeholder="Ví dụ: The Customer can register, log in, browse products, place an order, and make payment. The Administrator can manage products and generate reports."
              />
            </label>

            <label className="field">
              <span>Plain Text Input File</span>
              <input
                type="file"
                accept=".txt,.md,.doc,.docx,.pdf"
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
              <small className="field-hint">
                Không bắt buộc tải file. Phiên bản hiện tại đọc file như nguồn text đầu vào.
                Phù hợp nhất với `.txt`, `.md`, hoặc mock uploaded content có tên `.docx`.
              </small>
              {selectedFile ? (
                <small className="field-hint">Đã chọn file: {selectedFile.name}</small>
              ) : null}
            </label>

            <p className="section-copy">
              Gợi ý demo: dán một đoạn requirements paragraph ngắn, bấm <strong>Trích Xuất</strong> để xem Actor và Use Case,
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
      </main>
    </div>
  );
}

export default HomePage;
