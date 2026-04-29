from tests.helpers.apiOverrides import FakeMessageUseCase, installMessageUseCaseOverride


def testPostMessagesReturnsServiceUnavailableWhenDependencyFails(app, client, messagePayload):
    fakeUseCase = FakeMessageUseCase(
        response={},
        error=RuntimeError("dependency unavailable"),
    )
    installMessageUseCaseOverride(app, fakeUseCase)

    response = client.post("/messages", json=messagePayload)

    assert response.status_code == 503
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


def testPostMessagesReturnsGatewayTimeoutOnTimeoutError(app, client, messagePayload):
    fakeUseCase = FakeMessageUseCase(
        response={},
        error=TimeoutError("timeout while calling downstream dependency"),
    )
    installMessageUseCaseOverride(app, fakeUseCase)

    response = client.post("/messages", json=messagePayload)

    assert response.status_code == 504
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


def testPostMessagesSupportsDegradedResponseShape(app, client, messagePayload):
    fakeUseCase = FakeMessageUseCase(
        response={
            "status": "degraded",
            "reply": "Temporary issue, please try again shortly.",
            "traceId": "trace-degraded",
        }
    )
    installMessageUseCaseOverride(app, fakeUseCase)

    response = client.post("/messages", json=messagePayload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["reply"]
    assert body["traceId"]
