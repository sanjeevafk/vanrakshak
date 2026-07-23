from app.hardware import MAVLinkAutopilotAdapter


def test_mavlink_connect_and_dispatch():
    adapter = MAVLinkAutopilotAdapter()
    assert not adapter.is_connected()

    res_conn = adapter.connect("udp://:14540")
    assert res_conn is True
    assert adapter.is_connected()

    action = adapter.dispatch_action("RETURN_TO_BASE", payload={"lat": 12.97, "lon": 77.59})
    assert action["mavlink_cmd"] == "MAV_CMD_NAV_RETURN_TO_LAUNCH"
    assert action["mavlink_status"] == "SENT"
    assert len(adapter.dispatched_actions) == 1


def test_mavlink_siren_and_gimbal_actions():
    adapter = MAVLinkAutopilotAdapter()
    siren = adapter.dispatch_action("SIREN_ACTIVATE")
    gimbal = adapter.dispatch_action("GIMBAL_LOCK", payload={"pitch": -45, "yaw": 120})

    assert siren["mavlink_cmd"] == "MAV_CMD_PAYLOAD_PREPARE_DEPLOY"
    assert gimbal["mavlink_cmd"] == "MAV_CMD_DO_MOUNT_CONTROL"
    assert len(adapter.dispatched_actions) == 2
