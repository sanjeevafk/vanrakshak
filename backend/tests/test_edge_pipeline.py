from app.edge_pipeline import EdgeInferencePipeline


def test_edge_pipeline_buffer_and_drop_stale():
    pipeline = EdgeInferencePipeline(max_buffer_size=2)
    assert not pipeline.push_frame(b"frame_1")

    pipeline.start()
    assert pipeline.push_frame(b"frame_1")
    assert pipeline.push_frame(b"frame_2")
    assert pipeline.push_frame(b"frame_3")

    # Should return newest non-stale frame
    frame = pipeline.pop_frame()
    assert frame in {b"frame_2", b"frame_3"}
    pipeline.stop()
    assert not pipeline.push_frame(b"frame_4")
