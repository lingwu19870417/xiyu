"""护栏：危机识别、身份追问、禁语过滤。由 guardrails.json 驱动，不写死在代码里。"""

import json
import re
from pathlib import Path


class Guard:
    def __init__(self, path):
        self.d = json.loads(Path(path).read_text(encoding="utf-8"))

    def crisis(self, text):
        t = (text or "").replace(" ", "").lower()
        return any(k in t for k in self.d["crisis"]["keywords"])

    def crisis_script(self):
        return self.d["crisis"]["script"]

    def identity_question(self, text):
        t = (text or "").replace(" ", "").lower()
        return any(k.replace(" ", "") in t for k in self.d["ai_disclosure"]["keywords"])

    def identity_reply(self):
        return self.d["ai_disclosure"]["on_identity_question"]

    def blocked_topic(self, text):
        t = (text or "").replace(" ", "")
        for topic in self.d["boundaries"]["blocked_topics"]:
            if topic in t:
                return self.d["boundaries"]["blocked_response"]
        return None

    def scrub(self, text):
        """删掉禁语；删空了的句子整句丢弃。"""
        out = []
        for sent in re.split(r"(?<=[。！？!?])", text or ""):
            hit = any(p in sent for p in self.d["language"]["forbidden_patterns"])
            if hit:
                continue
            out.append(sent)
        cleaned = "".join(out).strip()
        return cleaned
