"""Redis kalitlari va kanallari — bitta joyda (barcha processlar shu nomlardan foydalanadi)."""

P = "fcv:"

# --- pub/sub kanallari ---
CH_CAMERAS = P + "ch:cameras"  # {action: created|updated|deleted, camera_id}
CH_TASKS = P + "ch:tasks"  # {camera_id, task_type} — vazifa sozlamasi o'zgardi
CH_STREAM_STATUS = P + "ch:stream_status"  # {camera_id, kind, status, error}
CH_EVENTS = P + "ch:events"  # UI uchun jonli hodisalar (sanoq, uskuna holati, train...)
CH_SYSTEM = P + "ch:system"  # tizim buyruqlari (inference to'xtatish va h.k.)


def ch_frames(camera_id: int, profile: str) -> str:
    """camera-logic → api: JPEG + metadata (profile: grid | main | analysis)."""
    return f"{P}ch:frames:{camera_id}:{profile}"


CH_FRAMES_PATTERN = P + "ch:frames:*"

# --- Redis Stream (yo'qolmasligi kerak bo'lgan hodisalar: Telegram uchun) ---
STREAM_EVENTS = P + "stream:events"


# --- holatlar ---
def stream_status(camera_id: int, kind: str) -> str:
    return f"{P}streamstat:{camera_id}:{kind}"


def consumer(camera_id: int, kind: str, who: str) -> str:
    """Oqim iste'molchisi (TTL bilan). video-service main oqimni shu asosida ochadi."""
    return f"{P}consumer:{camera_id}:{kind}:{who}"


CONSUMER_PATTERN = P + "consumer:*"


def viewer(camera_id: int, profile: str, client: str) -> str:
    """Brauzerda kimdir ko'rayapti (TTL bilan) — camera-logic JPEG tayyorlaydi."""
    return f"{P}viewer:{camera_id}:{profile}:{client}"


def viewer_pattern(camera_id: int, profile: str) -> str:
    return f"{P}viewer:{camera_id}:{profile}:*"


def ai_vision(camera_id: int) -> str:
    """Grid'da AI Vision yoqilgan (TTL) — grid profilga metadata qo'shiladi."""
    return f"{P}aivision:{camera_id}"


def live_state(camera_id: int) -> str:
    """camera-logic joriy holati (sanoq, uskuna) — hash, UI uchun."""
    return f"{P}live:{camera_id}"


def motion_signal(camera_id: int) -> str:
    return f"{P}signal:{camera_id}"


INFERENCE_PAUSED = P + "inference:paused"  # train paytida o'rnatiladi
INFERENCE_STATS = P + "inference:stats"
INFERENCE_REQ = P + "inference:req"


def inference_resp(camera_id: int) -> str:
    return f"{P}inference:resp:{camera_id}"


TRAIN_QUEUE = P + "train:queue"
TRAIN_CURRENT = P + "train:current"
TRAIN_CANCEL = P + "train:cancel"
TELEGRAM_STATUS = P + "telegram:status"
