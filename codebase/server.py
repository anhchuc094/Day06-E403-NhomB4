from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
CATEGORIES = ["Ăn uống", "Di chuyển", "Mua sắm", "Giải trí", "Sức khỏe", "Giáo dục", "Hóa đơn", "Khác"]
CHATBOT_PROMPT_PATH = ROOT / "prompts" / "chatbot-system-prompt.md"
OUT_OF_SCOPE_ANSWER = (
    "Tôi chỉ hỗ trợ tìm kiếm giao dịch, kiểm tra giao dịch mơ hồ "
    "và đề xuất chỉnh danh mục chi tiêu."
)
IDENTITY_ANSWER = (
    "Tôi là trợ lý AI giao dịch cho ZaloPay. Tôi có thể giúp bạn tìm kiếm giao dịch, "
    "kiểm tra các khoản mơ hồ và đề xuất chỉnh danh mục chi tiêu; mọi chỉnh sửa đều cần bạn xác nhận."
)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_env_file(ROOT / ".env")


def setting(name: str, fallback: str = "") -> str:
    return os.getenv(name) or fallback


def env_file_setting(name: str) -> str:
    path = ROOT / ".env"
    if not path.exists():
        return ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("\"'")
    return ""


def openrouter_api_key() -> str:
    return env_file_setting("OPENROUTER_API_KEY") or setting("OPENROUTER_API_KEY")


def openrouter_model() -> str:
    return env_file_setting("OPENROUTER_MODEL") or setting("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def chatbot_system_prompt() -> str:
    template = CHATBOT_PROMPT_PATH.read_text(encoding="utf-8")
    return template.replace("{{CATEGORIES}}", json.dumps(CATEGORIES, ensure_ascii=False))


def is_social_message(message: str) -> bool:
    normalized = message.lower().strip(" .,!?:;")
    return normalized in {
        "xin chào",
        "chào",
        "hello",
        "hi",
        "cảm ơn",
        "cám ơn",
        "thanks",
        "thank you",
    }


def is_identity_message(message: str) -> bool:
    normalized = message.lower().strip(" .,!?:;")
    return normalized in {
        "bạn là ai",
        "bạn làm gì",
        "bạn có thể làm gì",
        "trợ lý này là gì",
        "giới thiệu bản thân",
        "who are you",
        "what can you do",
    }


def is_transaction_request(message: str, transactions: list[dict[str, Any]] | None = None) -> bool:
    normalized = message.lower()
    transaction_terms = {
        "giao dịch",
        "khoản",
        "chi tiêu",
        "merchant",
        "danh mục",
        "category",
        "mơ hồ",
        "cần xác nhận",
        "thanh toán",
        "chuyển khoản",
        "số tiền",
        "học phí",
        "ăn uống",
        "di chuyển",
        "mua sắm",
        "giải trí",
        "sức khỏe",
        "giáo dục",
        "hóa đơn",
        "tx0",
    }
    conversational_references = {"nó", "giao dịch đó", "các giao dịch trên", "đổi nó", "sửa nó"}
    if any(term in normalized for term in transaction_terms | conversational_references):
        return True
    for transaction in transactions or []:
        searchable_values = {
            str(transaction.get("id", "")).lower(),
            str(transaction.get("merchant", "")).lower(),
            str(transaction.get("note", "")).lower(),
        }
        if any(value and value in normalized for value in searchable_values):
            return True
    return False


def classify_with_openrouter(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    api_key = openrouter_api_key()
    if not api_key:
        raise RuntimeError("Thiếu OPENROUTER_API_KEY trong codebase/.env")

    compact_transactions = [
        {
            "id": item.get("id"),
            "merchant": item.get("merchant"),
            "amount": item.get("amount"),
            "note": item.get("note"),
            "time": item.get("time"),
        }
        for item in transactions
    ]
    system_prompt = f"""
Bạn là Spending Classification Agent cho ví điện tử Việt Nam.
Phân loại từng giao dịch vào đúng một category trong danh sách: {json.dumps(CATEGORIES, ensure_ascii=False)}.

Quy tắc:
- confidence là số từ 0 đến 1.
- needsReview=true nếu confidence < 0.75, nội dung mơ hồ, hoặc giao dịch giá trị lớn có nguy cơ phân loại sai.
- reason là một câu tiếng Việt ngắn, giải thích dựa trên merchant/note.
- Không bỏ sót hoặc tự thêm id.
- Tạo 1-2 insights ngắn về chi tiêu. Nếu có giao dịch cần xác nhận, phải nhắc điều đó.
- Chỉ trả JSON theo cấu trúc:
{{"classifications":[{{"id":"tx001","category":"Ăn uống","confidence":0.95,"reason":"Merchant là quán cà phê","needsReview":false}}],"insights":["..."]}}
""".strip()
    payload = {
        "model": openrouter_model(),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Phân loại các giao dịch sau:\n" + json.dumps(compact_transactions, ensure_ascii=False),
            },
        ],
    }
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "ZaloPay AI Spending Classifier",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw_response = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Không kết nối được OpenRouter: {exc.reason}") from exc

    content = raw_response["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    classifications = validate_classifications(parsed.get("classifications"), transactions)
    return {
        "classifications": classifications,
        "insights": [str(item) for item in parsed.get("insights", [])[:2]],
        "provider": "OpenRouter",
        "model": raw_response.get("model", openrouter_model()),
        "usage": raw_response.get("usage", {}),
    }


def chat_with_openrouter(
    message: str,
    transactions: list[dict[str, Any]],
    classifications: list[dict[str, Any]],
    history: list[dict[str, str]],
) -> dict[str, Any]:
    if is_identity_message(message):
        return {
            "answer": IDENTITY_ANSWER,
            "matchedTransactionIds": [],
            "proposedCorrections": [],
            "provider": "Scope guard",
            "model": "local-rule",
            "usage": {},
        }
    if not is_social_message(message) and not is_transaction_request(message, transactions):
        return {
            "answer": OUT_OF_SCOPE_ANSWER,
            "matchedTransactionIds": [],
            "proposedCorrections": [],
            "provider": "Scope guard",
            "model": "local-rule",
            "usage": {},
        }

    api_key = openrouter_api_key()
    if not api_key:
        raise RuntimeError("Thiếu OPENROUTER_API_KEY trong codebase/.env")

    classification_by_id = {
        str(item.get("id")): item for item in classifications if isinstance(item, dict)
    }
    context = []
    for transaction in transactions:
        tx_id = str(transaction.get("id", ""))
        classification = classification_by_id.get(tx_id, {})
        context.append(
            {
                "id": tx_id,
                "merchant": transaction.get("merchant"),
                "amount": transaction.get("amount"),
                "note": transaction.get("note"),
                "time": transaction.get("time"),
                "category": classification.get("category"),
                "confidence": classification.get("confidence"),
                "reason": classification.get("reason"),
                "needsReview": classification.get("needsReview"),
            }
        )

    system_prompt = chatbot_system_prompt()
    conversation = [
        {
            "role": item["role"],
            "content": item["content"][:500],
        }
        for item in history[-8:]
        if isinstance(item, dict)
        and item.get("role") in {"user", "assistant"}
        and item.get("content")
    ]
    payload = {
        "model": openrouter_model(),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            *conversation,
            {
                "role": "user",
                "content": "Yêu cầu của người dùng:\n"
                + message
                + "\n\nDữ liệu giao dịch hiện tại:\n"
                + json.dumps(context, ensure_ascii=False),
            },
        ],
    }
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "ZaloPay AI Spending Chatbot",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw_response = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Không kết nối được OpenRouter: {exc.reason}") from exc

    parsed = json.loads(raw_response["choices"][0]["message"]["content"])
    validated = validate_chat_response(parsed, transactions)
    if is_social_message(message):
        validated["matchedTransactionIds"] = []
        validated["proposedCorrections"] = []
    classified_ids = {
        str(item.get("id"))
        for item in classifications
        if isinstance(item, dict) and item.get("category") in CATEGORIES
    }
    proposed_count = len(validated["proposedCorrections"])
    validated["proposedCorrections"] = [
        item for item in validated["proposedCorrections"] if item["id"] in classified_ids
    ]
    if proposed_count and not validated["proposedCorrections"]:
        validated["answer"] += " Hãy phân loại bằng AI trước khi áp dụng chỉnh sửa danh mục."
    return {
        **validated,
        "provider": "OpenRouter",
        "model": raw_response.get("model", openrouter_model()),
        "usage": raw_response.get("usage", {}),
    }


def validate_chat_response(raw: Any, transactions: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("AI không trả về chat response dạng object")

    expected_ids = {str(item["id"]) for item in transactions}
    matched_ids = []
    raw_matches = raw.get("matchedTransactionIds")
    for tx_id in raw_matches if isinstance(raw_matches, list) else []:
        normalized = str(tx_id)
        if normalized in expected_ids and normalized not in matched_ids:
            matched_ids.append(normalized)

    corrections = []
    raw_corrections = raw.get("proposedCorrections")
    for item in raw_corrections if isinstance(raw_corrections, list) else []:
        if not isinstance(item, dict):
            continue
        tx_id = str(item.get("id", ""))
        category = str(item.get("newCategory", ""))
        if tx_id not in expected_ids or category not in CATEGORIES:
            continue
        corrections.append(
            {
                "id": tx_id,
                "newCategory": category,
                "reason": str(item.get("reason", "AI đề xuất chỉnh danh mục"))[:180],
            }
        )

    return {
        "answer": str(raw.get("answer", "Tôi chưa tìm thấy thông tin phù hợp."))[:1200],
        "matchedTransactionIds": matched_ids[:20],
        "proposedCorrections": corrections[:10],
    }


def validate_classifications(raw: Any, transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("AI không trả về classifications dạng danh sách")
    expected_ids = {str(item["id"]) for item in transactions}
    results = []
    for item in raw:
        tx_id = str(item.get("id", ""))
        if tx_id not in expected_ids:
            continue
        category = str(item.get("category", "Khác"))
        if category not in CATEGORIES:
            category = "Khác"
        confidence = max(0.0, min(1.0, float(item.get("confidence", 0))))
        results.append(
            {
                "id": tx_id,
                "category": category,
                "confidence": confidence,
                "reason": str(item.get("reason", "AI chưa cung cấp lý do"))[:180],
                "needsReview": bool(item.get("needsReview", False)) or confidence < 0.75,
            }
        )
    if {item["id"] for item in results} != expected_ids:
        raise ValueError("AI trả thiếu hoặc trùng transaction id")
    return results


class AppHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/api/health":
            self.send_json(
                {
                    "ok": True,
                    "openrouterConfigured": bool(openrouter_api_key()),
                    "model": openrouter_model(),
                }
            )
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path not in {"/api/classify", "/api/chat"}:
            if self.path.startswith("/api/"):
                self.send_json({"error": f"API endpoint không tồn tại: {self.path}"}, status=404)
            else:
                self.send_error(404)
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(content_length).decode("utf-8"))
            transactions = body.get("transactions", [])
            if not isinstance(transactions, list) or not 1 <= len(transactions) <= 50:
                raise ValueError("transactions phải là danh sách từ 1 đến 50 giao dịch")
            if self.path == "/api/classify":
                self.send_json(classify_with_openrouter(transactions))
                return

            message = str(body.get("message", "")).strip()
            classifications = body.get("classifications", [])
            history = body.get("history", [])
            if not 1 <= len(message) <= 500:
                raise ValueError("message phải có từ 1 đến 500 ký tự")
            if not isinstance(classifications, list):
                raise ValueError("classifications phải là danh sách")
            if not isinstance(history, list):
                raise ValueError("history phải là danh sách")
            self.send_json(chat_with_openrouter(message, transactions, classifications, history))
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=502)

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    os.chdir(ROOT)
    port = int(setting("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), AppHandler)
    configured = "đã cấu hình" if openrouter_api_key() else "chưa cấu hình"
    print(f"Day06 server: http://127.0.0.1:{port}")
    print(f"OpenRouter: {configured} | model: {openrouter_model()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng server.")
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
