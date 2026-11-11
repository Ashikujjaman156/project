import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

import ai
from app import create_app


def make_app(tmp_path, **cfg):
    app = create_app({"SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path/'t.db'}", "SECRET_KEY": "t",
                      "OPENAI_API_KEY": "", **cfg})
    with app.app_context():
        import seed
        seed.seed()
    return app


@pytest.fixture()
def client(tmp_path):
    return make_app(tmp_path).test_client()


@pytest.fixture()
def ai_client(tmp_path):
    return make_app(tmp_path, OPENAI_API_KEY="test-key", AI_RATE_LIMIT=3).test_client()


def post(c, url, data=None):
    with c.session_transaction() as s:
        s["_csrf"] = "tok"
    return c.post(url, data={**(data or {}), "csrf_token": "tok"}, follow_redirects=True)


def login(c, email, pw):
    return post(c, "/login", {"email": email, "password": pw})


def chat(c, text="hello", token="tok"):
    with c.session_transaction() as s:
        s["_csrf"] = "tok"
    return c.post("/assistant/chat", json={"messages": [{"role": "user", "content": text}]},
                  headers={"X-CSRF-Token": token})


def test_flow(client):
    assert client.get("/").status_code == 200
    assert client.get("/jobs", follow_redirects=True).request.path == "/login"
    assert b"Welcome back" in login(client, "student2@university.edu", "Student@123").data
    assert b"needs a CGPA" in post(client, "/jobs/1/apply").data      # 7.4 < 7.5
    assert b"Applied to" in post(client, "/jobs/2/apply").data
    assert b"already applied" in post(client, "/jobs/2/apply").data
    assert client.get("/admin").status_code == 403
    assert client.get("/dashboard").status_code == 200
    post(client, "/logout")
    login(client, "admin@university.edu", "Admin@123")
    assert client.get("/admin").status_code == 200
    assert client.get("/admin/job/1/applicants").status_code == 200
    assert b"is now Selected" in post(client, "/admin/application/1/status", {"status": "Selected"}).data
    assert client.get("/admin/job/1/export.csv").mimetype == "text/csv"
    assert b"Job posted" in post(client, "/admin/job/new", {
        "company_id": 1, "title": "QA", "eligibility_cgpa": 6, "package_lpa": 5, "deadline": "2030-01-01"}).data
    assert client.get("/admin/job/1/edit").status_code == 200


def test_register_and_csrf(client):
    assert client.post("/login", data={"email": "a", "password": "b"}).status_code == 400
    r = post(client, "/register", {"name": "X Y", "email": "x@y.edu", "password": "longenough1",
                                   "roll_no": "R1", "department": "CSE", "cgpa": "8"})
    assert b"Account created" in r.data
    assert b"already registered" in post(client, "/register", {"name": "X", "email": "x@y.edu",
        "password": "longenough1", "roll_no": "R2", "department": "C", "cgpa": "8"}).data


def test_every_page_renders(client):
    for url in ["/", "/login", "/register", "/assistant", "/nope"]:
        assert client.get(url).status_code in (200, 404), url
    login(client, "student1@university.edu", "Student@123")
    for url in ["/jobs", "/jobs?q=bank&eligible=1", "/jobs/1", "/dashboard", "/profile"]:
        assert client.get(url).status_code == 200, url
    post(client, "/logout")
    login(client, "admin@university.edu", "Admin@123")
    for url in ["/admin", "/admin/company/new", "/admin/job/new", "/admin/job/1/edit",
                "/admin/job/1/applicants", "/admin/job/1/applicants?status=Selected", "/jobs/1"]:
        assert client.get(url).status_code == 200, url


# ---------- AI assistant ----------
def test_assistant_unconfigured_uses_basic_mode(client):
    d = chat(client, "which jobs are open?").get_json()
    assert d["offline"] and "Backend Engineer" in d["reply"]


def test_assistant_pages_and_csrf(ai_client):
    assert ai_client.get("/assistant").status_code == 200
    assert b"data-endpoint" in ai_client.get("/").data
    assert chat(ai_client, token="bad").status_code == 400


def test_assistant_grounding(ai_client, monkeypatch):
    seen = {}
    monkeypatch.setattr(ai, "call_openai", lambda msgs: seen.setdefault("m", msgs) and "ok!")
    assert chat(ai_client).get_json()["reply"] == "ok!"
    assert "Backend Engineer" in seen["m"][0]["content"] and "Ayesha" not in seen["m"][0]["content"]
    seen.clear()
    login(ai_client, "student2@university.edu", "Student@123")
    chat(ai_client)
    sysmsg = seen["m"][0]["content"]
    assert "Rafi Ahmed" in sysmsg and "CGPA 7.4" in sysmsg and "Ayesha" not in sysmsg


def test_assistant_limits_and_validation(ai_client, monkeypatch):
    monkeypatch.setattr(ai, "call_openai", lambda msgs: "fine")
    with ai_client.session_transaction() as s:
        s["_csrf"] = "tok"
    bad = ai_client.post("/assistant/chat", json={"messages": [{"role": "assistant", "content": "x"}]},
                         headers={"X-CSRF-Token": "tok"})
    assert bad.status_code == 400
    assert [chat(ai_client).status_code for _ in range(4)] == [200, 200, 200, 429]


class FakeResp:
    def __init__(self, status, text="", ctype="application/json", data=None):
        self.status_code, self.text, self.headers, self._d = status, text, {"content-type": ctype}, data

    def json(self):
        return self._d


def test_call_openai_provider_quirks(ai_client, monkeypatch):
    import requests
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append((url, dict(json)))
        if len(calls) == 1:
            return FakeResp(400, "Unsupported parameter: max_completion_tokens")
        return FakeResp(200, "", data={"choices": [{"message": {"content": " hi there "}}]})

    monkeypatch.setattr(requests, "post", fake_post)
    with ai_client.application.app_context():
        assert ai.call_openai([{"role": "user", "content": "x"}]) == "hi there"
    assert calls[0][0] == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert "max_tokens" in calls[1][1]

    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResp(403, "<html>captcha</html>", "text/html"))
    with ai_client.application.app_context():
        with pytest.raises(ai.AssistantError, match="web page"):
            ai.call_openai([{"role": "user", "content": "x"}])


def test_basic_mode_personal(client):
    login(client, "student2@university.edu", "Student@123")      # CGPA 7.4
    d = chat(client, "which jobs can I apply to?").get_json()
    assert "Management Trainee" in d["reply"] and "Backend Engineer" not in d["reply"]
    assert "Applied" in chat(client, "what is my application status").get_json()["reply"]


def test_fallback_can_be_disabled(tmp_path):
    app = make_app(tmp_path, AI_FALLBACK=False)
    assert chat(app.test_client()).status_code == 503
