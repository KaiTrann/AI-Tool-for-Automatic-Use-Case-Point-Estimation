// Bảng hiển thị danh sách use case được backend trích xuất từ free-text input.
function UseCasesTable({ useCases }) {
  return (
    <div className="stack-md">
      <div>
        <h2 className="section-title">Danh Sách Use Case</h2>
        <p className="section-copy">
          Bảng này hiển thị các Use Case mà backend đã lấy ra từ Use Case Document template.
        </p>
      </div>

      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>Use Case</th>
              <th>Complexity</th>
            </tr>
          </thead>
          <tbody>
            {useCases.length > 0 ? (
              useCases.map((useCase) => (
                <tr key={useCase.name}>
                  <td>{useCase.name}</td>
                  <td>{translateComplexity(useCase.complexity)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="2">Chưa có Use Case. Hãy bấm Trích Xuất để lấy dữ liệu.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function translateComplexity(value) {
  if (value === "simple") return "Simple";
  if (value === "average") return "Average";
  if (value === "complex") return "Complex";
  return value;
}

export default UseCasesTable;
