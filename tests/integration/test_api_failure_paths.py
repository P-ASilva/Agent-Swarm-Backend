from tests.helpers.api_overrides import FakeMessageUseCase, install_message_use_case_override


def test_post_messages_returns_service_unavailable_when_dependency_fails(
    app, client, message_payload
):
    fake_use_case = FakeMessageUseCase(
        response={},
        error=RuntimeError("dependency unavailable"),
    )
    install_message_use_case_override(app, fake_use_case)

    response = client.post("/messages", json=message_payload)

    assert response.status_code == 503
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


def test_post_messages_returns_gateway_timeout_on_timeout_error(
    app, client, message_payload
):
    fake_use_case = FakeMessageUseCase(
        response={},
        error=TimeoutError("timeout while calling downstream dependency"),
    )
    install_message_use_case_override(app, fake_use_case)

    response = client.post("/messages", json=message_payload)

    assert response.status_code == 504
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


def test_post_messages_supports_degraded_response_shape(app, client, message_payload):
    fake_use_case = FakeMessageUseCase(
        response={
            "status": "degraded",
            "reply": "Temporary issue, please try again shortly.",
            "trace_id": "trace-degraded",
        }
    )
    install_message_use_case_override(app, fake_use_case)

    response = client.post("/messages", json=message_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["reply"]
    assert body["trace_id"]
