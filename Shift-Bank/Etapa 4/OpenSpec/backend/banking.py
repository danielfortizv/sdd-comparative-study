"""Transactional banking rules shared by HTTP handlers and background processors."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import os
import re
import sqlite3
import time
import uuid

from database import get_db_connection
from account_model import AccountModelError, resolve_account_reference
from encryption import EncryptionError, protect_record, reveal_record
from audit import AuditError, append_event, audit_rejections

USER_ID = "usr_101"
MFA_THRESHOLD = Decimal("1000000.00")
MFA_CODE = "123456"
MFA_SECONDS = 300
ACH_SETTLEMENT_SECONDS = 30
FAILURE_CODE = "SIMULATED_SETTLEMENT_FAILURE"
FAILURE_TEXT = "Simulated interbank settlement failed; funds were returned."
INSUFFICIENT_FUNDS = "Insufficient funds"
INVALID_MFA_CODE = "Invalid MFA code"
MFA_SESSION_EXPIRED = "MFA session expired"
BENEFICIARY_NOT_FOUND = "Beneficiary not found"
UPDATE_ACCOUNT_BALANCE = "UPDATE accounts SET balance=? WHERE id=?"


class BankingError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message, self.status_code = message, status_code
        super().__init__(message)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    dt = (dt or now_utc()).astimezone(timezone.utc)
    return dt.isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def amount(value, *, positive=True) -> Decimal:
    try:
        raw = str(value).strip()
        if not re.fullmatch(r"(?:\d+(?:\.\d{0,2})?|\.\d{1,2})", raw): raise ValueError
        result = Decimal(raw)
        if not result.is_finite() or (positive and result <= 0) or result.as_tuple().exponent < -2:
            raise ValueError
        return from_cents(to_cents(result))
    except (InvalidOperation, ValueError, TypeError):
        raise BankingError("Amount must be a valid positive monetary value with no more than two decimal places")


def money(value: Decimal) -> str:
    cents = to_cents(value)
    return f"{'-' if cents < 0 else ''}{abs(cents)//100}.{abs(cents)%100:02d}"


def to_cents(value) -> int:
    value = value if isinstance(value, Decimal) else Decimal(str(value))
    sign, digits, exponent = value.as_tuple()
    coefficient = int("".join(str(d) for d in digits) or "0")
    if exponent < -2: raise BankingError("Money values support at most two decimal places")
    cents = coefficient * (10 ** (exponent + 2))
    return -cents if sign else cents


def from_cents(cents: int) -> Decimal:
    sign = "-" if cents < 0 else ""
    value = abs(cents)
    return Decimal(f"{sign}{value // 100}.{value % 100:02d}")


def recipient(data: dict) -> dict:
    fields = {k: str(data.get(k, "")).strip() for k in ("name", "bank_name", "routing_number", "account_number")}
    if not fields["name"]: raise BankingError("Beneficiary name is required")
    if not fields["bank_name"]: raise BankingError("Bank name is required")
    if not re.fullmatch(r"[0-9]{9}", fields["routing_number"]):
        raise BankingError("Routing number must contain exactly 9 numeric digits")
    if not re.fullmatch(r"[0-9]{4,17}", fields["account_number"]):
        raise BankingError("Account number must contain 4 to 17 numeric digits")
    return fields


def _begin(conn):
    delays=(0.025,0.05,0.1,0.2)
    for attempt in range(len(delays)+1):
        try:
            conn.execute("BEGIN IMMEDIATE")
            return
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt==len(delays):
                raise AuditError("Database is busy; the operation was not committed") from None
            time.sleep(delays[attempt])


def _safe_banking_reason(message: str) -> str:
    text=message.lower()
    if "insufficient funds" in text: return "insufficient_funds"
    if "limit" in text: return "transfer_limit"
    return "business_rule_rejected"


def daily_usage(conn, day: datetime) -> Decimal:
    start = day.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    start_s, end_s = iso(start), iso(end)
    internal = conn.execute("""SELECT amount FROM transactions WHERE status='COMPLETED'
        AND COALESCE(completed_at,timestamp)>=? AND COALESCE(completed_at,timestamp)<?""", (start_s, end_s)).fetchall()
    ach = conn.execute("""SELECT amount FROM ach_transfers WHERE status IN ('pending','settled')
        AND accepted_at>=? AND accepted_at<?""", (start_s, end_s)).fetchall()
    return from_cents(sum(to_cents(r["amount"]) for r in internal + ach))


def get_limits(conn=None):
    own = conn is None
    conn = conn or get_db_connection()
    try:
        row = conn.execute("SELECT per_transfer,daily FROM transfer_limits WHERE user_id=?", (USER_ID,)).fetchone()
        return {"user_id": USER_ID, "per_transfer": row["per_transfer"], "daily": row["daily"],
                "daily_usage": money(daily_usage(conn, now_utc()))}
    finally:
        if own: conn.close()


def validate_limits(conn, value: Decimal, at: datetime):
    row = conn.execute("SELECT per_transfer,daily FROM transfer_limits WHERE user_id=?", (USER_ID,)).fetchone()
    if row is None: raise BankingError("Transfer limits are not configured", 500)
    per, daily = Decimal(row["per_transfer"]), Decimal(row["daily"])
    if to_cents(value) > to_cents(per): raise BankingError("Transfer exceeds the current per-transfer limit")
    used = daily_usage(conn, at)
    if to_cents(used) + to_cents(value) > to_cents(daily): raise BankingError("Transfer exceeds the remaining UTC daily limit")


def validate_per_transfer(conn, value: Decimal):
    row = conn.execute("SELECT per_transfer FROM transfer_limits WHERE user_id=?", (USER_ID,)).fetchone()
    if row is None: raise BankingError("Transfer limits are not configured", 500)
    if to_cents(value) > to_cents(row["per_transfer"]): raise BankingError("Transfer exceeds the current per-transfer limit")


def _account(conn, account_id):
    try:
        row = resolve_account_reference(conn, account_id)
    except AccountModelError as exc:
        raise BankingError(str(exc)) from None
    if row is None: raise BankingError("Source account not found")
    return row


@audit_rejections("internal_transfer")
def create_internal(data: dict, at=None):
    at = at or now_utc(); value = amount(data.get("amount")); src_id = data.get("source_account_id"); dst_id = data.get("destination_account_id")
    conn = get_db_connection()
    try:
        _begin(conn); src = _account(conn, src_id); dst = _account(conn, dst_id)
        if src["id"] == dst["id"]: raise BankingError("Source and destination accounts must be different")
        if Decimal(src["balance"]) < value: raise BankingError(INSUFFICIENT_FUNDS)
        validate_limits(conn, value, at)
        txid = "tx_" + uuid.uuid4().hex[:16]; timestamp = iso(at)
        if value >= MFA_THRESHOLD:
            conn.execute("""INSERT INTO transactions(id,source_account_id,source_account_name,destination_account_id,destination_account_name,amount,timestamp,status)
                VALUES(?,?,?,?,?,?,?,'PENDING_MFA')""", (txid,src["id"],src["name"],dst["id"],dst["name"],money(value),timestamp))
            append_event(conn,"internal_transfer_attempt",txid,"pending_mfa",{"source_account_id":src["id"],"destination_account_id":dst["id"],"amount":money(value)},at)
            conn.commit(); return {"status":"PENDING_MFA","transfer_id":txid}
        _execute_internal(conn, txid, src, dst, value, timestamp, at)
        append_event(conn,"internal_transfer_completed",txid,"completed",{"source_account_id":src["id"],"destination_account_id":dst["id"],"amount":money(value)},at)
        conn.commit()
        return _transaction_json(txid,src,dst,value,timestamp,"COMPLETED")
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def _execute_internal(conn, txid, src, dst, value, timestamp, completed):
    sb, db = Decimal(src["balance"]), Decimal(dst["balance"])
    if sb < value: raise BankingError(INSUFFICIENT_FUNDS)
    conn.execute(UPDATE_ACCOUNT_BALANCE, (money(from_cents(to_cents(sb)-to_cents(value))),src["id"]))
    conn.execute(UPDATE_ACCOUNT_BALANCE, (money(from_cents(to_cents(db)+to_cents(value))),dst["id"]))
    conn.execute("UPDATE transactions SET status='COMPLETED',completed_at=? WHERE id=?", (iso(completed),txid))
    # For an immediate transfer insert its completed ledger row.
    exists = conn.execute("SELECT 1 FROM transactions WHERE id=?", (txid,)).fetchone()
    if exists is None:
        conn.execute("""INSERT INTO transactions(id,source_account_id,source_account_name,destination_account_id,destination_account_name,amount,timestamp,status,completed_at)
            VALUES(?,?,?,?,?,?,?,'COMPLETED',?)""", (txid,src["id"],src["name"],dst["id"],dst["name"],money(value),timestamp,iso(completed)))


def _transaction_json(txid, src, dst, value, timestamp, state):
    return {"id":txid,"source_account_id":src["id"],"source_account_name":src["name"],"destination_account_id":dst["id"],
            "destination_account_name":dst["name"],"amount":money(value),"timestamp":timestamp,"status":state}


@audit_rejections("internal_transfer_confirmation")
def confirm_internal(txid: str, code: str, at=None):
    at = at or now_utc(); conn = get_db_connection()
    try:
        _begin(conn); tx = conn.execute("SELECT * FROM transactions WHERE id=?",(txid,)).fetchone()
        if tx is None: raise BankingError("Transaction not found")
        if tx["status"] != "PENDING_MFA": raise BankingError(f"Transaction is in '{tx['status']}' state and cannot be confirmed")
        if code != MFA_CODE: raise BankingError(INVALID_MFA_CODE)
        if (at-parse_time(tx["timestamp"])).total_seconds() > MFA_SECONDS:
            conn.execute("UPDATE transactions SET status='EXPIRED' WHERE id=?",(txid,))
            append_event(conn,"mfa_attempt",txid,"expired",{"operation":"internal_transfer","reason_code":"mfa_expired"},at)
            conn.commit(); error=BankingError(MFA_SESSION_EXPIRED); error.audit_recorded=True; raise error
        value = Decimal(tx["amount"]); validate_limits(conn,value,at)
        src = _account(conn,tx["source_account_id"]); dst = _account(conn,tx["destination_account_id"])
        if Decimal(src["balance"]) < value:
            conn.execute("UPDATE transactions SET status='FAILED',failure_reason=? WHERE id=?",(INSUFFICIENT_FUNDS,txid))
            append_event(conn,"internal_transfer_rejected",txid,"rejected",{"reason_code":"insufficient_funds"},at)
            conn.commit(); error=BankingError(INSUFFICIENT_FUNDS); error.audit_recorded=True; raise error
        append_event(conn,"mfa_attempt",txid,"authorized",{"operation":"internal_transfer"},at)
        _execute_internal(conn,txid,src,dst,value,tx["timestamp"],at)
        append_event(conn,"internal_transfer_completed",txid,"completed",{"source_account_id":tx["source_account_id"],"destination_account_id":tx["destination_account_id"],"amount":tx["amount"]},at)
        conn.commit()
        return {"status":"COMPLETED","transfer_id":txid}
    except Exception:
        if conn.in_transaction: conn.rollback()
        raise
    finally: conn.close()


@audit_rejections("transfer_limits")
def save_limits(per_transfer, daily, at=None):
    per, day = amount(per_transfer), amount(daily); at=at or now_utc(); conn=get_db_connection()
    try:
        _begin(conn); conn.execute("UPDATE transfer_limits SET per_transfer=?,daily=?,updated_at=? WHERE user_id=?",(money(per),money(day),iso(at),USER_ID))
        append_event(conn,"transfer_limits_changed","limits_"+USER_ID,"updated",{"per_transfer":money(per),"daily":money(day)},at)
        conn.commit(); return get_limits(conn)
    except Exception: conn.rollback(); raise
    finally: conn.close()


def beneficiaries():
    conn=get_db_connection()
    try: return [reveal_record("beneficiaries", dict(r)) for r in conn.execute("SELECT id,name,bank_name,routing_number,account_number FROM beneficiaries WHERE user_id=? ORDER BY created_at",(USER_ID,))]
    finally: conn.close()


def beneficiary_create(data, at=None): return _beneficiary_write(None,data,at)
def beneficiary_update(bid,data,at=None): return _beneficiary_write(bid,data,at)
@audit_rejections("beneficiary_change")
def _beneficiary_write(bid,data,at=None):
    rec=recipient(data); at=iso(at); conn=get_db_connection()
    try:
        _begin(conn)
        if bid:
            event_outcome="updated"
            protected=protect_record("beneficiaries", bid, rec)
            cur=conn.execute("UPDATE beneficiaries SET name=?,bank_name=?,routing_number=?,account_number=?,updated_at=? WHERE id=? AND user_id=?",(protected["name"],protected["bank_name"],protected["routing_number"],protected["account_number"],at,bid,USER_ID))
            if not cur.rowcount: raise BankingError(BENEFICIARY_NOT_FOUND,404)
        else:
            bid="ben_"+uuid.uuid4().hex[:16]
            event_outcome="created"
            protected=protect_record("beneficiaries", bid, rec)
            conn.execute("INSERT INTO beneficiaries VALUES(?,?,?,?,?,?,?,?)",(bid,USER_ID,protected["name"],protected["bank_name"],protected["routing_number"],protected["account_number"],at,at))
        append_event(conn,"beneficiary_changed",bid,event_outcome,{"beneficiary_id":bid},parse_time(at))
        conn.commit(); return {"id":bid,**rec}
    except Exception: conn.rollback(); raise
    finally: conn.close()


@audit_rejections("beneficiary_delete")
def beneficiary_delete(bid):
    conn=get_db_connection()
    try:
        _begin(conn)
        cur=conn.execute("DELETE FROM beneficiaries WHERE id=? AND user_id=?",(bid,USER_ID))
        if not cur.rowcount: raise BankingError(BENEFICIARY_NOT_FOUND,404)
        append_event(conn,"beneficiary_changed",bid,"deleted",{"beneficiary_id":bid})
        conn.commit()
        return {"status":"deleted"}
    except Exception:
        if conn.in_transaction: conn.rollback()
        raise
    finally: conn.close()


def _resolve_recipient(conn, data):
    bid=data.get("beneficiary_id")
    if bid:
        row=conn.execute("SELECT * FROM beneficiaries WHERE id=? AND user_id=?",(bid,USER_ID)).fetchone()
        if not row: raise BankingError(BENEFICIARY_NOT_FOUND,404)
        protected=reveal_record("beneficiaries", dict(row))
        return {"name":protected["name"],"bank_name":protected["bank_name"],"routing_number":protected["routing_number"],"account_number":protected["account_number"]},bid
    return recipient(data),None


@audit_rejections("ach_transfer")
def submit_ach(data, at=None, occurrence_id=None):
    at=at or now_utc(); value=amount(data.get("amount")); conn=get_db_connection()
    try:
        _begin(conn); src=_account(conn,data.get("source_account_id")); rec,bid=_resolve_recipient(conn,data)
        if data.get("save_recipient") and bid is None:
            bid="ben_"+uuid.uuid4().hex[:16]
            timestamp=iso(at)
            protected=protect_record("beneficiaries",bid,rec)
            conn.execute("INSERT INTO beneficiaries VALUES(?,?,?,?,?,?,?,?)",(bid,USER_ID,protected["name"],protected["bank_name"],protected["routing_number"],protected["account_number"],timestamp,timestamp))
        if Decimal(src["balance"])<value: raise BankingError(INSUFFICIENT_FUNDS)
        validate_limits(conn,value,at)
        aid="ach_"+uuid.uuid4().hex[:16]; created=iso(at); state="PENDING_MFA" if value>=MFA_THRESHOLD else "pending"
        protected=protect_record("ach_transfers",aid,{"recipient_name":rec["name"],"bank_name":rec["bank_name"],"routing_number":rec["routing_number"],"account_number":rec["account_number"]})
        conn.execute("""INSERT INTO ach_transfers(id,source_account_id,source_account_name,amount,status,created_at,recipient_name,bank_name,routing_number,account_number,beneficiary_id,occurrence_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(aid,src["id"],src["name"],money(value),state,created,protected["recipient_name"],protected["bank_name"],protected["routing_number"],protected["account_number"],bid,occurrence_id))
        if state=="pending":
            _accept_ach(conn,aid,src,value,at,occurrence_id)
        append_event(conn,"ach_transfer_attempt",aid,"accepted" if state=="pending" else "pending_mfa",
                     {"source_account_id":src["id"],"amount":money(value),"beneficiary_id":bid},at)
        conn.commit(); return {"status":state,"transfer_id":aid,"mfa_required":state=="PENDING_MFA"}
    except Exception: conn.rollback(); raise
    finally: conn.close()


def _accept_ach(conn, aid, src, value, at, occurrence_id=None):
    # Requery under BEGIN IMMEDIATE so concurrent acceptance cannot overdraw.
    live=_account(conn,src["id"])
    if Decimal(live["balance"])<value: raise BankingError(INSUFFICIENT_FUNDS)
    validate_limits(conn,value,at)
    changed=conn.execute(UPDATE_ACCOUNT_BALANCE,(money(from_cents(to_cents(live["balance"])-to_cents(value))),live["id"]))
    if not changed.rowcount: raise BankingError(INSUFFICIENT_FUNDS)
    conn.execute("""UPDATE ach_transfers SET status='pending',accepted_at=? WHERE id=? AND status IN ('PENDING_MFA','pending')""",(iso(at),aid))
    if occurrence_id:
        conn.execute("UPDATE recurring_occurrences SET status='accepted',ach_transfer_id=? WHERE id=?",(aid,occurrence_id))


@audit_rejections("ach_transfer_confirmation")
def confirm_ach(aid, code, at=None):
    at=at or now_utc(); conn=get_db_connection()
    try:
        _begin(conn); tx=conn.execute("SELECT * FROM ach_transfers WHERE id=?",(aid,)).fetchone()
        if not tx: raise BankingError("Transfer not found",404)
        if tx["status"]!="PENDING_MFA": raise BankingError(f"Transfer is in '{tx['status']}' state and cannot be confirmed")
        if code!=MFA_CODE: raise BankingError(INVALID_MFA_CODE)
        if (at-parse_time(tx["created_at"])).total_seconds()>MFA_SECONDS:
            conn.execute("UPDATE ach_transfers SET status='EXPIRED' WHERE id=?",(aid,))
            append_event(conn,"mfa_attempt",aid,"expired",{"operation":"ach_transfer","reason_code":"mfa_expired"},at)
            conn.commit(); error=BankingError(MFA_SESSION_EXPIRED); error.audit_recorded=True; raise error
        value=Decimal(tx["amount"]); validate_limits(conn,value,at); src=_account(conn,tx["source_account_id"])
        if Decimal(src["balance"])<value: raise BankingError(INSUFFICIENT_FUNDS)
        recipient_data=reveal_record("ach_transfers",dict(tx))
        rec={"name":recipient_data["recipient_name"],"bank_name":recipient_data["bank_name"],"routing_number":recipient_data["routing_number"],"account_number":recipient_data["account_number"]}
        append_event(conn,"mfa_attempt",aid,"authorized",{"operation":"ach_transfer"},at)
        _accept_ach(conn,aid,src,value,at)
        append_event(conn,"ach_transfer_accepted",aid,"accepted",{"source_account_id":src["id"],"amount":money(value),"beneficiary_id":tx["beneficiary_id"]},at)
        conn.commit(); return {"status":"pending","transfer_id":aid}
    except Exception:
        if conn.in_transaction: conn.rollback()
        raise
    finally: conn.close()


def process_ach(now=None, failure_ids=None):
    """Settle due transfers; tests inject ids, production uses private environment configuration."""
    now=now or now_utc(); failures=set(failure_ids if failure_ids is not None else os.environ.get("SHIFT_BANK_SIMULATE_ACH_FAILURE_IDS", "").split(","))
    done=[]; conn=get_db_connection()
    try:
        rows=conn.execute("SELECT * FROM ach_transfers WHERE status='pending' AND accepted_at<=?",(iso(now-timedelta(seconds=ACH_SETTLEMENT_SECONDS)),)).fetchall()
        for row in rows:
            _begin(conn); current=conn.execute("SELECT * FROM ach_transfers WHERE id=?",(row["id"],)).fetchone()
            if not current or current["status"]!="pending": conn.rollback(); continue
            if current["id"] in failures:
                src=_account(conn,current["source_account_id"])
                if current["refund_applied"]==0:
                    conn.execute(UPDATE_ACCOUNT_BALANCE,(money(from_cents(to_cents(src["balance"])+to_cents(current["amount"]))),src["id"]))
                conn.execute("UPDATE ach_transfers SET status='failed',failed_at=?,failure_code=?,failure_reason=?,refund_applied=1 WHERE id=? AND status='pending'",(iso(now),FAILURE_CODE,FAILURE_TEXT,current["id"]))
                if current["occurrence_id"]:
                    conn.execute("UPDATE recurring_occurrences SET status='failed',failure_reason=? WHERE id=?",(FAILURE_TEXT,current["occurrence_id"]))
                result="failed"
                append_event(conn,"ach_transfer_failed_refunded",current["id"],"refunded_once",{"source_account_id":current["source_account_id"],"amount":current["amount"],"reason_code":FAILURE_CODE},now)
            else:
                conn.execute("UPDATE ach_transfers SET status='settled',settled_at=? WHERE id=? AND status='pending'",(iso(now),current["id"]))
                if current["occurrence_id"]:
                    conn.execute("UPDATE recurring_occurrences SET status='settled' WHERE id=?",(current["occurrence_id"],))
                result="settled"
                append_event(conn,"ach_transfer_settled",current["id"],"settled",{"source_account_id":current["source_account_id"],"amount":current["amount"]},now)
            conn.commit(); done.append({"id":current["id"],"status":result})
        return done
    finally: conn.close()


def expire_pending_mfa(now=None):
    now=now or now_utc(); cutoff=iso(now-timedelta(seconds=MFA_SECONDS)); conn=get_db_connection()
    try:
        _begin(conn)
        ach_ids=[r["id"] for r in conn.execute("SELECT id FROM ach_transfers WHERE status='PENDING_MFA' AND created_at<?",(cutoff,))]
        schedule_ids=[r["id"] for r in conn.execute("SELECT id FROM recurring_schedules WHERE status='PENDING_MFA' AND created_at<?",(cutoff,))]
        transfer_ids=[r["id"] for r in conn.execute("SELECT id FROM transactions WHERE status='PENDING_MFA' AND timestamp<?",(cutoff,))]
        a=conn.execute("UPDATE ach_transfers SET status='EXPIRED' WHERE status='PENDING_MFA' AND created_at<?",(cutoff,)).rowcount
        s=conn.execute("UPDATE recurring_schedules SET status='EXPIRED' WHERE status='PENDING_MFA' AND created_at<?",(cutoff,)).rowcount
        t=conn.execute("UPDATE transactions SET status='EXPIRED' WHERE status='PENDING_MFA' AND timestamp<?",(cutoff,)).rowcount
        for item in ach_ids: append_event(conn,"mfa_attempt",item,"expired",{"operation":"ach_transfer","reason_code":"mfa_expired"},now)
        for item in schedule_ids: append_event(conn,"mfa_attempt",item,"expired",{"operation":"recurring_schedule","reason_code":"mfa_expired"},now)
        for item in transfer_ids: append_event(conn,"mfa_attempt",item,"expired",{"operation":"internal_transfer","reason_code":"mfa_expired"},now)
        conn.commit(); return a+s+t
    except Exception: conn.rollback(); raise
    finally: conn.close()


def ach_history():
    conn=get_db_connection()
    try: return [reveal_record("ach_transfers",dict(r)) for r in conn.execute("SELECT * FROM ach_transfers ORDER BY COALESCE(accepted_at,created_at) DESC")]
    finally: conn.close()


def _future_occurrence(anchor: datetime, interval_days: int, after: datetime) -> datetime:
    delta=(after-anchor).total_seconds()
    n=max(0,int(delta//(interval_days*86400))+1)
    return anchor+timedelta(days=n*interval_days)


@audit_rejections("recurring_schedule")
def create_schedule(data, at=None):
    at=at or now_utc(); value=amount(data.get("amount")); freq=data.get("frequency")
    intervals={"daily":1,"weekly":7,"monthly":30}
    if freq not in intervals: raise BankingError("Frequency must be daily, weekly, or monthly")
    source_id=data.get("source_account_id"); typ=data.get("transfer_type","internal")
    if typ not in ("internal","ach"): raise BankingError("Transfer type must be internal or ach")
    conn=get_db_connection()
    try:
        _begin(conn); src=_account(conn,source_id)
        if typ=="internal":
            dst=_account(conn,data.get("destination_account_id"))
            if dst["id"]==src["id"]: raise BankingError("Source and destination accounts must be different")
            rec={"destination_account_id":dst["id"],"destination_account_name":dst["name"],"recipient_name":None,"bank_name":None,"routing_number":None,"account_number":None}; bid=None
        else:
            recipient_data,bid=_resolve_recipient(conn,data); rec={"destination_account_id":None,"destination_account_name":None,"recipient_name":recipient_data["name"],"bank_name":recipient_data["bank_name"],"routing_number":recipient_data["routing_number"],"account_number":recipient_data["account_number"]}
        if data.get("start_date"):
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["start_date"]): raise ValueError
                date=datetime.fromisoformat(data["start_date"]).date()
                anchor=datetime(date.year,date.month,date.day,tzinfo=timezone.utc)
            except (ValueError,TypeError): raise BankingError("Start date must be a valid UTC calendar date")
        else: anchor=at+timedelta(days=intervals[freq])
        if anchor<=at: raise BankingError("First execution time must be strictly in the future")
        validate_per_transfer(conn,value)
        sid="sch_"+uuid.uuid4().hex[:16]; state="PENDING_MFA" if value>=MFA_THRESHOLD else "active"
        protected=protect_record("recurring_schedules",sid,{k:rec[k] for k in ("recipient_name","bank_name","routing_number","account_number")})
        conn.execute("""INSERT INTO recurring_schedules(id,user_id,transfer_type,source_account_id,source_account_name,destination_account_id,destination_account_name,recipient_name,bank_name,routing_number,account_number,beneficiary_id,amount,frequency,interval_days,cadence_anchor,next_execution_at,status,created_at,mfa_expires_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(sid,USER_ID,typ,src["id"],src["name"],rec["destination_account_id"],rec["destination_account_name"],protected["recipient_name"],protected["bank_name"],protected["routing_number"],protected["account_number"],bid,money(value),freq,intervals[freq],iso(anchor),iso(anchor),state,iso(at),iso(at+timedelta(seconds=MFA_SECONDS)) if state=="PENDING_MFA" else None))
        append_event(conn,"recurring_schedule_created",sid,state.lower(),{"transfer_type":typ,"source_account_id":src["id"],"beneficiary_id":bid,"amount":money(value),"frequency":freq},at)
        conn.commit(); return {"schedule_id":sid,"status":state,"next_execution_at":iso(anchor),"mfa_required":state=="PENDING_MFA"}
    except Exception: conn.rollback(); raise
    finally: conn.close()


@audit_rejections("recurring_schedule_confirmation")
def confirm_schedule(sid, code, at=None):
    at=at or now_utc(); conn=get_db_connection()
    try:
        _begin(conn); sch=conn.execute("SELECT * FROM recurring_schedules WHERE id=? AND user_id=?",(sid,USER_ID)).fetchone()
        if not sch: raise BankingError("Schedule not found",404)
        if sch["status"]!="PENDING_MFA": raise BankingError("Schedule is not awaiting MFA")
        if code!=MFA_CODE: raise BankingError(INVALID_MFA_CODE)
        if at>=parse_time(sch["cadence_anchor"]):
            conn.execute("UPDATE recurring_schedules SET status='EXPIRED' WHERE id=?",(sid,))
            append_event(conn,"recurring_schedule_authorization",sid,"expired",{"reason_code":"first_execution_passed"},at)
            conn.commit(); error=BankingError("The first execution time has passed. Create a new schedule with a valid future start time."); error.audit_recorded=True; raise error
        if (at-parse_time(sch["created_at"])).total_seconds()>MFA_SECONDS:
            conn.execute("UPDATE recurring_schedules SET status='EXPIRED' WHERE id=?",(sid,))
            append_event(conn,"mfa_attempt",sid,"expired",{"operation":"recurring_schedule","reason_code":"mfa_expired"},at)
            conn.commit(); error=BankingError(MFA_SESSION_EXPIRED); error.audit_recorded=True; raise error
        limits=conn.execute("SELECT per_transfer FROM transfer_limits WHERE user_id=?",(USER_ID,)).fetchone()
        if Decimal(sch["amount"])>Decimal(limits["per_transfer"]): raise BankingError("Schedule exceeds the current per-transfer limit")
        append_event(conn,"mfa_attempt",sid,"authorized",{"operation":"recurring_schedule"},at)
        conn.execute("UPDATE recurring_schedules SET status='active',authorized_at=? WHERE id=?",(iso(at),sid))
        append_event(conn,"recurring_schedule_authorized",sid,"active",{"amount":sch["amount"]},at)
        conn.commit(); return {"schedule_id":sid,"status":"active"}
    except Exception:
        if conn.in_transaction: conn.rollback()
        raise
    finally: conn.close()


def list_schedules():
    conn=get_db_connection()
    try:
        schedules=[reveal_record("recurring_schedules",dict(r)) for r in conn.execute("SELECT * FROM recurring_schedules WHERE user_id=? ORDER BY created_at DESC",(USER_ID,))]
        for sch in schedules:
            sch["executions"]=[dict(r) for r in conn.execute("SELECT * FROM recurring_occurrences WHERE schedule_id=? ORDER BY scheduled_at DESC",(sch["id"],))]
        return schedules
    finally: conn.close()


@audit_rejections("recurring_schedule_lifecycle")
def control_schedule(sid, action, at=None):
    at=at or now_utc(); conn=get_db_connection()
    try:
        _begin(conn); sch=conn.execute("SELECT * FROM recurring_schedules WHERE id=? AND user_id=?",(sid,USER_ID)).fetchone()
        if not sch: raise BankingError("Schedule not found",404)
        state=sch["status"]
        if action=="pause" and state=="active": new="paused"
        elif action=="resume" and state=="paused":
            new="active"; next_at=_future_occurrence(parse_time(sch["cadence_anchor"]),sch["interval_days"],at)
            conn.execute("UPDATE recurring_schedules SET status=?,next_execution_at=? WHERE id=?",(new,iso(next_at),sid))
            append_event(conn,"recurring_schedule_resumed",sid,new,{"next_execution_at":iso(next_at)},at)
            conn.commit(); return {"schedule_id":sid,"status":new,"next_execution_at":iso(next_at)}
        elif action=="cancel" and state in ("active","paused"): new="cancelled"
        else: raise BankingError(f"Cannot {action} schedule in {state} state")
        conn.execute("UPDATE recurring_schedules SET status=? WHERE id=?",(new,sid))
        append_event(conn,"recurring_schedule_"+action,sid,new,{"previous_status":state},at)
        conn.commit(); return {"schedule_id":sid,"status":new}
    except Exception: conn.rollback(); raise
    finally: conn.close()


def process_schedules(now=None):
    now=now or now_utc(); conn=get_db_connection(); results=[]
    try:
        due=conn.execute("SELECT id FROM recurring_schedules WHERE status='active' AND next_execution_at<=? ORDER BY next_execution_at",(iso(now),)).fetchall()
        for item in due:
            _begin(conn); sch=conn.execute("SELECT * FROM recurring_schedules WHERE id=?",(item["id"],)).fetchone()
            if not sch or sch["status"]!="active" or parse_time(sch["next_execution_at"])>now:
                conn.rollback(); continue
            sch=reveal_record("recurring_schedules",dict(sch))
            scheduled=parse_time(sch["next_execution_at"]); occurrence_id="occ_"+hashlib.sha256(f"{sch['id']}|{iso(scheduled)}".encode()).hexdigest()[:24]
            existing=conn.execute("SELECT id FROM recurring_occurrences WHERE schedule_id=? AND scheduled_at=?",(sch["id"],iso(scheduled))).fetchone()
            if existing:
                next_at=_future_occurrence(parse_time(sch["cadence_anchor"]),sch["interval_days"],now)
                conn.execute("UPDATE recurring_schedules SET next_execution_at=? WHERE id=?",(iso(next_at),sch["id"])); conn.commit(); continue
            conn.execute("INSERT INTO recurring_occurrences(id,schedule_id,scheduled_at,status,attempted_at) VALUES(?,?,?,'processing',?)",(occurrence_id,sch["id"],iso(scheduled),iso(now)))
            value=Decimal(sch["amount"]); reason=None
            try:
                src=_account(conn,sch["source_account_id"])
                validate_limits(conn,value,now)
                if Decimal(src["balance"])<value: raise BankingError(INSUFFICIENT_FUNDS)
                if sch["transfer_type"]=="internal":
                    dst=_account(conn,sch["destination_account_id"]); txid="tx_"+uuid.uuid4().hex[:16]
                    timestamp=iso(now)
                    conn.execute(UPDATE_ACCOUNT_BALANCE,(money(from_cents(to_cents(src["balance"])-to_cents(value))),src["id"]))
                    conn.execute(UPDATE_ACCOUNT_BALANCE,(money(from_cents(to_cents(dst["balance"])+to_cents(value))),dst["id"]))
                    conn.execute("""INSERT INTO transactions(id,source_account_id,source_account_name,destination_account_id,destination_account_name,amount,timestamp,status,completed_at,occurrence_id)
                        VALUES(?,?,?,?,?,?,?,'COMPLETED',?,?)""",(txid,src["id"],src["name"],dst["id"],dst["name"],money(value),timestamp,timestamp,occurrence_id))
                    conn.execute("UPDATE recurring_occurrences SET status='completed',transaction_id=? WHERE id=?",(txid,occurrence_id))
                else:
                    aid="ach_"+uuid.uuid4().hex[:16]
                    protected=protect_record("ach_transfers",aid,{"recipient_name":sch["recipient_name"],"bank_name":sch["bank_name"],"routing_number":sch["routing_number"],"account_number":sch["account_number"]})
                    conn.execute("""INSERT INTO ach_transfers(id,source_account_id,source_account_name,amount,status,created_at,accepted_at,recipient_name,bank_name,routing_number,account_number,beneficiary_id,occurrence_id)
                        VALUES(?,?,?,?,'pending',?,?,?,?,?,?,?,?)""",(aid,sch["source_account_id"],sch["source_account_name"],money(value),iso(now),iso(now),protected["recipient_name"],protected["bank_name"],protected["routing_number"],protected["account_number"],sch["beneficiary_id"],occurrence_id))
                    conn.execute(UPDATE_ACCOUNT_BALANCE,(money(from_cents(to_cents(src["balance"])-to_cents(value))),src["id"]))
                    conn.execute("UPDATE recurring_occurrences SET status='accepted',ach_transfer_id=? WHERE id=?",(aid,occurrence_id))
            except BankingError as err:
                reason=err.message; conn.execute("UPDATE recurring_occurrences SET status='failed',failure_reason=? WHERE id=?",(reason,occurrence_id))
            append_event(conn,"recurring_execution",occurrence_id,"failed" if reason else "completed",{
                "schedule_id":sch["id"],"transfer_type":sch["transfer_type"],"amount":money(value),
                "transaction_id":txid if not reason and sch["transfer_type"]=="internal" else None,
                "ach_transfer_id":aid if not reason and sch["transfer_type"]=="ach" else None,
                "reason_code":_safe_banking_reason(reason) if reason else None},now)
            next_at=_future_occurrence(parse_time(sch["cadence_anchor"]),sch["interval_days"],now)
            conn.execute("UPDATE recurring_schedules SET next_execution_at=? WHERE id=? AND status='active'",(iso(next_at),sch["id"]))
            conn.commit(); results.append({"schedule_id":sch["id"],"occurrence_id":occurrence_id,"status":"failed" if reason else "processed","failure_reason":reason})
        return results
    except Exception:
        if conn.in_transaction: conn.rollback()
        raise
    finally: conn.close()


def recover_schedules(now=None):
    """Skip offline occurrences on startup/resume, preserving the original anchor."""
    now=now or now_utc(); conn=get_db_connection()
    try:
        _begin(conn)
        rows=conn.execute("SELECT id,cadence_anchor,interval_days FROM recurring_schedules WHERE status='active' AND next_execution_at<=?",(iso(now),)).fetchall()
        for row in rows:
            future=_future_occurrence(parse_time(row["cadence_anchor"]),row["interval_days"],now)
            conn.execute("UPDATE recurring_schedules SET next_execution_at=? WHERE id=? AND status='active'",(iso(future),row["id"]))
            append_event(conn,"recurring_schedule_recovered",row["id"],"missed_occurrences_skipped",{"next_execution_at":iso(future)},now)
        conn.commit(); return len(rows)
    except Exception: conn.rollback(); raise
    finally: conn.close()


def all_history(account_id=None):
    conn=get_db_connection()
    try:
        if account_id:
            try:
                resolved = resolve_account_reference(conn, account_id)
            except AccountModelError as exc:
                raise BankingError(str(exc)) from None
            if resolved is not None:
                account_id = resolved["id"]
        q="SELECT * FROM transactions"; params=()
        if account_id: q+=" WHERE source_account_id=? OR destination_account_id=?"; params=(account_id,account_id)
        results=[]
        for r in conn.execute(q,params):
            occurrence = conn.execute("SELECT schedule_id FROM recurring_occurrences WHERE id=?",(r["occurrence_id"],)).fetchone() if r["occurrence_id"] else None
            results.append({"id":r["occurrence_id"] or r["id"],"transaction_id":r["id"],"source_account_id":r["source_account_id"],"source_account_name":r["source_account_name"],"destination_account_id":r["destination_account_id"],"destination_account_name":r["destination_account_name"],"amount":r["amount"],"timestamp":r["timestamp"],"status":r["status"],"transfer_type":"recurring_internal" if occurrence else "internal","completed_at":r["completed_at"],"failure_reason":r["failure_reason"],"schedule_id":occurrence["schedule_id"] if occurrence else None})
        q="SELECT * FROM ach_transfers"; params=()
        if account_id: q+=" WHERE source_account_id=?"; params=(account_id,)
        for r in conn.execute(q,params):
            r=reveal_record("ach_transfers",dict(r))
            occurrence = conn.execute("SELECT schedule_id FROM recurring_occurrences WHERE id=?",(r["occurrence_id"],)).fetchone() if r["occurrence_id"] else None
            results.append({"id":r["occurrence_id"] or r["id"],"transfer_id":r["id"],"source_account_id":r["source_account_id"],"source_account_name":r["source_account_name"],"destination_account_id":None,"destination_account_name":r["recipient_name"],"recipient_name":r["recipient_name"],"bank_name":r["bank_name"],"routing_number":r["routing_number"],"account_number":r["account_number"],"amount":r["amount"],"timestamp":r["accepted_at"] or r["created_at"],"status":r["status"],"settled_at":r["settled_at"],"failure_code":r["failure_code"],"failure_reason":r["failure_reason"],"transfer_type":"recurring_ach" if occurrence else "ach","schedule_id":occurrence["schedule_id"] if occurrence else None})
        for r in conn.execute("SELECT o.*,s.source_account_id,s.source_account_name,s.transfer_type,s.destination_account_id,s.destination_account_name,s.recipient_name,s.amount FROM recurring_occurrences o JOIN recurring_schedules s ON s.id=o.schedule_id WHERE o.transaction_id IS NULL AND o.ach_transfer_id IS NULL"):
            schedule=conn.execute("SELECT * FROM recurring_schedules WHERE id=?",(r["schedule_id"],)).fetchone()
            recipient_name=reveal_record("recurring_schedules",dict(schedule))["recipient_name"]
            results.append({"id":r["id"],"source_account_id":r["source_account_id"],"source_account_name":r["source_account_name"],"destination_account_id":r["destination_account_id"],"destination_account_name":r["destination_account_name"] or recipient_name or "External recipient","recipient_name":recipient_name,"amount":r["amount"],"timestamp":r["attempted_at"],"scheduled_at":r["scheduled_at"],"status":r["status"],"failure_reason":r["failure_reason"],"transfer_type":"recurring_"+r["transfer_type"],"schedule_id":r["schedule_id"]})
        return sorted(results,key=lambda x:x["timestamp"],reverse=True)
    finally: conn.close()
