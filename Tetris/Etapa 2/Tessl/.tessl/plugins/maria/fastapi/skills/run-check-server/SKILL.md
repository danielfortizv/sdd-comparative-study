---
name: run-check-server
description: Start a FastAPI dev server, verify docs and OpenAPI schema, test endpoints, and run pytest. Use when running, checking, or debugging a FastAPI application.
---

# Run & Check FastAPI Server

## Steps

1. **Start the dev server**:

```bash
fastapi dev app/main.py
```

This enables auto-reload. For production, use `fastapi run app/main.py`.

2. **Verify interactive docs** load:

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs
# Expect: 200
```

3. **Check the OpenAPI schema**:

```bash
curl -s http://127.0.0.1:8000/openapi.json | python -m json.tool
```

Confirm all expected endpoints and response models appear.

4. **Test endpoints** with curl:

```bash
# GET example
curl -s http://127.0.0.1:8000/health

# POST example
curl -s -X POST http://127.0.0.1:8000/items/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Widget", "price": 9.99}'
```

5. **Run tests**:

```bash
pytest -v
```

6. **Troubleshooting**:

| Symptom | Cause | Fix |
|---|---|---|
| `Address already in use` | Port 8000 occupied | `lsof -i :8000` then kill the process, or use `--port 8001` |
| `ModuleNotFoundError` | Missing dependency | `pip install "fastapi[standard]"` |
| `No module named 'app'` | Wrong working directory | `cd` to the project root containing `app/` |
| 422 on POST | Request body doesn't match schema | Check the schema at `/docs` and fix the payload |
| `lifespan` error | Mixing `on_startup`/`on_shutdown` with `lifespan` | Use only `lifespan` — remove deprecated event handlers |
