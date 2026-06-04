const CATEGORIES = ["Ăn uống", "Di chuyển", "Mua sắm", "Giải trí", "Sức khỏe", "Giáo dục", "Hóa đơn", "Khác"];

async function readApiResponse(response, endpoint) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    const detail = (await response.text()).slice(0, 120);
    throw new Error(
      `${endpoint} không trả JSON. Hãy dừng và chạy lại python codebase/server.py.${detail ? ` Phản hồi: ${detail}` : ""}`
    );
  }
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `${endpoint} request failed`);
  return payload;
}

class OpenRouterSpendingAgent {
  constructor() {
    this.lastRun = { provider: "OpenRouter", model: "", insights: [] };
  }

  async classify(transactions, onProgress) {
    let progress = 8;
    const timer = setInterval(() => {
      progress = Math.min(progress + 7, 88);
      onProgress?.({
        current: progress,
        total: 100,
        merchant: "OpenRouter đang phân tích dữ liệu"
      });
    }, 180);

    try {
      const response = await fetch("/api/classify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transactions })
      });
      const payload = await readApiResponse(response, "/api/classify");
      this.lastRun = payload;
      return payload.classifications;
    } finally {
      clearInterval(timer);
      onProgress?.({ current: 100, total: 100, merchant: "Hoàn tất phân tích" });
    }
  }

  async chat(message, transactions, classifications, history) {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, transactions, classifications, history })
    });
    return readApiResponse(response, "/api/chat");
  }

  summarize(transactions, classifications) {
    const totals = {};
    classifications.forEach(result => {
      const tx = transactions.find(item => item.id === result.id);
      totals[result.category] = (totals[result.category] || 0) + tx.amount;
    });
    const sorted = Object.entries(totals).sort((a, b) => b[1] - a[1]);
    const totalSpent = transactions.reduce((sum, item) => sum + item.amount, 0);
    const needsReviewCount = classifications.filter(item => item.needsReview).length;
    const avgConfidence = classifications.reduce((sum, item) => sum + item.confidence, 0) / classifications.length;
    const [topCategory, topAmount] = sorted[0];
    const percent = Math.round(topAmount / totalSpent * 100);
    const defaultInsight = `${topCategory} đang là nhóm chi cao nhất, chiếm khoảng ${percent}% tổng chi. ${needsReviewCount ? `Có ${needsReviewCount} giao dịch cần bạn xác nhận.` : "Tất cả giao dịch đã được xác nhận."}`;
    return {
      totalSpent,
      totals: sorted,
      topCategory,
      topAmount,
      avgConfidence,
      needsReviewCount,
      insight: this.lastRun.insights?.length ? this.lastRun.insights.join(" ") : defaultInsight
    };
  }
}
