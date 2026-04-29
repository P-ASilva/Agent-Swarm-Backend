from app.rag_pipeline.chunk import DeterministicChunker


def testDeterministicChunkerGeneratesStableHashes():
    text = " ".join(f"word{index}" for index in range(200))
    chunker = DeterministicChunker(chunkSize=120, overlap=30)

    first = chunker.chunkText(text)
    second = chunker.chunkText(text)

    assert len(first) > 1
    assert [chunk.chunkHash for chunk in first] == [chunk.chunkHash for chunk in second]


def testDeterministicChunkerAppliesOverlapToNeighborChunks():
    text = " ".join(f"token{index}" for index in range(100))
    chunker = DeterministicChunker(chunkSize=80, overlap=20)
    chunks = chunker.chunkText(text)

    assert len(chunks) > 1
    assert chunks[1].text.split(" ")[0] in chunks[0].text
