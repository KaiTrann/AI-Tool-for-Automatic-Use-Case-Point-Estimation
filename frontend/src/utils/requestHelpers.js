// Các hàm phụ trợ nhỏ cho HomePage.
// Tách riêng để component chính ngắn gọn và dễ giải thích hơn.

// Tạo payload đúng định dạng cho API POST /ucp/calculate.
export function buildUcpPayload(extraction, formValues) {
  return {
    // Lấy dữ liệu đã extract từ backend.
    actors: extraction?.actors ?? [],
    use_cases: extraction?.use_cases ?? [],

    // Đổi dữ liệu từ input string sang number trước khi gửi cho backend.
    technical_complexity_factor: Number(formValues.technicalComplexityFactor),
    environmental_complexity_factor: Number(formValues.environmentalComplexityFactor),
    productivity_factor: Number(formValues.productivityFactor),
    team_size: Number(formValues.teamSize),
  };
}

// Tạo "dấu vân tay" đơn giản cho input hiện tại.
// Nếu text hoặc file thay đổi thì biết dữ liệu extract cũ không còn phù hợp.
export function buildInputSignature(text, llmMode, file) {
  const fileSignature =
    file && typeof file === "object"
      // Ghép các thuộc tính đủ để nhận ra người dùng đã đổi file hay chưa.
      ? `${file.name}-${file.size}-${file.lastModified}`
      : "";

  return JSON.stringify({
    text: text ?? "",
    llmMode: llmMode ?? "mock",
    fileSignature,
  });
}
