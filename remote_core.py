from typing import List, Tuple


def build_message(action: str, payload: str) -> bytes:
    return f"{action}:{payload}\n".encode("utf-8")


def parse_messages(buffer: bytes) -> List[Tuple[str, str]]:
    text = buffer.decode("utf-8", errors="ignore")
    messages = []
    for line in text.splitlines():
        if not line:
            continue
        if ":" not in line:
            messages.append(("TEXT", line))
            continue
        action, payload = line.split(":", 1)
        messages.append((action.strip(), payload.strip()))
    return messages


def is_valid_port(port: str) -> bool:
    try:
        value = int(port)
    except ValueError:
        return False
    return 1 <= value <= 65535


def normalize_host(host: str) -> str:
    host = host.strip()
    if not host:
        return "0.0.0.0"
    return host


def quality_to_scale(quality: str) -> float:
    normalized = (quality or "balanced").lower()
    mapping = {
        "low": 0.6,
        "balanced": 0.8,
        "high": 1.0,
        "ultra": 1.0,
        "auto": 0.8,
    }
    return mapping.get(normalized, 0.8)


def get_resolution(size, scale: float):
    width, height = size
    if scale <= 0:
        scale = 0.8
    return (max(240, int(width * scale)), max(160, int(height * scale)))
