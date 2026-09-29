import uuid
import datetime
from decimal import Decimal, InvalidOperation
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import get_db_connection, init_db

# Initialize FastAPI app
app = FastAPI(title="Shift Bank API", version="1.0.0")

# Enable CORS for standard frontend dev servers (such as Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Pydantic models for validation
class TransferRequest(BaseModel):
    source_account_id: str
    destination_account_id: str
    amount: str

class ConfirmRequest(BaseModel):
    code: str

@app.get("/api/accounts")
def get_accounts():
    """Returns all user accounts with their ID, name, and decimal string balance."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, balance FROM accounts")
        rows = cursor.fetchall()
        return [{"id": r["id"], "name": r["name"], "balance": r["balance"]} for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@app.get("/api/history")
def get_history(account_id: str | None = None):
    """Returns chronological ledger of transactions, optionally filtered by account_id."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if account_id:
            cursor.execute("""
                SELECT id, source_account_id, source_account_name,
                       destination_account_id, destination_account_name,
                       amount, timestamp, status
                FROM transactions
                WHERE source_account_id = ? OR destination_account_id = ?
                ORDER BY timestamp DESC
            """, (account_id, account_id))
        else:
            cursor.execute("""
                SELECT id, source_account_id, source_account_name,
                       destination_account_id, destination_account_name,
                       amount, timestamp, status
                FROM transactions
                ORDER BY timestamp DESC
            """)
        rows = cursor.fetchall()
        return [{
            "id": r["id"],
            "source_account_id": r["source_account_id"],
            "source_account_name": r["source_account_name"],
            "destination_account_id": r["destination_account_id"],
            "destination_account_name": r["destination_account_name"],
            "amount": r["amount"],
            "timestamp": r["timestamp"],
            "status": r["status"]
        } for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@app.post("/api/transfers")
def create_transfer(req: TransferRequest):
    """
    Initiates a bank transfer between accounts.
    - Non-sensitive (< 1,000,000 COP) is executed immediately and returns 200 OK.
    - Sensitive (>= 1,000,000 COP) enters PENDING_MFA state and returns 202 Accepted.
    """
    # 1. Parse amount to Decimal
    try:
        amount_dec = Decimal(req.amount)
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail="Invalid decimal format for amount")
    
    # 2. Check positive amount
    if amount_dec <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # 3. Check self-transfer
    if req.source_account_id == req.destination_account_id:
        raise HTTPException(status_code=400, detail="Source and destination accounts must be different")
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 4. Check if source account exists and retrieve details
        cursor.execute("SELECT name, balance FROM accounts WHERE id = ?", (req.source_account_id,))
        src = cursor.fetchone()
        if not src:
            raise HTTPException(status_code=400, detail="Source account not found")
        
        # 5. Check if destination account exists and retrieve details
        cursor.execute("SELECT name, balance FROM accounts WHERE id = ?", (req.destination_account_id,))
        dest = cursor.fetchone()
        if not dest:
            raise HTTPException(status_code=400, detail="Destination account not found")
        
        # 6. Check sufficient funds
        src_balance = Decimal(src["balance"])
        if src_balance < amount_dec:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        tx_id = f"tx_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # SENSITIVE TRANSFER ROUTING (>= 1,000,000.00 COP)
        if amount_dec >= Decimal("1000000.00"):
            # Insert PENDING_MFA transaction record
            with conn:
                cursor.execute("""
                    INSERT INTO transactions (
                        id, source_account_id, source_account_name,
                        destination_account_id, destination_account_name,
                        amount, timestamp, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tx_id, req.source_account_id, src["name"],
                    req.destination_account_id, dest["name"],
                    f"{amount_dec:.2f}", timestamp, "PENDING_MFA"
                ))
            return JSONResponse(
                status_code=202,
                content={"status": "PENDING_MFA", "transfer_id": tx_id}
            )
            
        # NON-SENSITIVE TRANSFER ROUTING (< 1,000,000.00 COP)
        else:
            # Execute transfer immediately in a single database transaction
            with conn:
                # Deduct source balance
                new_src_balance = src_balance - amount_dec
                cursor.execute(
                    "UPDATE accounts SET balance = ? WHERE id = ?",
                    (f"{new_src_balance:.2f}", req.source_account_id)
                )
                
                # Credit destination balance
                dest_balance = Decimal(dest["balance"])
                new_dest_balance = dest_balance + amount_dec
                cursor.execute(
                    "UPDATE accounts SET balance = ? WHERE id = ?",
                    (f"{new_dest_balance:.2f}", req.destination_account_id)
                )
                
                # Insert COMPLETED transaction record
                cursor.execute("""
                    INSERT INTO transactions (
                        id, source_account_id, source_account_name,
                        destination_account_id, destination_account_name,
                        amount, timestamp, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tx_id, req.source_account_id, src["name"],
                    req.destination_account_id, dest["name"],
                    f"{amount_dec:.2f}", timestamp, "COMPLETED"
                ))
            
            return {
                "id": tx_id,
                "source_account_id": req.source_account_id,
                "source_account_name": src["name"],
                "destination_account_id": req.destination_account_id,
                "destination_account_name": dest["name"],
                "amount": f"{amount_dec:.2f}",
                "timestamp": timestamp,
                "status": "COMPLETED"
            }
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error during transfer initiation: {e}")
    finally:
        conn.close()

@app.post("/api/transfers/{tx_id}/confirm")
def confirm_transfer(tx_id: str, req: ConfirmRequest):
    """
    Confirms a sensitive transfer by validating a 6-digit MFA code.
    If valid, updates status and atomically shifts the balances.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Query the transaction
        cursor.execute("""
            SELECT source_account_id, destination_account_id, amount, timestamp, status
            FROM transactions WHERE id = ?
        """, (tx_id,))
        tx = cursor.fetchone()
        
        if not tx:
            raise HTTPException(status_code=400, detail="Transaction not found")
        
        # 2. Check if status is PENDING_MFA
        if tx["status"] != "PENDING_MFA":
            raise HTTPException(status_code=400, detail=f"Transaction is in '{tx['status']}' state and cannot be confirmed")
        
        source_account_id = tx["source_account_id"]
        destination_account_id = tx["destination_account_id"]
        amount_dec = Decimal(tx["amount"])
        
        # 3. Verify standard MFA code
        if req.code != "123456":
            # Retain PENDING_MFA status, do not transition, just error
            raise HTTPException(status_code=400, detail="Invalid MFA code")
            
        # 4. Verify 5-minute timeout expiration
        tx_time = datetime.datetime.fromisoformat(tx["timestamp"].replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        elapsed_seconds = (now - tx_time).total_seconds()
        
        if elapsed_seconds > 300:  # 5 minutes
            with conn:
                cursor.execute("UPDATE transactions SET status = 'EXPIRED' WHERE id = ?", (tx_id,))
            raise HTTPException(status_code=400, detail="MFA session expired")
            
        # 5. Check if source account still has sufficient funds
        cursor.execute("SELECT balance FROM accounts WHERE id = ?", (source_account_id,))
        src = cursor.fetchone()
        if not src:
            with conn:
                cursor.execute("UPDATE transactions SET status = 'FAILED' WHERE id = ?", (tx_id,))
            raise HTTPException(status_code=400, detail="Source account not found")
            
        src_balance = Decimal(src["balance"])
        if src_balance < amount_dec:
            with conn:
                cursor.execute("UPDATE transactions SET status = 'FAILED' WHERE id = ?", (tx_id,))
            raise HTTPException(status_code=400, detail="Insufficient funds")
            
        # 6. Execute atomic balance transfer and complete transaction
        cursor.execute("SELECT balance FROM accounts WHERE id = ?", (destination_account_id,))
        dest = cursor.fetchone()
        if not dest:
            with conn:
                cursor.execute("UPDATE transactions SET status = 'FAILED' WHERE id = ?", (tx_id,))
            raise HTTPException(status_code=400, detail="Destination account not found")
            
        dest_balance = Decimal(dest["balance"])
        
        new_src_balance = src_balance - amount_dec
        new_dest_balance = dest_balance + amount_dec
        
        with conn:
            # Deduct source
            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (f"{new_src_balance:.2f}", source_account_id)
            )
            # Credit destination
            cursor.execute(
                "UPDATE accounts SET balance = ? WHERE id = ?",
                (f"{new_dest_balance:.2f}", destination_account_id)
            )
            # Mark COMPLETED
            cursor.execute(
                "UPDATE transactions SET status = 'COMPLETED' WHERE id = ?",
                (tx_id,)
            )
            
        return {"status": "COMPLETED", "transfer_id": tx_id}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error during confirmation: {e}")
    finally:
        conn.close()
