"""Acceptance checks for the authenticated demo customer and employee flows."""

import os
import json

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import unittest
from fastapi.testclient import TestClient

from backend.auth import SESSIONS
from backend.database import (db_get_refunds, db_get_workforce_tasks, engine, init_db, db_reset_all,
    employees_table, access_requests_table, onboarding_plans_table, training_assignments_table,
    customers_table, departments_table, transactions_table, refunds_table, support_tickets_table,
    expenses_table, it_tickets_table, training_modules_table, knowledge_documents_table,
    sales_leads_table, campaigns_table)
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

    def test_enterprise_seed_has_interconnected_demo_records(self):
        from sqlalchemy import func, select
        expected = {
            customers_table: 20, employees_table: 20, departments_table: 8,
            transactions_table: 50, refunds_table: 10, support_tickets_table: 20,
            expenses_table: 10, it_tickets_table: 10, onboarding_plans_table: 10,
            training_modules_table: 10, training_assignments_table: 10,
            knowledge_documents_table: 10,
            sales_leads_table: 10, campaigns_table: 8,
        }
        with engine.connect() as conn:
            counts = {table.name: conn.execute(select(func.count()).select_from(table)).scalar_one()
                      for table in expected}
        for table, minimum in expected.items():
            self.assertGreaterEqual(counts[table.name], minimum, f"{table.name} seed count: {counts[table.name]}")

    def test_admin_enterprise_overview_is_admin_only_and_covers_product_records(self):
        employee_headers = self.sign_in("employee@zerotouch.demo")
        self.assertEqual(self.client.get("/api/admin/enterprise-overview", headers=employee_headers).status_code, 403)
        admin_headers = self.sign_in("admin@zerotouch.demo")
        response = self.client.get("/api/admin/enterprise-overview", headers=admin_headers)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        for key in ("customers", "employees", "conversations", "tasks", "tickets", "transactions", "refunds", "knowledge", "audit"):
            self.assertGreater(body["metrics"][key], 0)
        self.assertGreaterEqual(len(body["agents"]), 10)

    def test_role_boundaries_and_customer_data_isolation(self):
        self.assertEqual(self.client.get("/api/workforce/tasks").status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "unknown@example.com", "password": "anything"}).status_code, 401)

        customer_headers = self.sign_in("ayush@zerotouch.demo")
        self.assertEqual(self.client.get("/api/workforce/tasks", headers=customer_headers).status_code, 403)
        txs = self.client.get("/api/customer/transactions", headers=customer_headers).json()
        self.assertTrue(txs)
        self.assertEqual(len(txs), 10)
        other_customer = self.sign_in("vansh@zerotouch.demo")
        self.assertTrue(self.client.get("/api/customer/transactions", headers=other_customer).json())
        self.assertNotEqual({item["transaction_id"] for item in txs},
                            {item["transaction_id"] for item in self.client.get("/api/customer/transactions", headers=other_customer).json()})

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
        status = self.client.post("/api/chat", headers=headers, json={"message": "Where is my refund?"})
        self.assertEqual(status.status_code, 200, status.text)
        self.assertEqual(status.json()["refund"]["refund_id"], refund["refund_id"])
        self.assertEqual(status.json()["status"], "VERIFIED")

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
        self.assertTrue(resolved.json()["reply"].startswith("Hi Ayush,"))
        self.assertNotIn("Hi Aarav Sharma", resolved.json()["reply"])
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
        self.assertGreaterEqual(queue.json()["result"]["count"], 1)

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

    def test_employee_onboarding_coordinates_departments_and_persists_conversation(self):
        from unittest.mock import patch
        headers = self.sign_in("employee@zerotouch.demo")
        with patch.dict(os.environ, {"XAI_API_KEY": ""}):
            response = self.client.post("/api/assistant", headers=headers, json={
                "message": "Onboard Rahul Sharma into Finance", "department": "hr",
            })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["provider"], "development_fallback")
        self.assertEqual(body["task"]["status"], "WAITING")
        self.assertIn("IT Agent", body["task"]["agents_involved"])
        self.assertIn("HR Agent", body["task"]["agents_involved"])
        self.assertTrue(any(action["tool"] == "create_onboarding_plan" for action in body["task"]["actions"]))
        with engine.connect() as conn:
            employee = conn.execute(employees_table.select().where(employees_table.c.employee_id == "emp-rahul")).mappings().one()
            plan = conn.execute(onboarding_plans_table.select().where(onboarding_plans_table.c.plan_id == "ONB-emp-rahul-01")).mappings().one()
            access = conn.execute(access_requests_table.select().where(access_requests_table.c.employee_id == "emp-rahul")).mappings().all()
            assignments = conn.execute(training_assignments_table.select().where(training_assignments_table.c.employee_id == "emp-rahul")).mappings().all()
        self.assertEqual(employee["department_id"], "finance")
        self.assertEqual(plan["status"], "IN_PROGRESS")
        self.assertEqual(access[0]["status"], "PENDING_APPROVAL")
        self.assertGreaterEqual(len(assignments), 4)
        admin_headers = self.sign_in("admin@zerotouch.demo")
        approved = self.client.post(f"/api/admin/access-requests/{access[0]['request_id']}/decision",
                                    headers=admin_headers, json={"decision":"APPROVE","notes":"Verified manager approval"})
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["status"], "APPROVED")
        self.assertEqual(approved.json()["reviewed_by"], "Ops Admin")
        conversation = self.client.get(f"/api/assistant/conversations/{body['conversation_id']}", headers=headers)
        self.assertEqual(conversation.status_code, 200)
        self.assertEqual([item["role"] for item in conversation.json()["messages"]], ["user", "assistant"])
        self.assertEqual(self.client.get(f"/api/assistant/conversations/{body['conversation_id']}", headers=admin_headers).status_code, 404)

    def test_employee_department_demo_scenarios_use_registered_tools(self):
        from unittest.mock import patch
        headers = self.sign_in("employee@zerotouch.demo")
        with patch.dict(os.environ, {"XAI_API_KEY": ""}):
            failed = self.client.post("/api/assistant", headers=headers, json={
                "message": "Show failed payments above ₹10,000", "department": "finance",
            })
            it_request = self.client.post("/api/assistant", headers=headers, json={
                "message": "Create an IT access request for Priya", "department": "it",
            })
            refund = self.client.post("/api/assistant", headers=headers, json={
                "message": "Process a customer refund for TX9281", "department": "support",
            })
            refund_status = self.client.post("/api/assistant", headers=headers, json={
                "message": "Check refund status for TX9281", "department": "finance",
            })
        self.assertEqual(failed.status_code, 200, failed.text)
        result = failed.json()["task"]["actions"][0]["result"]
        self.assertGreater(result["count"], 0)
        self.assertTrue(all(row["amount"] >= 10000 for row in result["transactions"]))
        self.assertEqual(it_request.status_code, 200, it_request.text)
        self.assertIn("approval", it_request.json()["reply"].lower())
        self.assertEqual(it_request.json()["task"]["status"], "WAITING")
        self.assertEqual(refund.status_code, 200, refund.text)
        self.assertIn("VERIFIED", refund.json()["reply"])
        self.assertEqual(refund_status.json()["task"]["actions"][0]["result"]["status"], "VERIFIED")

    def test_sales_and_marketing_agents_query_seeded_business_data(self):
        from unittest.mock import patch
        headers = self.sign_in("employee@zerotouch.demo")
        with patch.dict(os.environ, {"XAI_API_KEY": ""}):
            sales = self.client.post("/api/assistant", headers=headers, json={
                "message": "Find leads at Northstar Retail", "department": "sales",
            })
            marketing = self.client.post("/api/assistant", headers=headers, json={
                "message": "Show campaign performance", "department": "marketing",
            })
        self.assertEqual(sales.status_code, 200, sales.text)
        self.assertGreater(sales.json()["task"]["actions"][0]["result"]["count"], 0)
        self.assertEqual(sales.json()["task"]["actions"][0]["agent"], "Sales Agent")
        self.assertEqual(marketing.status_code, 200, marketing.text)
        self.assertGreater(marketing.json()["task"]["actions"][0]["result"]["count"], 0)
        self.assertEqual(marketing.json()["task"]["actions"][0]["agent"], "Marketing Agent")

    def test_grok_responses_tool_loop_executes_only_registered_local_tools(self):
        import asyncio
        import httpx
        from unittest.mock import patch
        from backend.xai_service import run_grok
        requests = []
        def respond(request):
            body = json.loads(request.content)
            requests.append(body)
            if len(requests) == 1:
                payload = {"id": "resp_demo_1", "output": [{"type": "function_call", "call_id": "fc_demo_1",
                    "name": "search_leads", "arguments": '{"query":"Northstar Retail"}'}]}
            else:
                payload = {"id": "resp_demo_2", "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": "Found the registered sales lead."}]}]}
            return httpx.Response(200, json=payload)
        original_client = httpx.AsyncClient
        transport = httpx.MockTransport(respond)
        with patch.dict(os.environ, {"XAI_API_KEY": "test-key", "XAI_MODEL": "grok-test"}), \
             patch("backend.xai_service.httpx.AsyncClient", side_effect=lambda **kwargs: original_client(transport=transport, **kwargs)):
            result = asyncio.run(run_grok("Find leads at Northstar Retail", {"id":"emp-aarav","name":"Aarav Sharma","role":"EMPLOYEE"}))
        self.assertEqual(result["provider"], "xai")
        self.assertEqual(result["reply"], "Found the registered sales lead.")
        self.assertEqual(result["tool_calls"][0]["tool"], "search_leads")
        self.assertGreater(result["tool_calls"][0]["result"]["count"], 0)
        self.assertEqual(requests[1]["previous_response_id"], "resp_demo_1")
        self.assertEqual(requests[1]["input"][0]["type"], "function_call_output")

