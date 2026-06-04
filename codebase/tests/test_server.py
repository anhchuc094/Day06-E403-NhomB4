import unittest

from server import (
    CATEGORIES,
    IDENTITY_ANSWER,
    OUT_OF_SCOPE_ANSWER,
    chatbot_system_prompt,
    chat_with_openrouter,
    is_social_message,
    is_identity_message,
    is_transaction_request,
    validate_chat_response,
    validate_classifications,
)


class ValidateClassificationsTest(unittest.TestCase):
    def setUp(self):
        self.transactions = [
            {"id": "tx001", "merchant": "Highlands Coffee"},
            {"id": "tx002", "merchant": "MOMO/ZLP transfer"},
        ]

    def test_normalizes_unknown_category_and_low_confidence(self):
        result = validate_classifications(
            [
                {
                    "id": "tx001",
                    "category": "Cafe",
                    "confidence": 0.9,
                    "reason": "Quán cà phê",
                    "needsReview": False,
                },
                {
                    "id": "tx002",
                    "category": CATEGORIES[-1],
                    "confidence": 0.4,
                    "reason": "Mơ hồ",
                    "needsReview": False,
                },
            ],
            self.transactions,
        )
        self.assertEqual(result[0]["category"], "Khác")
        self.assertTrue(result[1]["needsReview"])

    def test_rejects_missing_transaction(self):
        with self.assertRaises(ValueError):
            validate_classifications(
                [
                    {
                        "id": "tx001",
                        "category": "Ăn uống",
                        "confidence": 0.9,
                        "reason": "Quán cà phê",
                        "needsReview": False,
                    }
                ],
                self.transactions,
            )


class ValidateChatResponseTest(unittest.TestCase):
    def setUp(self):
        self.transactions = [
            {"id": "tx001", "merchant": "Highlands Coffee"},
            {"id": "tx002", "merchant": "VINUNI"},
        ]

    def test_keeps_valid_matches_and_corrections(self):
        result = validate_chat_response(
            {
                "answer": "Tìm thấy giao dịch học phí.",
                "matchedTransactionIds": ["tx002", "unknown"],
                "proposedCorrections": [
                    {
                        "id": "tx002",
                        "newCategory": "Giáo dục",
                        "reason": "Ghi chú là học phí",
                    },
                    {
                        "id": "tx001",
                        "newCategory": "Cafe",
                        "reason": "Category không hợp lệ",
                    },
                ],
            },
            self.transactions,
        )
        self.assertEqual(result["matchedTransactionIds"], ["tx002"])
        self.assertEqual(result["proposedCorrections"][0]["newCategory"], "Giáo dục")
        self.assertEqual(len(result["proposedCorrections"]), 1)

    def test_rejects_non_object_response(self):
        with self.assertRaises(ValueError):
            validate_chat_response([], self.transactions)

    def test_accepts_null_action_lists(self):
        result = validate_chat_response(
            {
                "answer": "Không có đề xuất.",
                "matchedTransactionIds": None,
                "proposedCorrections": None,
            },
            self.transactions,
        )
        self.assertEqual(result["matchedTransactionIds"], [])
        self.assertEqual(result["proposedCorrections"], [])

    def test_social_message_does_not_mean_search(self):
        self.assertTrue(is_social_message("xin chào"))
        self.assertTrue(is_social_message("Cảm ơn!"))
        self.assertFalse(is_social_message("Tìm giao dịch mơ hồ"))

    def test_chatbot_prompt_loads_categories(self):
        prompt = chatbot_system_prompt()
        self.assertIn("Ăn uống", prompt)
        self.assertNotIn("{{CATEGORIES}}", prompt)
        self.assertIn("Không được sử dụng kiến thức bên ngoài", prompt)

    def test_scope_detection(self):
        self.assertTrue(is_transaction_request("Tìm giao dịch mơ hồ"))
        self.assertTrue(is_transaction_request("Đổi giao dịch đó sang Giáo dục"))
        self.assertTrue(is_transaction_request("Highlands Coffee", self.transactions))
        self.assertFalse(is_transaction_request("Thời tiết hôm nay thế nào?"))

    def test_identity_message(self):
        self.assertTrue(is_identity_message("bạn là ai"))
        result = chat_with_openrouter("bạn là ai", self.transactions, [], [])
        self.assertEqual(result["answer"], IDENTITY_ANSWER)
        self.assertEqual(result["matchedTransactionIds"], [])

    def test_out_of_scope_request_does_not_call_openrouter(self):
        result = chat_with_openrouter(
            "Viết cho tôi một đoạn code Python",
            self.transactions,
            [],
            [],
        )
        self.assertEqual(result["answer"], OUT_OF_SCOPE_ANSWER)
        self.assertEqual(result["provider"], "Scope guard")
        self.assertEqual(result["matchedTransactionIds"], [])


if __name__ == "__main__":
    unittest.main()
