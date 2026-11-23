"""Wire-contract schema tests for the Stage 4 Option A duel wire (M3, task 11.2).

These tests pin the SINGLE versioned WebSocket duel wire contract to three
mutually reinforcing sources of truth and assert they agree:

* the Pydantic models in ``app/ws/contract.py`` (the runtime layer),
* the canonical JSON Schema (Draft 2020-12) at
  ``.kiro/specs/tetris-stage4-option-a/contract/duel-wire.schema.json``,
* the examples corpus at
  ``.kiro/specs/tetris-stage4-option-a/contract/duel-wire.examples.json``
  (every example carries a ``schema_rejects`` flag).

Requirements covered: 20.11, 21.1, 21.3, 21.4, 21.6.

The four task obligations are implemented as distinct test groups:

1. Every POSITIVE corpus example parses into its model and conforms, and the
   corpus is free of placeholders / ellipsis / pipe-delimited enum strings.
2. A wrong-typed field, a missing required field, and an extra undocumented
   field each fail MODEL validation, and no reject/error string leaks a
   filesystem path, SQL text, an exception/class name, or a stack trace.
3. The FULL corpus is validated against the canonical JSON Schema with a local
   Draft 2020-12 validator: every positive conforms; every negative whose
   ``schema_rejects`` flag is true is rejected; the documented runtime-only
   cases whose ``schema_rejects`` flag is false (e.g. ``lexical_float_revision``)
   are NOT required to be schema-rejected.
4. STRICT RUNTIME TYPING: inbound ``protocol_version``, ``expected_revision`` and
   inbound ``revision`` each reject a bool, a string and a float (including a
   lexical ``1.0``) at the MODEL layer, because JSON Schema ``integer`` alone may
   accept a mathematically integral ``1.0`` -- this strict runtime integer check
   is an additional semantic rule, not a schema-expressible constraint.

NOTE on the dev dependency: these tests import ``jsonschema`` to run the
Draft 2020-12 corpus-validation obligation. The dev-lock DECLARATION/pinning of
``jsonschema`` is tracked separately (task 15.2 / dependency declaration), not by
this test module.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Type

import pytest
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ValidationError

from app.ws.contract import (
    Ack,
    ActionMessage,
    ErrorFrame,
    Hello,
    Outcome,
    Reject,
    StateFrame,
    Welcome,
)

# ---------------------------------------------------------------------------
# Corpus / schema loading (the contract artifacts are the source of truth).
# ---------------------------------------------------------------------------

_CONTRACT_DIR = (
    Path(__file__).resolve().parents[2]
    / ".kiro"
    / "specs"
    / "tetris-stage4-option-a"
    / "contract"
)
_SCHEMA_PATH = _CONTRACT_DIR / "duel-wire.schema.json"
_EXAMPLES_PATH = _CONTRACT_DIR / "duel-wire.examples.json"


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


SCHEMA: Dict[str, Any] = _load_json(_SCHEMA_PATH)
CORPUS: Dict[str, Any] = _load_json(_EXAMPLES_PATH)
POSITIVE = CORPUS["positive"]
NEGATIVE = CORPUS["negative"]

#: Map the wire ``type`` discriminator to its Pydantic model.
MODEL_BY_TYPE: Dict[str, Type[BaseModel]] = {
    "hello": Hello,
    "action": ActionMessage,
    "welcome": Welcome,
    "state": StateFrame,
    "ack": Ack,
    "reject": Reject,
    "error": ErrorFrame,
    "outcome": Outcome,
}


def _model_for(message: Dict[str, Any]) -> Type[BaseModel]:
    msg_type = message.get("type")
    assert msg_type in MODEL_BY_TYPE, f"unknown message type {msg_type!r}"
    return MODEL_BY_TYPE[msg_type]


# ---------------------------------------------------------------------------
# Obligation 1: positive corpus parses into its model and conforms, and the
# corpus text contains no placeholders / ellipsis / pipe-delimited enum strings.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("example", POSITIVE, ids=[e["name"] for e in POSITIVE])
def test_positive_example_parses_into_its_model(example: Dict[str, Any]) -> None:
    """Every documented positive example parses into its model without error.

    Validates: Requirements 20.11, 21.1
    """

    message = example["message"]
    model = _model_for(message)
    instance = model.model_validate(message)
    # Round-trip: the model re-serializes to a payload carrying the same type
    # discriminator, proving conformance rather than silent coercion.
    dumped = instance.model_dump(mode="json")
    assert dumped["type"] == message["type"]
    assert dumped["protocol_version"] == 1


def test_corpus_has_no_placeholders_or_pipe_enums() -> None:
    """The example corpus must contain concrete values, not documentation stubs.

    Asserts that the documented example MESSAGES carry concrete values: no
    ellipsis placeholder (``...``), no ``TODO``/``TBD``/``PLACEHOLDER``/``FIXME``
    marker, and no pipe-delimited enum string (for example
    ``"waiting|playing|finished"``). A real message carries a single concrete
    enum member, never the union spelling. The scan targets the message payloads
    themselves; corpus METADATA (the ``why`` documentation prose) is intentionally
    NOT scanned, because that prose legitimately quotes the schema grammar
    ``^(A|B)-([1-9][0-9]{0,14})$`` whose ``|`` is a regex alternation operator,
    not a pipe-delimited enum value in a wire message.

    Validates: Requirements 20.11, 21.1
    """

    # Structural check: no string field VALUE in any example MESSAGE is a
    # pipe-delimited enum or an ellipsis placeholder.
    def _walk(node: Any) -> None:
        if isinstance(node, str):
            assert "|" not in node, f"pipe-delimited enum value found: {node!r}"
            assert node != "...", "ellipsis placeholder value found"
        elif isinstance(node, dict):
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    for example in POSITIVE + NEGATIVE:
        _walk(example["message"])

    # Raw-text scan restricted to the serialized MESSAGE payloads only (not the
    # corpus `why`/`name` metadata), for genuine placeholder markers.
    messages_raw = "\n".join(
        json.dumps(example["message"]) for example in POSITIVE + NEGATIVE
    )
    forbidden_substrings = ["...", "TODO", "TBD", "PLACEHOLDER", "FIXME"]
    for marker in forbidden_substrings:
        assert marker not in messages_raw, (
            f"message payloads contain forbidden placeholder {marker!r}"
        )

    # Flag any JSON string literal VALUE in a message payload that holds a bare
    # pipe (a pipe-delimited enum spelled as a union instead of one member).
    pipe_in_string = re.compile(r'"[^"\\]*\|[^"\\]*"')
    offenders = pipe_in_string.findall(messages_raw)
    assert not offenders, (
        f"message payloads contain pipe-delimited enum strings: {offenders}"
    )


# ---------------------------------------------------------------------------
# Obligation 2: wrong-typed / missing-required / extra-undocumented field each
# fail model validation; and reject/error strings never leak sensitive internals.
# ---------------------------------------------------------------------------


def test_wrong_typed_field_fails_model_validation() -> None:
    """A wrong-typed field is rejected by the model.

    Uses the corpus ``wrong_type_expected_revision_string`` case: an action whose
    ``expected_revision`` is the string ``"18"`` rather than an integer.

    Validates: Requirements 21.3, 21.4
    """

    example = next(
        e for e in NEGATIVE if e["name"] == "wrong_type_expected_revision_string"
    )
    message = example["message"]
    with pytest.raises(ValidationError):
        ActionMessage.model_validate(message)


def test_missing_required_field_fails_model_validation() -> None:
    """A missing required field is rejected by the model.

    Uses the corpus ``missing_required_field_action_without_kind`` case: an
    action with no ``kind`` field.

    Validates: Requirements 21.3, 21.4
    """

    example = next(
        e for e in NEGATIVE if e["name"] == "missing_required_field_action_without_kind"
    )
    message = example["message"]
    with pytest.raises(ValidationError):
        ActionMessage.model_validate(message)


def test_extra_undocumented_field_fails_model_validation() -> None:
    """An extra undocumented field is rejected by the model (extra='forbid').

    Uses the corpus ``extra_undocumented_field_hello_client_name`` case: a hello
    carrying a forbidden ``client_name`` field (there is intentionally no such
    field and no player-name collection).

    Validates: Requirements 21.3, 21.4
    """

    example = next(
        e for e in NEGATIVE if e["name"] == "extra_undocumented_field_hello_client_name"
    )
    message = example["message"]
    with pytest.raises(ValidationError):
        Hello.model_validate(message)


#: Patterns that would indicate a leaked internal in a human-facing string.
_FILESYSTEM_PATH_RE = re.compile(
    r"(?:[A-Za-z]:\\)"           # Windows drive path e.g. C:\...
    r"|(?:/(?:usr|home|var|etc|tmp|root|opt|app)/)"  # common POSIX absolute dirs
    r"|(?:\.py\b)"               # a *.py source file name
    r"|(?:\\[A-Za-z0-9_]+\\)"    # backslash path segment
)
_SQL_RE = re.compile(
    r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|FROM|WHERE|JOIN)\b",
    re.IGNORECASE,
)
_EXCEPTION_OR_CLASS_RE = re.compile(
    r"(?:\bTraceback\b)"
    r"|(?:[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Warning)\b)"  # FooError/BarException
    r"|(?:\bself\b)"
    r"|(?:<class\b)"
    r"|(?:\bObject at 0x)"
)
_STACK_TRACE_RE = re.compile(
    r'(?:File ")'               # 'File "..."' trace line
    r'|(?:line \d+, in )'        # 'line 42, in foo'
    r"|(?:\bat [A-Za-z0-9_.]+\()"  # 'at module.func('
)


def _assert_no_leak(text: str, context: str) -> None:
    assert _FILESYSTEM_PATH_RE.search(text) is None, (
        f"{context}: string leaks a filesystem path: {text!r}"
    )
    assert _SQL_RE.search(text) is None, (
        f"{context}: string leaks SQL text: {text!r}"
    )
    assert _EXCEPTION_OR_CLASS_RE.search(text) is None, (
        f"{context}: string leaks an exception/class name: {text!r}"
    )
    assert _STACK_TRACE_RE.search(text) is None, (
        f"{context}: string leaks a stack trace: {text!r}"
    )


def test_reject_and_error_strings_do_not_leak_internals() -> None:
    """Reject ``reason`` and error ``detail``/``reason`` never leak internals.

    No reject/error human-facing string in the corpus may contain a filesystem
    path, SQL text, an exception/class name, or a stack trace. Also exercises the
    leak detectors directly against known-bad samples so the assertions are
    proven meaningful (not vacuously passing).

    Validates: Requirements 21.3, 21.6
    """

    # Sanity-check the detectors on representative leak samples.
    leak_samples = [
        r"C:\Users\svc\app\ws\contract.py",
        "SELECT * FROM high_scores WHERE id=1",
        "ValueError: value must be an integer",
        'File "contract.py", line 42, in _strict_int',
    ]
    for sample in leak_samples:
        with pytest.raises(AssertionError):
            _assert_no_leak(sample, "self-test")

    # Now assert the corpus reject/error strings are all clean, validating each
    # through its model first so we are checking model-accepted frames.
    checked = 0
    for example in POSITIVE:
        message = example["message"]
        msg_type = message.get("type")
        if msg_type == "reject":
            Reject.model_validate(message)
            _assert_no_leak(message["reason"], f"reject/{example['name']}")
            checked += 1
        elif msg_type == "error":
            ErrorFrame.model_validate(message)
            _assert_no_leak(message["reason"], f"error.reason/{example['name']}")
            _assert_no_leak(message["detail"], f"error.detail/{example['name']}")
            checked += 1
    assert checked > 0, "expected at least one reject/error example in the corpus"


# ---------------------------------------------------------------------------
# Obligation 3: validate the FULL corpus against the canonical JSON Schema with
# a local Draft 2020-12 validator.
# ---------------------------------------------------------------------------


def test_schema_itself_is_a_valid_draft_2020_12_schema() -> None:
    """The canonical schema is a well-formed Draft 2020-12 schema.

    Validates: Requirements 20.11
    """

    Draft202012Validator.check_schema(SCHEMA)


@pytest.mark.parametrize("example", POSITIVE, ids=[e["name"] for e in POSITIVE])
def test_schema_accepts_every_positive_example(example: Dict[str, Any]) -> None:
    """Every positive example conforms to the canonical JSON Schema.

    Validates: Requirements 20.11, 21.1
    """

    validator = Draft202012Validator(SCHEMA)
    errors = sorted(validator.iter_errors(example["message"]), key=str)
    assert not errors, (
        f"positive example {example['name']!r} unexpectedly rejected by schema: "
        f"{[e.message for e in errors]}"
    )


@pytest.mark.parametrize("example", NEGATIVE, ids=[e["name"] for e in NEGATIVE])
def test_schema_rejects_flagged_negative_examples(example: Dict[str, Any]) -> None:
    """A negative example is schema-rejected iff its ``schema_rejects`` flag is true.

    Every negative with ``schema_rejects`` true MUST be rejected by the schema.
    The documented runtime-only cases with ``schema_rejects`` false (for example
    ``lexical_float_revision`` where the schema's ``integer`` may accept 1.0, and
    ``action_before_start_waiting`` which is a schema-valid frame gated only at
    runtime) are NOT required to be schema-rejected.

    Validates: Requirements 20.11, 21.3, 21.4, 21.6
    """

    validator = Draft202012Validator(SCHEMA)
    is_valid = validator.is_valid(example["message"])

    if example["schema_rejects"]:
        assert not is_valid, (
            f"negative example {example['name']!r} with schema_rejects=true was "
            f"NOT rejected by the schema"
        )
    else:
        # Runtime-only case: documents that the schema does NOT catch it. We only
        # record that the flag is honored; we do not require a schema rejection.
        assert is_valid or not is_valid  # intentionally no schema-rejection demand


def test_runtime_only_lexical_float_is_not_required_to_be_schema_rejected() -> None:
    """The documented ``lexical_float_revision`` case is runtime-only.

    Its ``schema_rejects`` flag is false; it must NOT be asserted as a schema
    rejection even though the MODEL rejects it (see the strict-typing tests).

    Validates: Requirements 20.11, 21.4
    """

    example = next(e for e in NEGATIVE if e["name"] == "lexical_float_revision")
    assert example["schema_rejects"] is False


# ---------------------------------------------------------------------------
# Obligation 4: STRICT RUNTIME TYPING at the MODEL layer. Inbound
# protocol_version, expected_revision and inbound revision each reject bool, str
# and float (including a lexical 1.0), even where JSON Schema integer accepts 1.0.
# ---------------------------------------------------------------------------

#: The non-integer values each strict inbound integer field must reject.
_STRICT_INT_REJECTS = [
    pytest.param(True, id="bool_true"),
    pytest.param(False, id="bool_false"),
    pytest.param("1", id="str_1"),
    pytest.param("18", id="str_18"),
    pytest.param(1.0, id="float_lexical_1_0"),
    pytest.param(18.0, id="float_18_0"),
]


def _valid_hello() -> Dict[str, Any]:
    return {"type": "hello", "protocol_version": 1, "room_id": "room-42"}


def _valid_action() -> Dict[str, Any]:
    return {
        "type": "action",
        "protocol_version": 1,
        "room_id": "room-42",
        "seat_id": "A",
        "action_id": "A-1",
        "expected_revision": 18,
        "kind": "cw",
    }


def _valid_ack() -> Dict[str, Any]:
    return {
        "type": "ack",
        "protocol_version": 1,
        "room_id": "room-42",
        "seat_id": "A",
        "action_id": "A-1",
        "revision": 19,
        "applied": True,
        "no_op": False,
    }


@pytest.mark.parametrize("bad_value", _STRICT_INT_REJECTS)
def test_protocol_version_rejects_non_int_at_runtime(bad_value: Any) -> None:
    """Inbound ``protocol_version`` rejects bool, str and float at the model layer.

    Validates: Requirements 21.4
    """

    message = _valid_hello()
    message["protocol_version"] = bad_value
    with pytest.raises(ValidationError):
        Hello.model_validate(message)


@pytest.mark.parametrize("bad_value", _STRICT_INT_REJECTS)
def test_expected_revision_rejects_non_int_at_runtime(bad_value: Any) -> None:
    """Inbound ``expected_revision`` rejects bool, str and float at the model layer.

    Validates: Requirements 21.4
    """

    message = _valid_action()
    message["expected_revision"] = bad_value
    with pytest.raises(ValidationError):
        ActionMessage.model_validate(message)


@pytest.mark.parametrize("bad_value", _STRICT_INT_REJECTS)
def test_inbound_revision_rejects_non_int_at_runtime(bad_value: Any) -> None:
    """Inbound ``revision`` (on Ack) rejects bool, str and float at the model layer.

    Validates: Requirements 21.4
    """

    message = _valid_ack()
    message["revision"] = bad_value
    with pytest.raises(ValidationError):
        Ack.model_validate(message)


def test_lexical_float_revision_schema_accepts_but_model_rejects() -> None:
    """The ``lexical_float_revision`` corpus case: schema accepts, model rejects.

    This is the crux of the additional-semantic-rule obligation: JSON Schema
    ``integer`` accepts the lexical float ``1.0`` (its value is integral), yet the
    strict runtime model rejects it because a JSON-decoded Python ``int`` is
    required. The corpus flags this with ``schema_rejects`` false.

    Validates: Requirements 20.11, 21.4
    """

    example = next(e for e in NEGATIVE if e["name"] == "lexical_float_revision")
    message = example["message"]

    # Schema side: the Draft 2020-12 validator accepts the lexical float 1.0.
    assert Draft202012Validator(SCHEMA).is_valid(message), (
        "schema was expected to ACCEPT the lexical float revision 1.0"
    )

    # Model side: strict runtime typing rejects it.
    with pytest.raises(ValidationError):
        Ack.model_validate(message)


def test_strict_int_accepts_a_genuine_int() -> None:
    """Sanity: a genuine JSON-decoded int is accepted by each inbound field.

    Guards against the strict validators being so aggressive they reject valid
    integers (which would make the rejection tests vacuous).

    Validates: Requirements 21.4
    """

    Hello.model_validate(_valid_hello())
    ActionMessage.model_validate(_valid_action())
    Ack.model_validate(_valid_ack())


# ---------------------------------------------------------------------------
# Obligation 5 (task 35.5): STRICT OUTBOUND SCALAR/BOOL TYPING. The outbound
# models must ALSO reject a boolean/float/string ``protocol_version`` and a
# boolean board cell rather than silently coercing them (``True == 1`` in
# Python). Strict tuple-collection rejection is NOT enabled globally: a valid
# decoded JSON board/coordinate array (including a negative-anchor I-piece)
# must still map to its coordinate tuples and parse. See the pre-correction
# note at
# docs/native-checks/19-m3-forfeit-writer-hello-model-z-correction/NOTE.md (F5).
# ---------------------------------------------------------------------------

#: The non-``1``/non-int values the OUTBOUND ``protocol_version`` must reject.
_STRICT_OUTBOUND_VERSION_REJECTS = [
    pytest.param(True, id="bool_true"),
    pytest.param(False, id="bool_false"),
    pytest.param("1", id="str_1"),
    pytest.param(1.0, id="float_lexical_1_0"),
]


def _valid_welcome() -> Dict[str, Any]:
    return {
        "type": "welcome",
        "protocol_version": 1,
        "room_id": "room-42",
        "seat_id": "A",
        "room_status": "waiting",
    }


def _valid_state_frame() -> Dict[str, Any]:
    """A minimal valid game_over state frame (null active_piece)."""

    return {
        "type": "state",
        "protocol_version": 1,
        "room_id": "room-42",
        "seat_id": "A",
        "revision": 0,
        "status": "game_over",
        "room_status": "waiting",
        "board": [[0] * 10 for _ in range(20)],
        "active_piece": None,
        "next_piece": None,
        "hold_piece": None,
        "can_hold": True,
        "score": 0,
        "total_lines": 0,
        "level": 1,
        "gravity_interval_ms": 500,
    }


def _valid_reject() -> Dict[str, Any]:
    return {
        "type": "reject",
        "protocol_version": 1,
        "room_id": "room-42",
        "seat_id": "A",
        "action_id": "A-1",
        "reason": "stale_revision",
        "authoritative_revision": 7,
    }


def _valid_error() -> Dict[str, Any]:
    return {
        "type": "error",
        "protocol_version": 1,
        "room_id": "room-42",
        "seat_id": "A",
        "reason": "malformed_message",
        "detail": "Malformed message.",
    }


def _valid_outcome() -> Dict[str, Any]:
    return {
        "type": "outcome",
        "protocol_version": 1,
        "room_id": "room-42",
        "result": "draw",
        "winning_seat": None,
        "losing_seat": None,
        "forfeiting_seat": None,
        "final_revision": {"A": 3, "B": 3},
    }


#: (model, builder) pairs for every OUTBOUND frame carrying ``protocol_version``.
_OUTBOUND_VERSION_CASES = [
    pytest.param(Welcome, _valid_welcome, id="welcome"),
    pytest.param(StateFrame, _valid_state_frame, id="state"),
    pytest.param(Ack, _valid_ack, id="ack"),
    pytest.param(Reject, _valid_reject, id="reject"),
    pytest.param(ErrorFrame, _valid_error, id="error"),
    pytest.param(Outcome, _valid_outcome, id="outcome"),
]


@pytest.mark.parametrize("model, builder", _OUTBOUND_VERSION_CASES)
@pytest.mark.parametrize("bad_value", _STRICT_OUTBOUND_VERSION_REJECTS)
def test_outbound_protocol_version_rejects_non_int_at_runtime(
    model: Type[BaseModel], builder: Any, bad_value: Any
) -> None:
    """Every OUTBOUND frame rejects a bool/float/str ``protocol_version``.

    The plain ``Literal[1]`` form silently accepts ``True`` (``True == 1``); the
    strict outbound validator rejects a boolean, a lexical float ``1.0`` and the
    string ``"1"`` instead of coercing them, mirroring the inbound strict rule.

    Validates: Requirements 21.1, 21.4
    """

    message = builder()
    message["protocol_version"] = bad_value
    with pytest.raises(ValidationError):
        model.model_validate(message)


@pytest.mark.parametrize("model, builder", _OUTBOUND_VERSION_CASES)
def test_outbound_protocol_version_accepts_canonical_one(
    model: Type[BaseModel], builder: Any
) -> None:
    """Sanity: a genuine ``protocol_version`` of ``1`` is still accepted/emitted.

    Guards against the strict outbound validator being so aggressive it rejects
    the canonical constant (which would make the rejection tests vacuous) and
    confirms outbound builders still emit the canonical version ``1``.

    Validates: Requirements 21.1
    """

    instance = model.model_validate(builder())
    assert instance.model_dump(mode="json")["protocol_version"] == 1


def test_outbound_state_board_rejects_boolean_cell() -> None:
    """A boolean board cell is rejected by ``StateFrame`` (no bool->int coerce).

    ``True``/``False`` must NOT be silently coerced to the cell codes ``1``/``0``;
    a board cell is a strict JSON integer in 0..7.

    Validates: Requirements 21.1, 21.4
    """

    for bad_cell in (True, False):
        message = _valid_state_frame()
        message["board"][10][0] = bad_cell
        with pytest.raises(ValidationError):
            StateFrame.model_validate(message)


def test_outbound_state_board_rejects_float_and_string_cell() -> None:
    """A float/string board cell is rejected by ``StateFrame`` as well.

    Validates: Requirements 21.1, 21.4
    """

    for bad_cell in (1.0, "1"):
        message = _valid_state_frame()
        message["board"][10][0] = bad_cell
        with pytest.raises(ValidationError):
            StateFrame.model_validate(message)


def test_outbound_state_board_accepts_all_valid_cell_codes() -> None:
    """Sanity: genuine integer cell codes 0..7 are still accepted.

    Guards against the strict cell-code validator rejecting valid integers.

    Validates: Requirements 21.1
    """

    message = _valid_state_frame()
    # Paint the top row with each valid code 0..7 then zeros.
    message["board"][0] = [0, 1, 2, 3, 4, 5, 6, 7, 0, 0]
    instance = StateFrame.model_validate(message)
    assert instance.board[0] == [0, 1, 2, 3, 4, 5, 6, 7, 0, 0]


def test_outbound_strict_cell_does_not_break_coordinate_tuples() -> None:
    """Strict cell/version typing must NOT reject valid coordinate tuples.

    A valid decoded JSON board plus a negative-anchor I-piece (origin row/col
    within the negative anchor bounds) must still map to its ``AnchorCoord`` /
    ``OccupiedCell`` tuples and parse. This pins the "do NOT globally enable
    strict tuple-collection rejection" obligation.

    Validates: Requirements 21.1, 21.4
    """

    message = _valid_state_frame()
    message["status"] = "playing"
    message["room_status"] = "playing"
    message["active_piece"] = {
        "type": "I",
        "origin": [-4, -3],
        "cells": [[0, 0], [0, 1], [0, 2], [0, 3]],
    }
    instance = StateFrame.model_validate(message)
    assert instance.active_piece is not None
    assert tuple(instance.active_piece.origin) == (-4, -3)
    assert [tuple(c) for c in instance.active_piece.cells] == [
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
    ]
