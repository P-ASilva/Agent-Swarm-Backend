from tests.helpers.apiOverrides import FakeMessageUseCase, installMessageUseCaseOverride


def testPostMessagesCallsUseCaseAndReturnsNormalizedPayload(app, client, messagePayload):
    fakeUseCase = FakeMessageUseCase(
        response={"status": "ok", "reply": "mocked-reply", "traceId": "trace-123"}
    )
    installMessageUseCaseOverride(app, fakeUseCase)

    response = client.post("/messages", json=messagePayload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["reply"] == "mocked-reply"
    assert body["traceId"] == "trace-123"

    assert len(fakeUseCase.calls) == 1
    callRepr = repr(fakeUseCase.calls[0])
    assert messagePayload["message"] in callRepr
    assert messagePayload["userId"] in callRepr


def testPostMessagesResponseEnvelopeHidesInternalFields(app, client, messagePayload):
    fakeUseCase = FakeMessageUseCase(
        response={
            "status": "ok",
            "reply": "hello",
            "traceId": "trace-456",
            "internalDebug": "do-not-expose",
        }
    )
    installMessageUseCaseOverride(app, fakeUseCase)

    response = client.post("/messages", json=messagePayload)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"status", "reply", "traceId"}
