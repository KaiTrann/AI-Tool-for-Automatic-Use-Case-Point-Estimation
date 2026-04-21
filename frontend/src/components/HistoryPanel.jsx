// Panel lịch sử dùng để xem lại các lần tính UCP đã được lưu trong MySQL.
// Component này chỉ hiển thị dữ liệu và phát sự kiện khi người dùng bấm "Xem lại".
function HistoryPanel({
  // runs là danh sách lịch sử lấy từ GET /analysis-runs.
  runs,
  // loading cho biết panel đang tải danh sách, xem chi tiết hoặc xóa.
  loading,
  // error là lỗi riêng của panel lịch sử.
  error,
  // selectedRunId dùng để tô sáng dòng đang xem lại.
  selectedRunId,
  // onRefresh là hàm tải lại lịch sử.
  onRefresh,
  // onSelectRun là hàm xem lại một run.
  onSelectRun,
  // onDeleteRun là hàm xóa một run.
  onDeleteRun,
}) {
  // Component chỉ render UI; logic gọi API nằm ở HomePage để dễ quản lý state chung.
  return (
    // stack-md tạo khoảng cách giữa header, error và bảng.
    <div className="stack-md">
      {/* Header của panel lịch sử gồm tiêu đề và nút tải lại. */}
      <div className="history-header">
        <div>
          <h2 className="section-title">Lịch Sử Tính Toán</h2>
          <p className="section-copy">
            Mục này lấy dữ liệu từ MySQL để xem lại các lần đã extract và tính UCP trước đó.
          </p>
        </div>

        {/* Nút này tải lại danh sách lịch sử; disabled khi đang loading để tránh gọi API nhiều lần. */}
        <button
          type="button"
          className="secondary-button compact-button"
          onClick={onRefresh}
          disabled={loading}
        >
          {/* Đổi text theo trạng thái loading. */}
          {loading ? "Đang tải..." : "Tải Lại"}
        </button>
      </div>

      {/* Nếu có lỗi lịch sử thì hiển thị riêng ở đây, không đè lỗi form chính. */}
      {error ? <p className="error-text">{error}</p> : null}

      {/* Bọc table bằng div để có thể scroll ngang khi màn hình nhỏ. */}
      <div className="table-card history-table-card">
        <table>
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Tài liệu</th>
              <th>UCP</th>
              <th>Effort</th>
              <th>Schedule</th>
              <th>Trạng thái</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {/* Nếu có run thì render từng dòng, nếu không thì render empty state. */}
            {runs.length > 0 ? (
              // map từng run từ MySQL thành một dòng trong bảng lịch sử.
              runs.map((run) => (
                // selected-row giúp tô sáng run đang xem lại.
                <tr key={run.id} className={selectedRunId === run.id ? "selected-row" : ""}>
                  {/* ID chính là analysis_runs.id trong MySQL. */}
                  <td>{run.id}</td>
                  <td>
                    {/* Tên tài liệu lấy từ documents.title. */}
                    <strong>{run.document_title ?? "Không có tiêu đề"}</strong>
                    {/* Thời điểm chạy lấy từ analysis_runs.started_at. */}
                    <span className="history-meta">
                      {formatDateTime(run.started_at)}
                    </span>
                  </td>
                  {/* UCP lấy từ bảng calculations. */}
                  <td>{run.ucp ?? "-"}</td>
                  {/* Effort theo giờ lấy từ calculations.effort_hours. */}
                  <td>{run.effort_hours ? `${run.effort_hours} giờ` : "-"}</td>
                  {/* Schedule theo tháng lấy từ calculations.schedule_months. */}
                  <td>{run.schedule_months ? `${run.schedule_months} tháng` : "-"}</td>
                  {/* Status lấy từ analysis_runs.status và dịch sang tiếng Việt. */}
                  <td>{translateStatus(run.status)}</td>
                  <td>
                    {/* Nhóm 2 nút thao tác trong cùng một ô. */}
                    <div className="history-action-row">
                      {/* Nút Xem Lại sẽ load chi tiết run lên bảng Actor/Use Case/ResultCards. */}
                      <button
                        type="button"
                        className="primary-button compact-button"
                        onClick={() => onSelectRun(run.id)}
                        disabled={loading}
                      >
                        Xem Lại
                      </button>
                      {/* Nút Xóa gọi DELETE /analysis-runs/{run_id}. */}
                      <button
                        type="button"
                        className="danger-button compact-button"
                        onClick={() => onDeleteRun(run.id)}
                        disabled={loading}
                      >
                        Xóa
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              // Empty state khi chưa có calculation nào trong DB.
              <tr>
                <td colSpan="7">
                  Chưa có lịch sử tính toán. Hãy bấm Tính Toán để backend lưu kết quả vào MySQL.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Format ngày giờ cho dễ nhìn khi demo trên giao diện.
function formatDateTime(value) {
  // Nếu backend không trả thời gian thì hiển thị rỗng.
  if (!value) {
    return "";
  }

  // Chuyển ISO string từ backend thành Date của JavaScript.
  const date = new Date(value);
  // Nếu parse lỗi thì trả lại chuỗi gốc để không mất dữ liệu.
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  // Format theo locale Việt Nam cho dễ đọc khi demo.
  return date.toLocaleString("vi-VN");
}

// Dịch trạng thái database sang chữ dễ hiểu hơn cho người dùng.
function translateStatus(value) {
  // Run thành công.
  if (value === "success") return "Thành công";
  // Run thất bại.
  if (value === "failed") return "Thất bại";
  // Run đang chạy hoặc chưa mark success/failed.
  if (value === "running") return "Đang chạy";
  // Nếu có status lạ thì giữ nguyên để debug.
  return value ?? "-";
}

export default HistoryPanel;
