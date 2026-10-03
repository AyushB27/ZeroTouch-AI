"""Acceptance checks for the authenticated demo customer and employee flows."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import unittest
from fastapi.testclient import TestClient

from backend.auth import SESSIONS
from backend.database import db_get_refunds, db_get_workforce_tasks, engine, init_db, db_reset_all
from backend.main import app


class ProductFlowTests(unittest.TestCase):
    def setUp(self):
        init_db()
        db_reset_all()
        SESSIONS.clear()
        self.client = TestClient(app)

    def tearDown(self):
        SESSIONS.clear()
        engine.dispose()

    def sign_in(self, email):
        response = self.client.post("/api/auth/login", json={"email": email, "password": "demo123"})
        self.assertEqual(response.status_code, 200)
        return {"Authorization": f"Bearer {response.json()['token']}"}

    def test_role_boundaries_and_customer_data_isolation(self):
        self.assertEqual(self.client.get("/api/workforce/tasks").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "unknown@example.com", "password": "anything"}).status_code, 401)

        customer_headers = self.sign_in("ayush@zerotouch.demo")
        self.assertEqual(self.client.get("/api/workforce/tasks", headers=customer_headers).status_code, 403)
        txs = self.client.get("/api/customer/transactions", headers=customer_headers).json()
        self.assertTrue(txs)
        self.assertEqual(len(txs), 8)
        other_customer = self.sign_in("vansh@zerotouch.demo")
        self.assertEqual(self.client.get("/api/customer/transactions", headers=other_customer).json(), [])

        employee_headers = self.sign_in("employee@zerotouch.demo")
        self.assertEqual(self.client.get("/api/workforce/tasks", headers=employee_headers).status_code, 200)
        self.assertEqual(self.client.get("/api/workforce/dashboard", headers=employee_headers).status_code, 403)

        admin_headers = self.sign_in("admin@zerotouch.demo")
        self.assertEqual(self.client.get("/api/workforce/dashboard", headers=admin_headers).status_code, 200)

    def test_refund_is_executed_verified_and_idempotent(self):
        headers = self.sign_in("ayush@zerotouch.demo")
        response = self.client.post("/api/refunds/create", headers=headers, json={"transaction_id": "TX9281"})
        self.assertEqual(response.status_code, 200, response.text)
        refund = response.json()
        self.assertEqual(refund["status"], "VERIFIED")
        self.assertEqual(refund["action_ref"], "REV-TX9281")

        replay = self.client.post("/api/refunds/create", headers=headers, json={"transaction_id": "TX9281"})
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["refund_id"], refund["refund_id"])
        self.assertEqual(len(db_get_refunds("cust-ayush")), 1)
        self.assertEqual(self.client.get("/api/customer/refunds", headers=headers).json()[0]["refund_id"], refund["refund_id"])

        other_customer = self.sign_in("vansh@zerotouch.demo")
        self.assertEqual(self.client.post("/api/refunds/create", headers=other_customer, json={"transaction_id": "TX9281"}).status_code, 404)

    def test_customer_chat_executes_refund_and_escalation_creates_ticket(self):
        headers = self.sign_in("ayush@zerotouch.demo")
        resolved = self.client.post("/api/chat", headers=headers, json={
            "message": "My TX9281 payment was deducted but merchant did not receive it",
        })
        self.assertEqual(resolved.status_code, 200, resolved.text)
        self.assertEqual(resolved.json()["status"], "RESOLVED")
        self.assertTrue(resolved.json()["reply"])
        self.assertEqual(len(db_get_refunds("cust-ayush")), 1)

        escalated = self.client.post("/api/chat", headers=headers, json={
            "message": "Please check TX9342; I want a human support agent",
        })
        self.assertEqual(escalated.status_code, 200, escalated.text)
        self.assertEqual(escalated.json()["status"], "ESCALATED")
        tickets = self.client.get("/api/tickets", headers=headers).json()
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0]["case_id"], escalated.json()["case_id"])

        employee_headers = self.sign_in("employee@zerotouch.demo")
        queue = self.client.post("/api/workforce/command", headers=employee_headers, json={
            "command": "Find all unresolved high-priority customer issues",
        })
        self.assertEqual(queue.json()["result"]["count"], 1)

    def test_tickets_and_employee_commands_are_persisted(self):
        customer_headers = self.sign_in("ayush@zerotouch.demo")
        created = self.client.post("/api/tickets", headers=customer_headers, json={
            "category": "PAYMENT", "transaction_id": "TX9281", "summary": "Please review this payment",
        })
        self.assertEqual(created.status_code, 200, created.text)
        self.assertTrue(created.json()["ticket_id"].startswith("TKT-"))
        self.assertEqual(len(self.client.get("/api/tickets", headers=customer_headers).json()), 1)

        employee_headers = self.sign_in("employee@zerotouch.demo")
        report = self.client.post("/api/workforce/command", headers=employee_headers, json={
            "command": "Prepare weekly customer support report",
        })
        self.assertEqual(report.status_code, 200, report.text)
        self.assertEqual(report.json()["status"], "SUCCESS")
        self.assertGreater(report.json()["result"]["transaction_count"], 0)
        self.assertTrue(any(task.get("case_id") == report.json()["task_id"] for task in db_get_workforce_tasks()))

        failed = self.client.post("/api/workforce/command", headers=employee_headers, json={
            "command": "Summarize today's failed payments",
        })
        self.assertGreaterEqual(failed.json()["result"]["count"], 1)

        unsupported = self.client.post("/api/workforce/command", headers=employee_headers, json={
            "command": "Send money to TX9281",
        })
        self.assertEqual(unsupported.json()["status"], "NEEDS_INPUT")

    def test_workforce_approvals_use_connectors_and_authenticated_audit_actor(self):
        employee_headers = self.sign_in("employee@zerotouch.demo")
        self.client.get("/api/workforce/tasks", headers=employee_headers)

        finance = self.client.post("/api/workforce/tasks/CASE-FIN-201/approve", headers=employee_headers,
                                   json={"approver": "Spoofed Admin"})
        self.assertEqual(finance.status_code, 200, finance.text)
        self.assertEqual(finance.json()["case"]["approver"], "Aarav Sharma")
        self.assertEqual(finance.json()["case"]["verification_status"], "VERIFIED")
        self.assertIn("JRNL-STMT-902", finance.json()["case"]["execution_ref"])

        hr = self.client.post("/api/workforce/tasks/CASE-HR-101/approve", headers=employee_headers, json={})
        self.assertEqual(hr.status_code, 200, hr.text)
        self.assertEqual(hr.json()["case"]["verification_status"], "VERIFIED")

        payment = self.client.post("/api/workforce/tasks/CASE-SPT-9281/approve", headers=employee_headers, json={})
        self.assertEqual(payment.status_code, 200, payment.text)
        self.assertEqual(payment.json()["case"]["verification_status"], "VERIFIED")

        blocked = self.client.post("/api/workforce/tasks/CASE-SPT-9342/approve", headers=employee_headers, json={})
        self.assertEqual(blocked.status_code, 409)
        escalated_task = next(task for task in db_get_workforce_tasks() if task["case_id"] == "CASE-SPT-9342")
        self.assertEqual(escalated_task["status"], "ESCALATED")

