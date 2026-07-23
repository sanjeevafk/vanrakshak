from app.edge_pipeline import EdgeInferencePipeline


def test_edge_pipeline_buffer_and_drop_stale():
    pipeline = EdgeInferencePipeline(max_buffer_size=2)
    assert not pipeline.push_frame(b"frame_1")

    pipeline.start()
    assert pipeline.push_frame(b"frame_1")
    assert pipeline.push_frame(b"frame_2")
    assert pipeline.push_frame(b"frame_3")

    assert pipeline.pop_frame() == b"frame_3"
    pipeline.stop()
    assert not pipeline.push_frame(b"frame_4")

def test_configured_buffer_size_is_honored():
    pipeline = EdgeInferencePipeline(max_buffer_size=1)
    pipeline.start(); pipeline.push_frame(b"one"); pipeline.push_frame(b"two")
    assert pipeline.pop_frame() == b"two"
