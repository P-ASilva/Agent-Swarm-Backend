def testDefaultRouterPathReturnsFallbackAgentReply(client, monkeypatch):
    monkeypatch.setenv("ROUTER_MODEL", "")

    response = client.post(
        "/messages",
        json={"message": "What should I do here?", "userId": "client789"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["reply"].startswith("Fallback agent answered:")
