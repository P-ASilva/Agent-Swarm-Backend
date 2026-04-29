import pytest


def testPostMessagesSuccessReturnsResponseEnvelope(client, messagePayload):
    response = client.post("/messages", json=messagePayload)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert set(["status", "reply", "traceId"]).issubset(data.keys())
    assert isinstance(data["status"], str)
    assert isinstance(data["reply"], str)
    assert isinstance(data["traceId"], str)


@pytest.mark.parametrize(
    "payload",
    [
        {"userId": "client789"},
        {"message": "hello"},
        {"message": "", "userId": "client789"},
        {"message": "hello", "userId": ""},
        {},
    ],
)
def testPostMessagesRejectsInvalidPayload(client, payload):
    response = client.post("/messages", json=payload)

    assert response.status_code == 422


def testGetHealthReturnsStablePayload(client):
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "status" in data
    assert isinstance(data["status"], str)


def testDocsEndpointIsAvailable(client):
    response = client.get("/docs")

    assert response.status_code == 200
    contentType = response.headers.get("content-type", "")
    assert "text/html" in contentType
