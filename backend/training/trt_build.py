"""ONNX (FP16) → TensorRT engine (dinamik batch), ultralytics bilan mos fayl formatida.

TensorRT 11 faqat "strongly-typed" tarmoqlarni qo'llaydi: FP16 aniqlik ONNX grafning o'zida bo'ladi
(ultralytics `half=True` bilan GPU'da eksport). Ultralytics'ning o'zi bu holatda nvidia-modelopt talab qiladi —
undan qochish uchun engine'ni shu yerda quramiz. Fayl formati: [4 bayt LE uzunlik][metadata JSON][engine].
"""

from __future__ import annotations

import json
from pathlib import Path


def onnx_metadata(onnx_path: Path) -> dict:
    from ultralytics.nn.backends.base import BaseBackend

    meta = BaseBackend.read_metadata(onnx_path)
    return {k: v for k, v in meta.items()}


def build_engine(
    onnx_path: Path, out_path: Path, *, imgsz: int = 640, max_batch: int = 8, workspace_gb: float = 2.0
) -> dict:
    import tensorrt as trt

    logger = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(logger)
    major = int(trt.__version__.split(".")[0])
    flags = 0
    if major < 10:
        flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
    elif hasattr(trt.NetworkDefinitionCreationFlag, "STRONGLY_TYPED") and major == 10:
        flags = 1 << int(trt.NetworkDefinitionCreationFlag.STRONGLY_TYPED)
    network = builder.create_network(flags)
    parser = trt.OnnxParser(network, logger)
    if not parser.parse_from_file(str(onnx_path)):
        errs = "; ".join(str(parser.get_error(i)) for i in range(parser.num_errors))
        raise RuntimeError(f"ONNX o'qilmadi: {errs}")
    config = builder.create_builder_config()
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, int(workspace_gb * (1 << 30)))
    inp = network.get_input(0)
    profile = builder.create_optimization_profile()
    mx = (imgsz * 5 // 4 + 31) // 32 * 32  # rect letterbox (val) uchun zaxira
    profile.set_shape(inp.name, (1, 3, 32, 32), (max(1, max_batch // 2), 3, imgsz, imgsz), (max_batch, 3, mx, mx))
    config.add_optimization_profile(profile)
    serialized = builder.build_serialized_network(network, config)
    if serialized is None:
        raise RuntimeError("TensorRT engine qurilmadi")
    meta = onnx_metadata(onnx_path)
    meta.update({"batch": max_batch, "dynamic": True})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".building")
    with open(tmp, "wb") as f:
        m = json.dumps(meta, default=str).encode()
        f.write(len(m).to_bytes(4, byteorder="little", signed=True))
        f.write(m)
        f.write(bytes(serialized))
        f.flush()
        import os

        os.fsync(f.fileno())
    tmp.replace(out_path)
    return meta
