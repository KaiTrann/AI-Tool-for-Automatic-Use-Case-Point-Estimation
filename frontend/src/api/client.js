// Gom toàn bộ lệnh gọi API vào một file để phần giao diện dễ đọc hơn.
// Dùng `fetch` trực tiếp để phù hợp với prototype học thuật đơn giản.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Lớp lỗi nhỏ để giao diện hiển thị lỗi backend rõ ràng hơn.
export class ApiError extends Error {
  constructor(message, status = 500, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

// Hàm gọi API dùng chung cho toàn bộ project.
// Nhiệm vụ:
// - gửi request
// - đọc dữ liệu trả về
// - chuẩn hóa lỗi từ FastAPI
async function apiRequest(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch (networkError) {
    throw new ApiError(
      "Không thể kết nối tới backend. Hãy kiểm tra FastAPI đã chạy tại http://localhost:8000 chưa.",
      0,
      networkError
    );
  }

  const data = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiError(formatErrorMessage(data), response.status, data);
  }

  return data;
}

// Đọc dữ liệu trả về từ backend.
// Nếu backend trả JSON thì parse JSON, nếu không thì đọc text thường.
async function parseResponseBody(response) {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return text ? { detail: text } : {};
}

// Chuyển lỗi validation của FastAPI thành chuỗi dễ hiển thị.
function formatErrorMessage(errorPayload) {
  if (!errorPayload) {
    return "Backend trả về lỗi không xác định.";
  }

  const { detail } = errorPayload;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const fieldPath = Array.isArray(item.loc) ? item.loc.join(" -> ") : "trường dữ liệu";
        return `${fieldPath}: ${item.msg}`;
      })
      .join(" | ");
  }

  if (typeof detail === "object") {
    return JSON.stringify(detail);
  }

  return "Backend trả về định dạng lỗi không mong đợi.";
}

// Tạo FormData cho các API nhận Requirements Text và file upload.
function buildAnalysisFormData(text, options = {}) {
  const formData = new FormData();

  // Backend nhận dữ liệu text qua field tên "text".
  formData.append("text", text ?? "");

  // llm_mode cho backend biết sẽ chạy nhánh extractor nào.
  formData.append("llm_mode", options.llmMode ?? "mock");

  // Các tham số bên dưới chỉ cần gửi khi có giá trị.
  // Điều này giúp cùng một helper dùng được cho cả /extract và /analyze-and-calculate.
  if (options.technicalComplexityFactor !== undefined) {
    formData.append("technical_complexity_factor", String(options.technicalComplexityFactor));
  }

  if (options.environmentalComplexityFactor !== undefined) {
    formData.append("environmental_complexity_factor", String(options.environmentalComplexityFactor));
  }

  if (options.productivityFactor !== undefined) {
    formData.append("productivity_factor", String(options.productivityFactor));
  }

  if (options.teamSize !== undefined) {
    formData.append("team_size", String(options.teamSize));
  }

  if (options.file) {
    // uploaded_file là tên field mà FastAPI route đang chờ.
    formData.append("uploaded_file", options.file);
  }

  return formData;
}

// Kiểm tra backend có đang chạy hay không.
export async function checkHealth() {
  return apiRequest("/health", {
    method: "GET",
  });
}

// Gửi Requirements Text / Use Case Description đến API trích xuất.
export async function extractData(text, options = {}) {
  return apiRequest("/extract", {
    method: "POST",
    body: buildAnalysisFormData(text, options),
  });
}

// Gửi dữ liệu đã trích xuất sang API tính UCP.
export async function calculateUCP(payload) {
  return apiRequest("/ucp/calculate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

// Gọi API gộp: vừa trích xuất vừa tính toán trong một request.
export async function analyzeAndCalculate(text, options = {}) {
  return apiRequest("/analyze-and-calculate", {
    method: "POST",
    body: buildAnalysisFormData(text, options),
  });
}

// Lấy danh sách các lần tính toán đã lưu trong MySQL.
// API backend trả về dạng: { runs: [...] }.
export async function listAnalysisRuns() {
  // Gọi endpoint backend lấy danh sách run đã lưu.
  return apiRequest("/analysis-runs", {
    // GET vì chỉ đọc dữ liệu, không thay đổi database.
    method: "GET",
  });
}

// Lấy chi tiết một lần chạy để frontend có thể hiển thị lại actor, use case và kết quả UCP.
export async function getAnalysisRun(runId) {
  // runId là id của analysis_runs trong MySQL.
  return apiRequest(`/analysis-runs/${runId}`, {
    // GET chi tiết một run.
    method: "GET",
  });
}

// Xóa một lần tính toán khỏi lịch sử MySQL.
// Backend sẽ xóa cascade các actor/use case/calculation/log liên quan.
export async function deleteAnalysisRun(runId) {
  // runId là id cần xóa khỏi bảng analysis_runs.
  return apiRequest(`/analysis-runs/${runId}`, {
    // DELETE để backend xóa run và các bảng con liên quan.
    method: "DELETE",
  });
}
