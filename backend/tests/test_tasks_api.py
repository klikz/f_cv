async def _cam(client, sub=True):
    body = {"name": "K", "main_rtsp_url": "rtsp://h/main"}
    if sub:
        body["sub_rtsp_url"] = "rtsp://h/sub"
    return (await client.post("/api/cameras", json=body)).json()["id"]


async def test_tasks_flow(client):
    cid = await _cam(client)
    t = (await client.get(f"/api/cameras/{cid}/tasks")).json()
    assert t["analysis_stream"] == "main" and not t["tasks"]["counting"]["enabled"]
    assert t["tasks"]["counting"]["issues"] == ["ROI hududi chizilmagan"]
    t = (await client.put(f"/api/cameras/{cid}/tasks/counting", json={"enabled": True})).json()
    assert t["tasks"]["counting"]["enabled"] and not t["tasks"]["counting"]["configured"]

    cfg = {"roi_polygon": [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9]], "line": [[0.5, 0.1], [0.5, 0.9]], "direction": "both"}
    r = await client.put(f"/api/cameras/{cid}/counting", json=cfg)
    assert r.status_code == 200 and r.json()["direction"] == "both"
    t = (await client.get(f"/api/cameras/{cid}/tasks")).json()
    assert t["tasks"]["counting"]["configured"] and t["tasks"]["counting"]["issues"] == []

    # tahlil oqimini almashtirish — shakllar tozalanadi
    t = (await client.post(f"/api/cameras/{cid}/analysis-stream", json={"stream": "sub"})).json()
    assert t["analysis_stream"] == "sub"
    c = (await client.get(f"/api/cameras/{cid}/counting")).json()
    assert c["roi_polygon"] is None and c["line"] is None and c["stream"] == "sub"


async def test_validation(client):
    cid = await _cam(client, sub=False)
    bad = [
        {"roi_polygon": [[0.1, 0.1], [0.2, 0.2]]},
        {"roi_polygon": [[0.1, 0.1], [1.2, 0.2], [0.3, 0.3]]},
        {"line": [[0.5, 0.5], [0.505, 0.5]]},
        {"inference_fps": 50},
    ]
    for b in bad:
        assert (await client.put(f"/api/cameras/{cid}/counting", json=b)).status_code == 422, b
    r = await client.post(f"/api/cameras/{cid}/analysis-stream", json={"stream": "sub"})
    assert r.status_code == 422
    r = await client.put(f"/api/cameras/{cid}/equipment", json={"home_exit_threshold": 5, "home_return_threshold": 8})
    assert r.status_code == 422
    r = await client.put(
        f"/api/cameras/{cid}/equipment",
        json={"roi_polygon": [[0, 0], [1, 0], [1, 1]], "exclude_zones": [[[0.1, 0.1], [0.2, 0.1], [0.2, 0.2]]]},
    )
    assert r.status_code == 200 and len(r.json()["exclude_zones"]) == 1
