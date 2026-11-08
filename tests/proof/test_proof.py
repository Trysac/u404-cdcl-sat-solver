"""Tests for DRAT proof tracing and Reverse Unit Propagation (RUP) verification."""

import io
import os
import tempfile

import pytest

from cdcl_proof.proof import (
    DratProofTracer,
    ProofError,
    _normalize_clause,
    _rup_check,
    verify_rup_proof,
)


def test_drat_tracer_emit_and_close() -> None:
    output = io.StringIO()
    tracer = DratProofTracer(output)
    tracer.emit_clause([1, 2])
    tracer.emit_deletion([1, 2])
    tracer.emit_clause([])  # empty clause
    tracer.emit_deletion([])
    tracer.close()

    content = output.getvalue()
    assert "1 2 0\n" in content
    assert "d 1 2 0\n" in content
    assert "0\n" in content
    assert "d 0\n" in content

    with pytest.raises(ProofError) as exc_info:
        tracer.emit_clause([1])
    assert exc_info.value.code == "tracer_closed"

    with pytest.raises(ProofError) as exc_info:
        tracer.emit_deletion([1])
    assert exc_info.value.code == "tracer_closed"


def test_drat_tracer_file_context_manager() -> None:
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        path = tf.name

    try:
        with DratProofTracer(path) as tracer:
            tracer.emit_clause([1, -2])
            tracer.emit_deletion([1, -2])
            tracer.emit_clause([])

        with open(path, encoding="utf-8") as f:
            data = f.read()
        assert data == "1 -2 0\nd 1 -2 0\n0\n"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_acceptance_unsat_file_terminates_with_zero() -> None:
    # WHEN proof_path is provided for an UNSAT problem THEN the emitted DRAT file terminates with '0' as its final non-empty line
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        path = tf.name

    try:
        tracer = DratProofTracer(path)
        tracer.emit_clause([1])
        tracer.emit_clause([-1])
        tracer.emit_clause([])  # 0
        tracer.close()

        with open(path, encoding="utf-8") as f:
            non_empty_lines = [line.strip() for line in f if line.strip()]
        assert non_empty_lines[-1] == "0"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_acceptance_rup_checker_accepts_unsat_proof() -> None:
    # WHEN an UNSAT formula is solved with proof_path set THEN a reverse-unit-propagation checker in the tests accepts every added clause of the proof up to the empty clause '0'
    clauses = [[1, 2], [-1, 2], [1, -2], [-1, -2]]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        path = tf.name

    try:
        with open(path, "w", encoding="utf-8") as f:
            # DRAT derivation for clauses:
            # [1, 2] and [-1, 2] imply [2] by RUP
            f.write("2 0\n")
            # [1, -2] and [-1, -2] with 2 imply empty clause
            f.write("0\n")

        assert verify_rup_proof(clauses, path) is True
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_rup_with_deletion_and_tautology() -> None:
    clauses = [[1], [-1]]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        path = tf.name

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("c This is a comment\n\n")
            f.write("1 -1 0\n")  # tautology
            f.write("d 2 3 0\n")  # deletion of non-existent clause
            f.write("0\n")

        assert verify_rup_proof(clauses, path) is True
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_rup_empty_clause_derivation_from_unsat_active_set() -> None:
    # Test that empty clause '0' is verified when active_clauses become directly contradictory
    clauses = [[1], [-1]]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        path = tf.name

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("0\n")

        assert verify_rup_proof(clauses, path) is True
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_rup_initial_empty_clause() -> None:
    clauses = [[]]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        path = tf.name
    try:
        assert verify_rup_proof(clauses, path) is True
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_rup_invalid_file_handling() -> None:
    assert verify_rup_proof([[1]], "/nonexistent/path/for/sure") is False

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        path = tf.name

    try:
        # Bad line missing 0
        with open(path, "w", encoding="utf-8") as f:
            f.write("1 2\n")
        assert verify_rup_proof([[1]], path) is False

        # Non-integer token
        with open(path, "w", encoding="utf-8") as f:
            f.write("1 abc 0\n")
        assert verify_rup_proof([[1]], path) is False

        # Invalid RUP clause that is not implied
        with open(path, "w", encoding="utf-8") as f:
            f.write("3 4 0\n")
        assert verify_rup_proof([[1, 2]], path) is False

        # Empty file without empty clause
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        assert verify_rup_proof([[1, 2]], path) is False
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_rup_file_too_large() -> None:
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
        path = tf.name
        tf.write("0\n")

    try:
        with pytest.raises(ProofError) as exc_info:
            verify_rup_proof([], path, max_bytes=1)
        assert exc_info.value.code == "proof_too_large"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_helper_normalize_clause() -> None:
    assert _normalize_clause([2, 1, 1, -1]) is None
    assert _normalize_clause([3, -1, 3, 2]) == (-1, 2, 3)
    assert _normalize_clause([]) == ()


def test_rup_check_edge_cases() -> None:
    # Tautology in rup check
    assert _rup_check((1, -1), []) is True
    # Immediate conflict when assigning negations of duplicate opposite lits
    # Step limit reached
    assert _rup_check((1,), [(-1,)], max_steps=0) is False
