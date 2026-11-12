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
        
        try:
            parsed_data = json.loads(data.decode("utf-8"))
        except:
            parsed_data = data.decode("utf-8")
            
        return response.status, parsed_data
    finally:
        conn.close()

def run_stage2_tests():
    print("====================================================")
    print("      STAGE 2 PRODUCT REVIEWS & MODERATION TEST     ")
    print("====================================================")
    
    # 1. Fetch initial approved reviews for Product 1 (Premium Ergonomic Keyboard)
    print("\n[TEST 1] GET /api/products/1/reviews")
    status, reviews = make_request("GET", "/api/products/1/reviews")
    print(f"Status: {status}")
    if status == 200 and isinstance(reviews, list) and len(reviews) == 2:
        print("Success: Retrieved 2 approved reviews for Product 1.")
        print(f"Review 1 author: {reviews[0]['username']}, rating: {reviews[0]['rating']}")
        print(f"Review 2 author: {reviews[1]['username']}, rating: {reviews[1]['rating']}")
    else:
        print(f"FAILED: Expected 2 approved reviews. Received: {reviews}")
        return False

    # 2. Login standard user to submit a review
    print("\n[TEST 2] POST /api/login (Standard user)")
    login_body = {"username": "testuser_smoke", "password": "testpassword123"}
    status, data = make_request("POST", "/api/login", login_body)
    print(f"Status: {status}")
    token = None
    if status == 200 and "token" in data:
        token = data["token"]
        print("Success: Logged in testuser_smoke.")
    else:
        print(f"FAILED: Expected successful login. Received: {data}")
        return False

    # 3. Submit a review as a standard user for Product 1
    print("\n[TEST 3] POST /api/products/1/reviews")
    review_body = {
        "rating": 5,
        "comment": "Absolutely brilliant piece of tech! Changed my life.",
        "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    }
    headers = {"Authorization": f"Bearer {token}"}
    status, data = make_request("POST", "/api/products/1/reviews", review_body, headers)
    print(f"Status: {status}")
    review_id = None
    if status == 200 and "review" in data:
        review_id = data["review"]["id"]
        print(f"Success: Submitted review. ID: {review_id}, Status: {data['review']['status']}")
        if data["review"]["status"] != "pending":
            print(f"FAILED: Review should be 'pending' initially. Status: {data['review']['status']}")
            return False
    else:
        print(f"FAILED: Expected successful review submission. Received: {data}")
        return False

    # 4. Verify the new pending review is NOT visible in the public reviews list
    print("\n[TEST 4] GET /api/products/1/reviews (Verify pending not visible)")
    status, reviews = make_request("GET", "/api/products/1/reviews")
    print(f"Status: {status}")
    if status == 200 and len(reviews) == 2:
        print("Success: Pending review is hidden from public view as expected.")
    else:
        print(f"FAILED: Expected 2 approved reviews, found: {len(reviews)}")
        return False

    # 5. Non-moderator tries to access moderation list (Expecting 403 Forbidden)
    print("\n[TEST 5] GET /api/moderation/reviews (Non-moderator check)")
    status, data = make_request("GET", "/api/moderation/reviews", headers=headers)
    print(f"Status: {status}")
    if status == 403:
        print(f"Success: Correctly rejected access. Message: {data.get('detail')}")
    else:
        print(f"FAILED: Expected 403 Forbidden, received: {status}")
        return False

    # 6. Login as the default moderator user
    print("\n[TEST 6] POST /api/login (Moderator)")
    mod_login_body = {"username": "moderator", "password": "moderator"}
    status, data = make_request("POST", "/api/login", mod_login_body)
    print(f"Status: {status}")
    mod_token = None
    if status == 200 and "token" in data:
        mod_token = data["token"]
        print("Success: Logged in moderator.")
    else:
        print(f"FAILED: Expected successful login as moderator. Received: {data}")
        return False

    # 7. Moderator retrieves moderation reviews
    print("\n[TEST 7] GET /api/moderation/reviews (Moderator)")
    mod_headers = {"Authorization": f"Bearer {mod_token}"}
    status, reviews_list = make_request("GET", "/api/moderation/reviews", headers=mod_headers)
    print(f"Status: {status}")
    if status == 200 and isinstance(reviews_list, list) and len(reviews_list) >= 4:
        print(f"Success: Retrieved {len(reviews_list)} reviews for moderation.")
        pending_review = next((r for r in reviews_list if r["id"] == review_id), None)
        if pending_review and pending_review["status"] == "pending":
            print(f"Success: Found our pending review in the moderation queue.")
        else:
            print("FAILED: Our pending review was not found in the queue or had wrong status.")
            return False
    else:
        print(f"FAILED: Expected reviews list. Received: {reviews_list}")
        return False

    # 8. Moderator approves the review
    print(f"\n[TEST 8] POST /api/moderation/reviews/{review_id}/status (Approve)")
    status, data = make_request("POST", f"/api/moderation/reviews/{review_id}/status", {"status": "approved"}, mod_headers)
    print(f"Status: {status}")
    if status == 200 and data["review"]["status"] == "approved":
        print("Success: Moderator approved the review.")
    else:
        print(f"FAILED: Expected approval success. Received: {data}")
        return False

    # 9. Verify approved review is now visible in the public reviews list
    print("\n[TEST 9] GET /api/products/1/reviews (Verify newly approved is visible)")
    status, reviews = make_request("GET", "/api/products/1/reviews")
    print(f"Status: {status}")
    if status == 200 and len(reviews) == 3:
        newly_approved = next((r for r in reviews if r["id"] == review_id), None)
        if newly_approved:
            print(f"Success: Verified review {review_id} is now publicly visible! Review: '{newly_approved['comment']}'")
        else:
            print("FAILED: Could not find our approved review in the list.")
            return False
    else:
        print(f"FAILED: Expected 3 approved reviews, found: {len(reviews)}")
        return False

    print("\n====================================================")
    print("      ALL STAGE 2 API TESTS PASSED SUCCESSFULLY!     ")
    print("====================================================")
    return True

if __name__ == "__main__":
    import sys
    if not run_stage2_tests():
        sys.exit(1)
