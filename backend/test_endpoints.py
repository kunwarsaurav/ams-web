import requests
import json
import time

BASE_URL = "http://localhost:8080"

def run_tests():
    print("Running Automated Tests for Endpoints...\n")

    # 1. Test Device Ping Endpoint
    print("Testing GET /device/ping")
    try:
        response = requests.get(f"{BASE_URL}/device/ping")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200, "Ping endpoint failed"
        assert "status" in response.json(), "Invalid ping response format"
        print("[PASS] Ping Endpoint OK\n")
    except Exception as e:
        print(f"[FAIL] Ping Endpoint Failed: {e}\n")

    # 2. Simulate Webhook Punch (POST /)
    print("Testing Webhook POST / (Simulating Device Punch)")
    webhook_data = {
        "user_id": "999",
        "io_time": time.strftime("%Y%m%d%H%M%S"),
        "verify_mode": "1"
    }
    headers = {
        "dev_id": "TEST_DEVICE_123",
        "request_code": "realtime_glog",
        "trans_id": "100"
    }
    try:
        response = requests.post(f"{BASE_URL}/", json=webhook_data, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        assert response.status_code == 200, "Webhook endpoint failed"
        assert response.text.strip() == "result=OK", "Webhook response must be 'result=OK'"
        print("[PASS] Webhook Punch OK\n")
    except Exception as e:
        print(f"[FAIL] Webhook Punch Failed: {e}\n")

    # 3. Simulate Webhook Enroll (POST /)
    print("Testing Webhook POST / (Simulating Device Enroll)")
    enroll_data = {
        "user_id": "999",
        "user_name": "Test User",
    }
    headers["request_code"] = "realtime_enroll_data"
    try:
        response = requests.post(f"{BASE_URL}/", json=enroll_data, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        assert response.status_code == 200, "Webhook enroll endpoint failed"
        assert response.text.strip() == "result=OK", "Webhook response must be 'result=OK'"
        print("[PASS] Webhook Enroll OK\n")
    except Exception as e:
        print(f"[FAIL] Webhook Enroll Failed: {e}\n")

    # 4. Test Get Raw Logs Endpoint
    print("Testing GET /attendance/logs/today")
    try:
        response = requests.get(f"{BASE_URL}/attendance/logs/today")
        print(f"Status: {response.status_code}")
        assert response.status_code == 200, "Get logs endpoint failed"
        logs = response.json()
        print(f"Retrieved {len(logs)} logs.")
        assert len(logs) > 0, "No logs retrieved (expected at least 1 from the test punch)"
        assert "machine_user_id" in logs[0], "Invalid log schema"
        assert "employee_name" in logs[0], "Invalid log schema"
        print("[PASS] Get Raw Logs OK\n")
    except Exception as e:
        print(f"[FAIL] Get Raw Logs Failed: {e}\n")

    # 5. Test AI Status Endpoint
    print("Testing GET /ai/status")
    try:
        response = requests.get(f"{BASE_URL}/ai/status")
        print(f"Status: {response.status_code}")
        assert response.status_code == 200, "AI status endpoint failed"
        status = response.json()
        assert "installed" in status, "Invalid AI status response"
        print(f"Response: {status}")
        print("[PASS] AI Status OK\n")
    except Exception as e:
        print(f"[FAIL] AI Status Failed: {e}\n")

if __name__ == "__main__":
    run_tests()
