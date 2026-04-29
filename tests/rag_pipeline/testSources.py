import json

from app.rag_pipeline.sources import (
    computeSeedManifestHash,
    extractSeedUrlsFromChallengeContext,
    loadSeedUrls,
)


def testExtractSeedUrlsFromChallengeContextExtractsAnyDomain():
    context = """
    Useful:
    https://www.infinitepay.io
    https://www.infinitepay.io/pix
    https://example.com/hello
    Ignore:
    https://www.infinitepay.io/pix#section
    """
    urls = extractSeedUrlsFromChallengeContext(context)

    assert urls == [
        "https://www.infinitepay.io/",
        "https://www.infinitepay.io/pix",
        "https://example.com/hello",
    ]


def testComputeSeedManifestHashIsDeterministicIndependentOfOrder():
    first = ["https://www.infinitepay.io/pix", "https://www.infinitepay.io/"]
    second = ["https://www.infinitepay.io/", "https://www.infinitepay.io/pix"]

    assert computeSeedManifestHash(first) == computeSeedManifestHash(second)


def testLoadSeedUrlsReadsJsonManifest(tmp_path):
    manifest = tmp_path / "seedUrls.json"
    payload = {
        "urls": [
            "https://www.infinitepay.io/pix",
            "https://www.infinitepay.io/pix#faq",
            "https://www.infinitepay.io/maquininha",
        ]
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    urls = loadSeedUrls(manifestPath=manifest, contextPath=None)

    assert urls == [
        "https://www.infinitepay.io/pix",
        "https://www.infinitepay.io/maquininha",
    ]


def testLoadSeedUrlsRaisesWhenNoInputSourceExists():
    try:
        loadSeedUrls(manifestPath="does-not-exist.json", contextPath=None)
        raise AssertionError("Expected FileNotFoundError when seed manifest is missing.")
    except FileNotFoundError:
        pass
