import json

from app.core import keys
from app.services.cameras import unmask

CAM = {
    "name": "Liniya-1",
    "main_rtsp_url": "rtsp://admin:p%40ss@10.0.0.5:554/main",
    "sub_rtsp_url": "rtsp://admin:p%40ss@10.0.0.5:554/sub",
}


async def test_crud_and_masking(client, redis):
    ps = redis.pubsub()
    await ps.subscribe(keys.CH_CAMERAS)
    r = await client.post("/api/cameras", json=CAM)
    assert r.status_code == 201, r.text
    cam = r.json()
    assert cam["main_rtsp_url"] == "rtsp://admin:•••@10.0.0.5:554/main"
    assert cam["analysis_stream"] == "main"
    assert [s["kind"] for s in cam["streams"]] == ["main", "sub"]

    msg = None
    for _ in range(20):
        msg = await ps.get_message(ignore_subscribe_messages=True, timeout=0.2)
        if msg:
            break
    assert msg and json.loads(msg["data"]) == {"action": "created", "camera_id": cam["id"]}

    # maskalangan manzil qaytsa — parol saqlanadi
    r = await client.patch(f"/api/cameras/{cam['id']}", json={"name": "Yangi", "main_rtsp_url": cam["main_rtsp_url"]})
    assert r.status_code == 200
    from app.core.db import get_sessionmaker
    from app.models.cameras import Camera

    async with get_sessionmaker()() as s:
        row = await s.get(Camera, cam["id"])
        assert row.main_rtsp_url == CAM["main_rtsp_url"]
        assert row.name == "Yangi"

    # sub ni olib tashlash
    r = await client.patch(f"/api/cameras/{cam['id']}", json={"clear_sub": True})
    assert r.json()["sub_rtsp_url"] is None
    assert [s["kind"] for s in r.json()["streams"]] == ["main"]

    assert (await client.get("/api/cameras")).json()[0]["name"] == "Yangi"
    assert (await client.delete(f"/api/cameras/{cam['id']}")).status_code == 204
    assert (await client.get(f"/api/cameras/{cam['id']}")).status_code == 404
    await ps.aclose()


async def test_validation(client):
    r = await client.post("/api/cameras", json={"name": "x", "main_rtsp_url": "ftp://a"})
    assert r.status_code == 422
    r = await client.post("/api/cameras", json={"name": "", "main_rtsp_url": "rtsp://a/b"})
    assert r.status_code == 422


async def test_reorder(client):
    ids = []
    for i in range(3):
        ids.append(
            (await client.post("/api/cameras", json={"name": f"K{i}", "main_rtsp_url": f"rtsp://h/{i}"})).json()["id"]
        )
    await client.post("/api/cameras/reorder", json={"ids": list(reversed(ids))})
    assert [c["id"] for c in (await client.get("/api/cameras")).json()] == list(reversed(ids))


async def test_probe_bad_url(client):
    r = await client.post("/api/cameras/probe", json={"url": "rtsp://127.0.0.1:1/none"})
    assert r.status_code == 200
    assert r.json()["ok"] is False and "rad etdi" in r.json()["error"]


def test_unmask():
    assert unmask("rtsp://u:•••@h/x", "rtsp://u:secret@h/x") == "rtsp://u:secret@h/x"
    assert unmask("rtsp://u:new@h/x", "rtsp://u:secret@h/x") == "rtsp://u:new@h/x"
    assert unmask("rtsp://h/x", "rtsp://u:secret@h/x") == "rtsp://h/x"
