"""对话模型：任何 OpenAI 兼容接口都能接（智谱 / DeepSeek / 阿里百炼 / 本地 Ollama）。"""

import json
import os
import urllib.error
import urllib.request


class LLM:
    def __init__(self, cfg, key_file=None):
        self.cfg = cfg
        self.key_file = key_file
        # 允许用环境变量临时覆盖，方便切换到本地模型或其他服务
        self.base = (os.environ.get("XIYU_BASE_URL") or cfg["base_url"]).rstrip("/")
        self.model = os.environ.get("XIYU_MODEL") or cfg["model"]
        # key 的读取顺序：环境变量 > 本地 key 文件（网页里粘贴保存的）
        self.key = os.environ.get(cfg.get("api_key_env", "XIYU_API_KEY"), "").strip()
        if not self.key and key_file and key_file.exists():
            self.key = key_file.read_text(encoding="utf-8").strip()

    @property
    def available(self):
        return bool(self.key)

    def set_key(self, key):
        """保存 key：写本地文件，下次启动自动读取。"""
        key = (key or "").strip()
        if not key:
            raise ValueError("key 为空")
        self.key = key
        if self.key_file:
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            self.key_file.write_text(key, encoding="utf-8")

    def chat(self, system, history, user_text):
        if not self.available:
            raise RuntimeError(
                "还没有配置对话模型的 key。在网页上方的输入框里粘贴保存即可。"
            )
        msgs = [{"role": "system", "content": system}]
        msgs += history[-6:]
        msgs.append({"role": "user", "content": user_text})
        payload = {
            "model": self.model,
            "messages": msgs,
            "temperature": self.cfg.get("temperature", 0.85),
            "max_tokens": self.cfg.get("max_tokens", 160),
            "stream": False,
        }
        req = urllib.request.Request(
            self.base + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.get("timeout", 30)) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            raise RuntimeError(f"模型接口返回 {e.code}：{detail}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"连不上模型接口：{e.reason}")
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError):
            raise RuntimeError(f"返回格式不符合预期：{str(data)[:200]}")
