from vision.onvif.client import OnvifProfile, _scope_value, suggest_main_sub


def test_suggest_main_sub():
    ps = [
        OnvifProfile("sub", "Sub", 640, 360, 15, "H264", "rtsp://h/sub"),
        OnvifProfile("main", "Main", 2560, 1440, 25, "H265", "rtsp://h/main"),
        OnvifProfile("third", "3", 1280, 720, 15, "H264", None),
    ]
    assert suggest_main_sub(ps) == ("main", "sub")
    assert suggest_main_sub([ps[1]]) == ("main", None)
    assert suggest_main_sub([]) == (None, None)


def test_scope_parsing():
    scopes = ["onvif://www.onvif.org/hardware/DS-2CD2143", "onvif://www.onvif.org/name/HIKVISION_Camera"]
    assert _scope_value(scopes, "hardware") == "DS-2CD2143"
    assert _scope_value(scopes, "name") == "HIKVISION Camera"
    assert _scope_value(scopes, "mfr") is None
