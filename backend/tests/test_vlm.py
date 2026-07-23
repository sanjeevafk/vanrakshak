import asyncio
from app.vlm import VLMAdapter

def test_valid_and_markdown_json_parse():
    async def request(_): return '```json\n{"scene_summary":"person","vlm_confidence":0.8}\n```'
    result = asyncio.run(VLMAdapter(request=request).analyze(track_id=1, crop=b"a", artifact_ref="a1", evidence_id="e1"))
    assert result.confidence == .8 and result.fallback_reason is None

def test_invalid_response_falls_back_without_secret():
    async def request(_): return "not json"
    result = asyncio.run(VLMAdapter(request=request).analyze(track_id=1, crop=b"a", artifact_ref="a1", evidence_id="e1"))
    assert result.fallback_reason == "INVALID_PROVIDER_RESPONSE"
    assert "api" not in result.model.lower()

def test_cache_and_track_limit():
    calls = 0
    async def request(_):
        nonlocal calls
        calls += 1
        return '{"vlm_confidence":0.7}'
    async def run():
        adapter = VLMAdapter(request=request, max_calls_per_track=3)
        for i in range(4):
            result = await adapter.analyze(track_id=1, crop=f"{i}".encode(), artifact_ref=f"a{i}", evidence_id=f"e{i}")
        cached = await adapter.analyze(track_id=1, crop=b"0", artifact_ref="a0", evidence_id="cached")
        return result, cached
    result, cached = asyncio.run(run())
    assert result.fallback_reason == "CALL_LIMIT"
    assert cached.confidence == .7
    assert calls == 3

def test_timeout_falls_back():
    async def request(_):
        await asyncio.sleep(.05)
        return '{"vlm_confidence":1}'
    result = asyncio.run(VLMAdapter(request=request, timeout_seconds=.001).analyze(track_id=1, crop=b"a", artifact_ref="a", evidence_id="e"))
    assert result.fallback_reason == "TIMEOUT"
