import json
from unittest.mock import Mock, patch
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from .ai import _gemini_generate, get_faq_answer
from .models import StaffProfile, Ticket


class GeminiFaqTests(SimpleTestCase):
    @override_settings(GEMINI_API_KEY="test-gemini-secret", GEMINI_MODEL="gemini-3.5-flash-lite")
    @patch("support.ai.requests.post")
    def test_gemini_request_authenticates_with_header_and_returns_text(self, mock_post):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": "Gemini "}, {"text": "answer."}]}
            }]
        }
        mock_post.return_value = response

        answer = _gemini_generate("How do I create a ticket?")

        self.assertEqual(answer, "Gemini answer.")
        request = mock_post.call_args
        self.assertEqual(request.kwargs["headers"]["x-goog-api-key"], "test-gemini-secret")
        self.assertNotIn("params", request.kwargs)
        self.assertIn("gemini-3.5-flash-lite:generateContent", request.args[0])
        self.assertEqual(
            request.kwargs["json"]["contents"],
            [{"parts": [{"text": "How do I create a ticket?"}]}],
        )

    @override_settings(GEMINI_API_KEY="test-gemini-secret", GEMINI_MODEL="gemini-3.5-flash-lite")
    @patch("support.ai.requests.post")
    def test_gemini_api_error_is_logged_without_leaking_key(self, mock_post):
        response = Mock(status_code=403, ok=False)
        response.json.return_value = {
            "error": {
                "status": "PERMISSION_DENIED",
                "message": "Rejected key test-gemini-secret",
            }
        }
        mock_post.return_value = response

        with self.assertLogs("django", level="ERROR") as captured:
            answer = _gemini_generate("Question")

        self.assertIsNone(answer)
        logs = "\n".join(captured.output)
        self.assertIn("HTTP 403", logs)
        self.assertIn("[REDACTED]", logs)
        self.assertNotIn("test-gemini-secret", logs)

    @patch("support.ai._gemini_generate", return_value=None)
    def test_faq_keeps_safe_fallback_when_gemini_is_unavailable(self, _mock_generate):
        self.assertEqual(
            get_faq_answer("How do I create a ticket?"),
            "The AI assistant is temporarily unavailable. "
            "Please create a support ticket and our team will help.",
        )

    @patch("support.ai._gemini_generate", return_value="Gemini response.")
    def test_faq_displays_gemini_response(self, _mock_generate):
        self.assertEqual(get_faq_answer("How do I create a ticket?"), "Gemini response.")


class SupportWorkflowTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username="customer", password="test-pass-123")
        self.staff_user = User.objects.create_user(username="agent", password="test-pass-123")
        self.profile = StaffProfile.objects.create(user=self.staff_user, department="Technical")
        self.ticket = Ticket.objects.create(
            subject="Cannot log in", description="Login page returns an error",
            user=self.customer, priority="Medium"
        )

    def test_staff_can_claim_unassigned_ticket(self):
        self.client.login(username="agent", password="test-pass-123")
        response = self.client.post(reverse("claim_ticket", args=[self.ticket.pk]))
        self.ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.assigned_to, self.profile)
        self.assertEqual(self.ticket.status, Ticket.Status.IN_PROGRESS)

    @patch("support.views.assign_priority")
    def test_priority_and_department_are_applied_on_ticket_creation(self, mock_assign):
        mock_assign.return_value = {"priority": "High", "department": "Technical"}
        self.client.login(username="customer", password="test-pass-123")
        response = self.client.post(reverse("create_ticket"), {
            "subject": "Production is down", "description": "All users see an outage"
        })
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(subject="Production is down")
        self.assertEqual(ticket.priority, "High")
        self.assertEqual(ticket.suggested_department, "Technical")
        self.assertEqual(ticket.assigned_to, self.profile)

    def test_customer_cannot_view_another_users_ticket(self):
        other = User.objects.create_user(username="other", password="test-pass-123")
        self.client.login(username="other", password="test-pass-123")
        response = self.client.get(reverse("ticket_detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 403)

    def test_faq_endpoint_returns_json_unauthorized_without_login(self):
        response = self.client.post(reverse("get_faq_answer"), {"question": "How do I create a ticket?"})
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(
            response.content,
            {"error": "Your session expired. Please sign in again."},
        )

    @patch("support.views.get_faq_answer", return_value="Gemini response.")
    def test_faq_endpoint_returns_answer_to_authenticated_customer(self, mock_answer):
        self.client.login(username="customer", password="test-pass-123")
        response = self.client.post(reverse("get_faq_answer"), {"question": "How do I create a ticket?"})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"answer": "Gemini response."})
        mock_answer.assert_called_once_with("How do I create a ticket?")
