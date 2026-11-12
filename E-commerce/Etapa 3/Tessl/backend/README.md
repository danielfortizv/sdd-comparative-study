# E-Commerce Backend (Stage 1)

This is the Python and FastAPI server-side application for the Stage 1 E-Commerce application.

## Prerequisites
- Python 3.8+

## Setup & Installation
1. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server
Start the local server using:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at: `http://127.0.0.1:8000`
You can view interactive documentation at: `http://127.0.0.1:8000/docs`
