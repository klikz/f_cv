"""Train subprocess'i: `python -m training.run_train --data ... --out ...` — har epoch JSON qator chiqaradi."""

import argparse
import json
import sys
import time

from training.ml_env import base_weights_dir, setup_ultralytics_env


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)  # project dir
    ap.add_argument("--model", default="n")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--resume", default=None)  # last.pt
    a = ap.parse_args()
    setup_ultralytics_env()
    from ultralytics import YOLO

    t0 = time.time()

    def on_epoch(trainer) -> None:
        m = trainer.metrics or {}
        raw = getattr(trainer, "loss_items", None)
        if raw is None:
            li = []
        elif isinstance(raw, dict):
            li = [float(v) for v in raw.values()]
        elif hasattr(raw, "tolist"):
            li = raw.tolist()
        else:
            li = [float(v) for v in raw]
        li = [float(v) for v in (li if isinstance(li, list) else [li])]
        ep = trainer.epoch + 1
        el = time.time() - t0
        rec = {
            "epoch": ep,
            "epochs": trainer.epochs,
            "elapsed": el,
            "eta": el / ep * (trainer.epochs - ep) if ep else None,
            "box_loss": li[0] if len(li) > 0 else None,
            "cls_loss": li[1] if len(li) > 1 else None,
            "dfl_loss": li[2] if len(li) > 2 else None,
            "precision": m.get("metrics/precision(B)"),
            "recall": m.get("metrics/recall(B)"),
            "map50": m.get("metrics/mAP50(B)"),
            "map5095": m.get("metrics/mAP50-95(B)"),
        }
        print("FCV_EPOCH " + json.dumps(rec), flush=True)

    if a.resume:
        model = YOLO(a.resume)
        model.add_callback("on_fit_epoch_end", on_epoch)
        model.train(resume=True)
    else:
        weights = base_weights_dir() / f"yolo26{a.model}.pt"
        model = YOLO(str(weights))
        model.add_callback("on_fit_epoch_end", on_epoch)
        model.train(
            data=a.data,
            epochs=a.epochs,
            imgsz=a.imgsz,
            batch=a.batch,
            project=a.out,
            name="run",
            exist_ok=True,
            patience=a.patience,
            plots=False,
            workers=4,
            device=0,
            verbose=True,
            cache=False,
            single_cls=True,
            amp=True,
            seed=0,
            deterministic=False,
            save_period=-1,
        )
    best = model.trainer.best
    print("FCV_DONE " + json.dumps({"best": str(best), "seconds": time.time() - t0}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("FCV_ERROR " + json.dumps({"error": f"{e.__class__.__name__}: {e}"}), flush=True)
        raise
    sys.exit(0)
