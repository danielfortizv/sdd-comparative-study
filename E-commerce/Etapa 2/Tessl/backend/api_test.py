import http.client
import json

BASE_HOST = "127.0.0.1"
BASE_PORT = 8000

def make_request(method, path, body=None, headers=None):
    if headers is None:
        headers = {}
    
    conn = http.client.HTTPConnection(BASE_HOST, BASE_PORT)
    try:
        body_data = None
        if body is not None:
            body_data = json.dumps(body)
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
        
        conn.request(method, path, body_data, headers)
        response = conn.getresponse()
        data = response.read()
        
        # Load JSON if content is JSON
        try:
            parsed_data = json.loads(data.decode("utf-8"))
        except:
            parsed_data = data.decode("utf-8")
            
        return response.status, parsed_data
    finally:
        conn.close()

def run_tests():
    print("====================================================")
    print("      STAGE 1 E-COMMERCE API SMOKE-TEST SUITE       ")
    print("====================================================")
    
    # 1. Get Products Catalog
    print("\n[TEST 1] GET /api/products")
    status, data = make_request("GET", "/api/products")
    print(f"Status: {status}")
    if status == 200 and isinstance(data, list) and len(data) == 5:
        print("Success: Served 5 products.")
        print(f"Sample product: {data[0]['name']} - ${data[0]['price']}")
    else:
        print(f"FAILED: Expected list of 5 products. Received: {data}")
        return False

    # 2. Register New User
    print("\n[TEST 2] POST /api/register")
    reg_body = {"username": "testuser_smoke", "password": "testpassword123"}
    status, data = make_request("POST", "/api/register", reg_body)
    print(f"Status: {status}")
    token = None
    if status == 200 and "token" in data and data["username"] == "testuser_smoke":
        token = data["token"]
        print("Success: Registered testuser_smoke.")
        print(f"Bearer Token Received: {token}")
    else:
        print(f"FAILED: Expected registration success with token. Received: {data}")
        return False

    # 3. Attempt Duplicate Registration
    print("\n[TEST 3] POST /api/register (Duplicate, expecting 409)")
    status, data = make_request("POST", "/api/register", reg_body)
    print(f"Status: {status}")
    if status == 409:
        print(f"Success: Correctly rejected duplicate user. Message: {data.get('detail')}")
    else:
        print(f"FAILED: Expected 409 Conflict for duplicate username. Received: {status}")
        return False

    # 4. Login User (Correct password)
    print("\n[TEST 4] POST /api/login")
    login_body = {"username": "testuser_smoke", "password": "testpassword123"}
    status, data = make_request("POST", "/api/login", login_body)
    print(f"Status: {status}")
    if status == 200 and "token" in data:
        token = data["token"]
        print("Success: Logged in testuser_smoke.")
    else:
        print(f"FAILED: Expected login success. Received: {data}")
        return False

    # 5. Rejection of Checkout without Authentication
    print("\n[TEST 5] POST /api/checkout (Unauthenticated checkout rejection, expecting 401)")
    checkout_body = {
        "items": [{"product_id": 1, "quantity": 2}]
    }
    status, data = make_request("POST", "/api/checkout", checkout_body)
    print(f"Status: {status}")
    if status == 401:
        print(f"Success: Correctly rejected checkout without auth. Message: {data.get('detail')}")
    else:
        print(f"FAILED: Expected 401 Unauthorized for checkout without token. Received: {status}")
        return False

    # 6. Rejection of Checkout with an Empty Cart
    print("\n[TEST 6] POST /api/checkout (Empty cart checkout rejection, expecting 422)")
    headers = {"Authorization": f"Bearer {token}"}
    empty_checkout_body = {"items": []}
    status, data = make_request("POST", "/api/checkout", empty_checkout_body, headers)
    print(f"Status: {status}")
    # Pydantic validates payload length or emptiness
    if status in (422, 400):
        print(f"Success: Correctly rejected empty cart checkout. Response: {data}")
    else:
        print(f"FAILED: Expected 422/400 validation error for empty items list. Received: {status}")
        return False

    # 7. Successful Simulated Checkout
    print("\n[TEST 7] POST /api/checkout (Authenticated & items present)")
    status, data = make_request("POST", "/api/checkout", checkout_body, headers)
    print(f"Status: {status}")
    if status == 200 and "summary" in data:
        summary = data["summary"]
        print("Success: Fictitious checkout completed.")
        print(f"Message: {data.get('message')}")
        print(f"Buyer: {summary.get('buyer')}")
        print(f"Total Amount Charged: ${summary.get('total_amount')}")
        print(f"Items summary: {summary.get('items')}")
        if "order_id" in data or "order_id" in summary:
            print("FAILED: Order ID exists in the response. Disallowed by requirements!")
            return False
        else:
            print("Success: Verified that NO Order ID is present in the response.")
    else:
        print(f"FAILED: Expected 200 OK simulated checkout success. Received: {data}")
        return False

    # 8. Authenticated Logout
    print("\n[TEST 8] POST /api/logout (Session Invalidation)")
    status, data = make_request("POST", "/api/logout", body=None, headers=headers)
    print(f"Status: {status}")
    if status == 200:
        print(f"Success: Session invalidated. Message: {data.get('message')}")
    else:
        print(f"FAILED: Expected 200 OK logout. Received: {data}")
        return False

    # 9. Verify token is cleared from memory and rejects checkout now
    print("\n[TEST 9] POST /api/checkout (Using invalidated token, expecting 401)")
    status, data = make_request("POST", "/api/checkout", checkout_body, headers)
    print(f"Status: {status}")
    if status == 401:
        print("Success: Verified session token is fully invalidated after logout.")
    else:
        print(f"FAILED: Token was not invalidated! Received status: {status}")
        return False

    print("\n====================================================")
    print("      ALL API SMOKE-TESTS PASSED SUCCESSFULLY!      ")
    print("====================================================")
    return True

if __name__ == "__main__":
    import sys
    success = run_tests()
    if not success:
        sys.exit(1)
