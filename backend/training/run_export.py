"""TensorRT eksport subprocess'i: FP16, dinamik batch; engine va .pt ni val to'plamida solishtiradi."""

import argparse
import json
import time
from pathlib import Path

from training.ml_env import setup_ultralytics_env, versions


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pt", required=True)
    ap.add_argument("--engine-out", required=True)
    ap.add_argument("--data", default=None)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=8)
    a = ap.parse_args()
    setup_ultralytics_env()
    from ultralytics import YOLO

    from training.trt_build import build_engine

    t0 = time.time()
    out = Path(a.engine_out)
    model = YOLO(a.pt)
    onnx_path = Path(
        model.export(
            format="onnx", half=True, dynamic=True, batch=a.batch, imgsz=a.imgsz, device=0, simplify=True, verbose=False
        )
    )
    build_engine(onnx_path, out, imgsz=a.imgsz, max_batch=a.batch)
    onnx_path.unlink(missing_ok=True)
    build_sec = time.time() - t0
    res = {"engine": str(out), "build_seconds": build_sec, **versions()}
    if a.data:
        try:
            m_pt = YOLO(a.pt).val(data=a.data, imgsz=a.imgsz, batch=8, device=0, plots=False, verbose=False)
            m_en = YOLO(str(out), task="detect").val(
                data=a.data, imgsz=a.imgsz, batch=1, device=0, plots=False, verbose=False
            )
            res["pt_map50"] = float(m_pt.box.map50)
            res["engine_map50"] = float(m_en.box.map50)
            res["pt_map5095"] = float(m_pt.box.map)
            res["engine_map5095"] = float(m_en.box.map)
        except Exception as e:
            res["val_error"] = str(e)
    (out.parent / "meta.json").write_text(json.dumps(res, indent=2))
    print("FCV_EXPORT " + json.dumps(res), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("FCV_ERROR " + json.dumps({"error": f"{e.__class__.__name__}: {e}"}), flush=True)
        raise
