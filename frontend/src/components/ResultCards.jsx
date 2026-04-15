// Các thẻ kết quả giúp trình bày nhanh các giá trị chính của UCP.
function ResultCards({ result }) {
  const ucp = result?.ucp;
  const effort = result?.effort;
  const schedule = result?.schedule;

  const cards = [
    {
      label: "UAW",
      value: ucp?.uaw ?? "-",
      helper: "Tổng trọng số Actor",
    },
    {
      label: "UUCW",
      value: ucp?.uucw ?? "-",
      helper: "Tổng trọng số Use Case",
    },
    {
      label: "UCP",
      value: ucp?.ucp ?? "-",
      helper: "Use Case Point đã hiệu chỉnh",
    },
    {
      label: "Effort",
      value: effort ? `${effort.hours} giờ` : "-",
      helper: "Ước lượng Effort",
    },
    {
      label: "Schedule",
      value: schedule ? `${schedule.months} tháng` : "-",
      helper: "Ước lượng Schedule",
    },
  ];

  return (
    <div className="stack-md">
      <div>
        <h2 className="section-title">Kết Quả Tính Toán</h2>
        <p className="section-copy">
          Thẻ này tóm tắt nhanh kết quả UCP calculation từ dữ liệu đã trích xuất.
        </p>
      </div>

      <div className="cards-grid">
        {cards.map((card) => (
          <article className="result-card" key={card.label}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <p>{card.helper}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

export default ResultCards;
