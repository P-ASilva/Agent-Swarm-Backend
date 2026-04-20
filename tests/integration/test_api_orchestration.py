from tests.helpers.api_overrides import FakeMessageUseCase, install_message_use_case_override


def test_post_messages_calls_use_case_and_returns_normalized_payload(app, client, message_payload):
    fake_use_case = FakeMessageUseCase(
        response={"status": "ok", "reply": "mocked-reply", "trace_id": "trace-123"}
    )
    install_message_use_case_override(app, fake_use_case)

    response = client.post("/messages", json=message_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["reply"] == "mocked-reply"
    assert body["trace_id"] == "trace-123"

    assert len(fake_use_case.calls) == 1
    call_repr = repr(fake_use_case.calls[0])
    assert message_payload["message"] in call_repr
    assert message_payload["user_id"] in call_repr


def test_post_messages_response_envelope_hides_internal_fields(app, client, message_payload):
    fake_use_case = FakeMessageUseCase(
        response={
            "status": "ok",
            "reply": "hello",
            "trace_id": "trace-456",
            "internal_debug": "do-not-expose",
        }
    )
    install_message_use_case_override(app, fake_use_case)

    response = client.post("/messages", json=message_payload)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"status", "reply", "trace_id"}
