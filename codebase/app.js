const money = value => new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(value);
const categoryIcons = { "Ăn uống": "☕", "Di chuyển": "↗", "Mua sắm": "▣", "Giải trí": "▶", "Sức khỏe": "+", "Giáo dục": "▤", "Hóa đơn": "▧", "Khác": "?" };
let transactions = [];
let results = [];
let agent;
let reviewOnly = false;
let highlightedIds = new Set();
let chatHistory = [];

const $ = selector => document.querySelector(selector);
const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#039;"
})[character]);

async function loadData() {
  const txResponse = await fetch("data/transactions.json");
  transactions = await txResponse.json();
  agent = new OpenRouterSpendingAgent();
  checkProvider();
  renderTransactions();
}

async function checkProvider() {
  try {
    const response = await fetch("/api/health");
    const health = await response.json();
    $("#agentStatus").textContent = health.openrouterConfigured
      ? `Sẵn sàng: OpenRouter · ${health.model}`
      : "Chưa có API key OpenRouter";
  } catch {
    $("#agentStatus").textContent = "Không kết nối được AI server";
  }
}

function renderTransactions() {
  const list = reviewOnly ? transactions.filter(tx => results.find(item => item.id === tx.id)?.needsReview) : transactions;
  $("#transactions").innerHTML = list.map(tx => {
    const result = results.find(item => item.id === tx.id);
    const time = new Date(tx.time).toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
    return `<article class="transaction ${result?.needsReview ? "needs-review" : ""} ${highlightedIds.has(tx.id) ? "chat-match" : ""}">
      <div class="merchant-icon">${categoryIcons[result?.category] || "₫"}</div>
      <div class="transaction-copy">
        <strong>${tx.merchant}</strong><small>${tx.note} · ${time}</small>
        ${result ? `<div class="classification"><span>${result.category}</span><span>${Math.round(result.confidence * 100)}%</span>${result.needsReview ? "<b>Cần xác nhận</b>" : ""}</div><p>${result.reason}</p>` : ""}
      </div>
      <div class="amount">-${money(tx.amount)}</div>
      ${result ? `<select aria-label="Sửa category" data-id="${tx.id}">${CATEGORIES.map(category => `<option ${category === result.category ? "selected" : ""}>${category}</option>`).join("")}</select>` : ""}
    </article>`;
  }).join("");
  document.querySelectorAll("select").forEach(select => select.addEventListener("change", correctCategory));
}

async function runAgent() {
  $("#classifyButton").disabled = true;
  $("#classifyButton").textContent = "AI đang phân tích...";
  $("#agentPanel").classList.remove("hidden");
  try {
    results = await agent.classify(transactions, ({ current, total, merchant }) => {
      const percent = Math.round(current / total * 100);
      $("#agentStatus").textContent = `Đang đọc ${merchant}`;
      $("#agentPercent").textContent = `${percent}%`;
      $("#progressBar").style.width = `${percent}%`;
    });
    const run = agent.lastRun;
    $("#agentStatus").textContent = `${run.provider} · ${run.model}`;
    $("#classifyButton").textContent = "✓ AI đã phân loại";
    renderDashboard();
    renderTransactions();
    $("#chatSection").classList.remove("hidden");
  } catch (error) {
    results = [];
    $("#chatSection").classList.add("hidden");
    $("#agentStatus").textContent = `Lỗi OpenRouter: ${error.message}`;
    $("#agentPercent").textContent = "0%";
    $("#progressBar").style.width = "0";
    $("#classifyButton").disabled = false;
    $("#classifyButton").textContent = "Thử phân loại lại";
    showToast("Không thể phân loại: cần kết nối OpenRouter API.");
  }
}

function renderDashboard() {
  const summary = agent.summarize(transactions, results);
  $("#dashboard").classList.remove("hidden");
  $("#totalSpent").textContent = money(summary.totalSpent);
  $("#topCategory").textContent = summary.topCategory;
  $("#topAmount").textContent = money(summary.topAmount);
  $("#avgConfidence").textContent = `${Math.round(summary.avgConfidence * 100)}%`;
  $("#reviewCount").textContent = `${summary.needsReviewCount} cần xác nhận`;
  $("#insightText").textContent = summary.insight;
  $("#categoryChips").innerHTML = summary.totals.map(([category, amount]) => `<span>${category}<strong>${money(amount)}</strong></span>`).join("");
}

function correctCategory(event) {
  applyCategoryCorrection(event.target.dataset.id, event.target.value, "Đã được người dùng xác nhận");
}

function applyCategoryCorrection(transactionId, newCategory, reason) {
  const result = results.find(item => item.id === transactionId);
  if (!result) {
    showToast("Hãy phân loại bằng AI trước khi chỉnh danh mục.");
    return false;
  }
  const oldCategory = result.category;
  result.category = newCategory;
  result.confidence = 1;
  result.needsReview = false;
  result.reason = reason;
  renderDashboard();
  renderTransactions();
  showToast(`Đã sửa ${oldCategory} → ${result.category}. Dashboard đã cập nhật.`);
  return true;
}

function addChatMessage(role, content, extraHtml = "") {
  const message = document.createElement("div");
  message.className = `chat-message ${role}`;
  message.innerHTML = `<p>${escapeHtml(content)}</p>${extraHtml}`;
  $("#chatMessages").appendChild(message);
  $("#chatMessages").scrollTop = $("#chatMessages").scrollHeight;
}

function transactionSummary(transactionId) {
  const tx = transactions.find(item => item.id === transactionId);
  const result = results.find(item => item.id === transactionId);
  if (!tx) return "";
  return `<div class="chat-result">
    <strong>${escapeHtml(tx.merchant)}</strong>
    <span>${money(tx.amount)}${result?.category ? ` · ${escapeHtml(result.category)}` : ""}</span>
    <small>${escapeHtml(tx.note)}</small>
  </div>`;
}

async function sendChatMessage(message) {
  const text = message.trim();
  if (!text) return;
  if (!agent) {
    showToast("Trợ lý đang tải dữ liệu, vui lòng thử lại.");
    return;
  }
  addChatMessage("user", text);
  $("#chatInput").value = "";
  $("#chatSendButton").disabled = true;
  addChatMessage("assistant loading", "AI đang tìm trong lịch sử giao dịch...");
  try {
    const response = await agent.chat(text, transactions, results, chatHistory);
    document.querySelector(".chat-message.loading")?.remove();
    chatHistory.push({ role: "user", content: text }, { role: "assistant", content: response.answer });
    chatHistory = chatHistory.slice(-8);
    highlightedIds = new Set(response.matchedTransactionIds);
    renderTransactions();

    const matches = response.matchedTransactionIds.map(transactionSummary).join("");
    const corrections = response.proposedCorrections.map(correction => {
      const tx = transactions.find(item => item.id === correction.id);
      return `<div class="chat-correction">
        <span>Đề xuất: <strong>${escapeHtml(tx?.merchant || correction.id)}</strong> → ${escapeHtml(correction.newCategory)}</span>
        <small>${escapeHtml(correction.reason)}</small>
        <button data-correction-id="${escapeHtml(correction.id)}" data-category="${escapeHtml(correction.newCategory)}">Áp dụng</button>
      </div>`;
    }).join("");
    addChatMessage("assistant", response.answer, matches + corrections);
  } catch (error) {
    document.querySelector(".chat-message.loading")?.remove();
    addChatMessage("assistant error", `Không thể gọi OpenRouter: ${error.message}`);
  } finally {
    $("#chatSendButton").disabled = false;
  }
}

function showToast(message) {
  $("#toast").textContent = message;
  $("#toast").classList.add("show");
  setTimeout(() => $("#toast").classList.remove("show"), 3000);
}

$("#classifyButton").addEventListener("click", runAgent);
$("#filterButton").addEventListener("click", event => {
  if (!results.length) {
    showToast("Hãy phân loại bằng AI trước khi lọc giao dịch cần xác nhận.");
    return;
  }
  reviewOnly = !reviewOnly;
  event.target.textContent = reviewOnly ? "Cần xác nhận" : "Tất cả";
  renderTransactions();
});
$("#chatForm").addEventListener("submit", event => {
  event.preventDefault();
  sendChatMessage($("#chatInput").value);
});
document.querySelectorAll("[data-prompt]").forEach(button => button.addEventListener("click", () => {
  sendChatMessage(button.dataset.prompt);
}));
$("#chatMessages").addEventListener("click", event => {
  const button = event.target.closest("[data-correction-id]");
  if (!button) return;
  if (applyCategoryCorrection(button.dataset.correctionId, button.dataset.category, "Đã xác nhận đề xuất từ AI chatbot")) {
    button.disabled = true;
    button.textContent = "Đã áp dụng";
  }
});

loadData().catch(() => {
  $("#transactions").innerHTML = "<p>Không tải được data. Hãy chạy prototype bằng HTTP server theo README.</p>";
});
