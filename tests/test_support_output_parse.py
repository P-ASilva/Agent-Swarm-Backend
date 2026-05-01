from __future__ import annotations

import json

from app.modeling.prompts.support.parser import parseSupportModelOutput


def test_parse_support_output_valid_operations():
    raw = json.dumps(
        {
            "assistant_reply": "Feito.",
            "operations": [
                {"kind": "noop", "payload": {}},
                {
                    "kind": "profile_patch",
                    "payload": {
                        "display_name": "Jo",
                        "profile_metadata": {"locale": "pt-BR"},
                    },
                },
            ],
        }
    )
    out = parseSupportModelOutput(raw)
    assert out.assistantReply == "Feito."
    assert len(out.operations) == 2
    assert out.operations[0].kind == "noop"
    assert out.operations[1].payload["display_name"] == "Jo"


def test_parse_support_output_strips_owner_keys():
    raw = json.dumps(
        {
            "assistant_reply": "ok",
            "operations": [
                {
                    "kind": "profile_patch",
                    "payload": {
                        "display_name": "X",
                        "conversation_owner_key": "guest:evil",
                    },
                }
            ],
        }
    )
    out = parseSupportModelOutput(raw)
    assert "conversation_owner_key" not in out.operations[0].payload


def test_parse_support_output_invalid_json():
    out = parseSupportModelOutput("{")
    assert "Tente novamente" in out.assistantReply
    assert out.operations == ()
