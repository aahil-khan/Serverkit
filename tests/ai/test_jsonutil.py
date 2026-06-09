"""Tests for JSON extraction from model output."""

from __future__ import annotations

from serverkit.ai.jsonutil import extract_first_json_object, parse_model_json


def test_extract_first_object_nested():
    blob = 'prefix {"resource": "processes", "filters": [{"action": "cpu_above", "value": 10}]} trailing'
    ex = extract_first_json_object(blob)
    assert ex is not None
    assert parse_model_json(blob) == {
        "resource": "processes",
        "filters": [{"action": "cpu_above", "value": 10}],
    }


def test_parse_strips_line_comments():
    raw = """{
  "schema_version": 2,
  "name": "wf",
  "created_at": null,
  "last_run": null,
  "steps": [
    { "type": "process_filter", "memory_above": 500, // comment
      "cpu_above": null, "named": null },
    { "type": "summary" }
  ]
}"""
    data = parse_model_json(raw)
    assert data is not None
    assert data["name"] == "wf"
    assert len(data["steps"]) == 2


def test_parse_prefers_first_balanced_object_not_rfind_garbage():
    """Avoid rfind('}') swallowing hallucinated trailing objects."""
    raw = """{"resource": "processes", "filters": [{"action": "cpu_above", "value": 10}]}
    then garbage { "_id" : "x" }"""
    data = parse_model_json(raw)
    assert data == {
        "resource": "processes",
        "filters": [{"action": "cpu_above", "value": 10}],
    }
