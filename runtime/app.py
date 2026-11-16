"""夕语运行时 · 阶段 0：打字 -> 她用自己的声音回答。

启动：双击 run.bat，或 runtime/.venv/Scripts/python.exe app.py
"""

import json
import os
import threading
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

from engine.gptsovits import GPTSoVITS
from engine.guard import Guard
from engine.llm import LLM
from engine.persona import Persona
from engine.tts import TTS

ROOT = Path(__file__).resolve().parent
PERSONA_DIR = ROOT / "persona"
AUDIO_DIR = ROOT / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

cfg = json.loads((PERSONA_DIR / "config.json").read_text(encoding="utf-8"))
persona = Persona(PERSONA_DIR)
guard = Guard(PERSONA_DIR / "guardrails.json")
llm = LLM(cfg["llm"], PERSONA_DIR / "llm-key.txt")
# 声音后端二选一，改 persona/config.json 的 tts.engine 即可切换：
#   "f5-tts"      → 本地零样本克隆（轻，音色相似度有限）
#   "gpt-sovits"  → 微调后的专属模型（需先启动 9880 语音服务）
if cfg["tts"].get("engine") == "gpt-sovits":
    tts = GPTSoVITS(cfg["tts"], persona.voice())
else:
    # f5 的专属参数在 tts.f5 里，合并后再交给 F5 引擎
    tts = TTS({**cfg["tts"], **cfg["tts"].get("f5", {})}, persona.voice())

app = Flask(__name__, static_folder="static", static_url_path="/static")
state = {"history": [], "tts_ready": False, "tts_error": None}


def warmup():
    try:
        tts.load()
        state["tts_ready"] = True
        print("[tts] 模型已加载", flush=True)
    except Exception as e:  # noqa: BLE001
        state["tts_error"] = str(e)[:300]
        print(f"[tts] 加载失败：{e}", flush=True)


def append_memory(user_text, reply, kind="对话"):
    path = PERSONA_DIR / cfg["memory"]["file"].split("/")[-1]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    block = f"\n## {ts}｜{kind}\n- 用户：{user_text}\n- 回应：{reply}\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(block)


def synth(text):
    name = f"{uuid.uuid4().hex[:12]}.wav"
    tts.say(text, AUDIO_DIR / name)
    return f"/audio/{name}"


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/audio/<name>")
def audio(name):
    return send_file(AUDIO_DIR / name, mimetype="audio/wav")


@app.get("/api/status")
def status():
    return jsonify(
        {
            "persona": persona.p["meta"]["name"],
            "build_type": persona.p["meta"]["build_type"],
            "llm_ready": llm.available,
            "llm_model": cfg["llm"]["model"],
            "tts_ready": state["tts_ready"],
            "tts_error": state["tts_error"],
            "notice": persona.p["meta"]["status"],
        }
    )


@app.post("/api/key")
def save_key():
    data = request.get_json(silent=True) or {}
    key = (data.get("key") or "").strip()
    if len(key) < 12:
        return jsonify({"error": "key 看起来不完整，请确认整串都复制上了"}), 400
    try:
        llm.set_key(key)
    except (ValueError, OSError) as e:
        return jsonify({"error": f"保存失败：{e}"}), 500
    # 保存后立刻试一次，让问题当场暴露，而不是等第一句话
    try:
        llm.chat("只回复两个字：可以", [], "测试")
    except RuntimeError as e:
        return jsonify({"ok": True, "llm_ready": True, "warning": str(e)[:300]})
    return jsonify({"ok": True, "llm_ready": True})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "空消息"}), 400

    # 1. 危机：立刻跳出角色，不经过模型
    if guard.crisis(text):
        reply = guard.crisis_script()
        append_memory(text, reply, kind="危机跳出")
        return jsonify({"reply": reply, "crisis": True, "audio": safe_synth(reply), "sources": []})

    # 2. 身份追问：如实承认
    if guard.identity_question(text):
        reply = guard.identity_reply()
        append_memory(text, reply, kind="身份追问")
        return jsonify({"reply": reply, "crisis": False, "audio": safe_synth(reply), "sources": []})

    # 3. 越界话题
    blocked = guard.blocked_topic(text)
    if blocked:
        append_memory(text, blocked, kind="越界拦截")
        return jsonify({"reply": blocked, "crisis": False, "audio": safe_synth(blocked), "sources": []})

    # 4. 正常对话：检索 -> 生成 -> 过滤禁语
    hits = persona.retrieve(text, cfg["retrieval"]["top_k"])
    system = persona.system_prompt(hits)
    try:
        raw = llm.chat(system, state["history"], text)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    reply = guard.scrub(raw) or "……吃饭了没"
    state["history"] += [
        {"role": "user", "content": text},
        {"role": "assistant", "content": reply},
    ]
    append_memory(text, reply)
    return jsonify(
        {
            "reply": reply,
            "crisis": False,
            "audio": safe_synth(reply),
            "sources": [{"id": s["id"], "title": s["title"]} for s in hits],
        }
    )


def safe_synth(text):
    try:
        path = synth(text)
        state["tts_ready"] = True
        return path
    except Exception as e:  # noqa: BLE001
        state["tts_error"] = str(e)[:300]
        print(f"[tts] 合成失败：{e}", flush=True)
        return None


if __name__ == "__main__":
    threading.Thread(target=warmup, daemon=True).start()
    host, port = cfg["server"]["host"], cfg["server"]["port"]
    if cfg["server"].get("open_browser") and not os.environ.get("XIYU_NO_BROWSER"):
        threading.Timer(2.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    print(f"[server] http://{host}:{port}", flush=True)
    app.run(host=host, port=port, threaded=True)
