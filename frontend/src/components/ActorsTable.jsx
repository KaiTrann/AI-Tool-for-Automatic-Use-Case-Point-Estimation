// Bảng hiển thị danh sách actor được backend trích xuất từ free-text input.
function ActorsTable({ actors }) {
  return (
    <div className="stack-md">
      <div>
        <h2 className="section-title">Danh Sách Actor</h2>
        <p className="section-copy">
          Bảng này hiển thị các Actor mà backend đã trích xuất từ Requirements Text hoặc Use Case Description.
        </p>
      </div>

      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>Actor</th>
              <th>Complexity</th>
            </tr>
          </thead>
          <tbody>
            {actors.length > 0 ? (
              actors.map((actor) => (
                <tr key={actor.name}>
                  <td>{actor.name}</td>
                  <td>{translateComplexity(actor.complexity)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="2">Chưa có Actor. Hãy bấm Trích Xuất để lấy dữ liệu.</td>
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

export default ActorsTable;
