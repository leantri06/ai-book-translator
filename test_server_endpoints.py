"""
FastAPI Server Endpoint Tests.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)

def test_endpoints():
    print("Testing GET /api/settings...")
    res = client.get("/api/settings")
    assert res.status_code == 200
    print("  Settings:", res.json())

    print("Testing POST /api/settings...")
    save_res = client.post("/api/settings", json={
        "provider": "gemini",
        "api_key": "test-key",
        "model": "gemini-2.5-flash",
        "base_url": "",
        "temperature": 0.3
    })
    assert save_res.status_code == 200

    print("Testing GET /api/projects...")
    proj_res = client.get("/api/projects")
    assert proj_res.status_code == 200
    print("  Projects count:", len(proj_res.json()))

    print("Testing GET / (index.html)...")
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert "AI Book Translator" in index_res.text
    print("  Index HTML served successfully!")

    print("\n>>> ALL API ENDPOINTS PASSED! <<<")

if __name__ == "__main__":
    test_endpoints()
