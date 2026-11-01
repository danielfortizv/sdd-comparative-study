---
alwaysApply: true
---

# PII Sanitisation

## Response Model Requirement

Every FastAPI endpoint MUST declare `response_model=` with a Pydantic model. This acts as an allowlist — only fields in the response model are serialised. Endpoints returning raw dicts, ORM objects, or untyped data are not permitted.

```python
# Required — explicit response model
@app.get("/users/{id}", response_model=UserResponse)

# Not permitted — no response model
@app.get("/users/{id}")
```

## PII Field Detection

When a response model contains fields matching PII patterns, warn and recommend one of:
1. **Remove** the field from the response model
2. **Mask** the field (e.g., `email` → `j***@example.com`)
3. **Document justification** with a code comment explaining why the PII is required in the response

### PII patterns to flag

| Category | Field name patterns |
|---|---|
| Email | `email`, `email_address`, `*_email` |
| Phone | `phone`, `phone_number`, `mobile`, `telephone` |
| SSN / National ID | `ssn`, `national_id`, `tax_id`, `social_security` |
| Physical address | `address`, `street`, `city`, `zip_code`, `postal_code` |
| Date of birth | `dob`, `date_of_birth`, `birth_date`, `birthday` |
| IP address | `ip`, `ip_address`, `client_ip` |
| Financial | `account_number`, `card_number`, `iban`, `routing_number` |
