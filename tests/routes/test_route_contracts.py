import pytest


def test_post_messages_success_returns_response_envelope(client, message_payload):
    response = client.post("/messages", json=message_payload)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert set(["status", "reply", "trace_id"]).issubset(data.keys())
    assert isinstance(data["status"], str)
    assert isinstance(data["reply"], str)
    assert isinstance(data["trace_id"], str)


@pytest.mark.parametrize(
    "payload",
    [
        {"user_id": "client789"},
        {"message": "hello"},
        {"message": "", "user_id": "client789"},
        {"message": "hello", "user_id": ""},
        {},
    ],
)
def test_post_messages_rejects_invalid_payload(client, payload):
    response = client.post("/messages", json=payload)

    assert response.status_code == 422


def test_get_health_returns_stable_payload(client):
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "status" in data
    assert isinstance(data["status"], str)


def test_docs_endpoint_is_available(client):
    response = client.get("/docs")

    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type
