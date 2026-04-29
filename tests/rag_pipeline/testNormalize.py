from app.rag_pipeline.normalize import canonicalizeUrl, extractTitleAndText


def testCanonicalizeUrlDropsQueryAndFragment():
    canonical = canonicalizeUrl("https://www.infinitepay.io/pix/?utm_source=test#overview")
    assert canonical == "https://www.infinitepay.io/pix"


def testExtractTitleAndTextRemovesScriptNoise():
    html = """
    <html>
      <head><title>Infinitepay Pix</title></head>
      <body>
        <script>console.log('ignore')</script>
        <h1>Pix</h1>
        <p>Receive instantly.</p>
      </body>
    </html>
    """
    title, text = extractTitleAndText(html)

    assert title == "Infinitepay Pix"
    assert "Receive instantly." in text
    assert "console.log" not in text
