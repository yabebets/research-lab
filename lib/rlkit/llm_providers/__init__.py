"""rlkit.llm の会社ごとの差（要求の組み立て・送信・応答の読み取り）。

各モジュールは同じ関数を持つ:
    build_body(cfg, *, system, messages, images, tools, max_tokens, effort, params, prompt_cache) -> (body, blobs)
        body は画像を IMAGE_REF（"rl-image:sha256:<hex>"）で参照した形。そのまま記録に残せる
    materialize(body, blobs) -> 送る形（画像の参照を base64 に置き換えたもの）
    make_client(cfg) -> SDK のクライアント
    send(client, body, cfg) -> (raw: dict, request_id)
    parse(raw, cfg) -> dict（text, tool_calls, stop_reason, refusal, usage, model_returned, assistant_message …）
    refusal_from_error(exc) -> dict | None
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import struct
from pathlib import Path

IMAGE_REF = "rl-image:sha256:"

MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif"}


class Blob:
    """1 枚の画像。記録では sha256 で参照し、中身は 1 回だけ保存する。"""

    def __init__(self, data: bytes, media_type: str, path: str | None = None):
        self.data = data
        self.media_type = media_type
        self.path = path
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.size = image_size(data)

    @property
    def ref(self) -> str:
        return IMAGE_REF + self.sha256

    @property
    def ext(self) -> str:
        for ext, mt in MEDIA_TYPES.items():
            if mt == self.media_type and ext != ".jpeg":
                return ext
        return ".bin"

    def b64(self) -> str:
        return base64.standard_b64encode(self.data).decode("ascii")


def load_image(path) -> Blob:
    p = Path(path)
    mt = MEDIA_TYPES.get(p.suffix.lower())
    if mt is None:
        raise ValueError(f"画像の形式が分かりません（png / jpg / webp / gif）: {p}")
    return Blob(p.read_bytes(), mt, str(p))


def image_size(data: bytes) -> tuple[int, int] | None:
    """PNG・JPEG・GIF の幅と高さ。読めなければ None（見積もりでは上限のトークン数を使う）。"""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        w, h = struct.unpack("<HH", data[6:10])
        return w, h
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            seg = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seg
    return None


def collect_blobs(messages, images) -> tuple[list, dict]:
    """images（パス）と、messages の中の {"type": "image", "path": ...} を Blob にする。"""
    blobs: dict[str, Blob] = {}
    top = []
    for x in images or []:
        b = x if isinstance(x, Blob) else load_image(x)
        blobs[b.sha256] = b
        top.append(b)
    for m in messages:
        c = m.get("content")
        if isinstance(c, list):
            for blk in c:
                if isinstance(blk, dict) and blk.get("type") == "image" and "path" in blk:
                    b = load_image(blk["path"])
                    blobs[b.sha256] = b
    return top, blobs


def blob_for_path(blobs: dict, path) -> Blob:
    data = Path(path).read_bytes()
    return blobs[hashlib.sha256(data).hexdigest()]


def replace_refs(obj, fmt):
    """IMAGE_REF で始まる文字列を fmt(sha) に置き換えた深いコピー。"""
    if isinstance(obj, str):
        return fmt(obj[len(IMAGE_REF):]) if obj.startswith(IMAGE_REF) else obj
    if isinstance(obj, list):
        return [replace_refs(x, fmt) for x in obj]
    if isinstance(obj, dict):
        return {k: replace_refs(v, fmt) for k, v in obj.items()}
    return copy.copy(obj)


def first_user_index(messages) -> int | None:
    for i, m in enumerate(messages):
        if m.get("role") == "user":
            return i
    return None


def as_blocks(content) -> list:
    if content is None:
        return []
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return list(content)


def tool_spec(t) -> dict:
    """Tool（dataclass）か dict を {name, description, input_schema} にそろえる。"""
    if isinstance(t, dict):
        return {"name": t["name"], "description": t.get("description", ""),
                "input_schema": t.get("input_schema") or t.get("parameters")}
    return {"name": t.name, "description": t.description, "input_schema": t.input_schema}


def parse_json_args(s):
    if isinstance(s, dict):
        return s, None
    try:
        return json.loads(s or "{}"), None
    except json.JSONDecodeError as e:
        return None, f"道具の引数が JSON として読めません: {e}"
