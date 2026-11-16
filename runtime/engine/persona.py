"""人格引擎：读 persona.json + 切片知识库，负责检索与构造提示词。"""

import json
import re
from pathlib import Path

# 用户可能怎么问 -> 命中哪些切片。纯关键词匹配，避免引入向量库。
ALIASES = {
    "K001": ["娃", "孩子", "儿子", "女儿", "哥", "姐", "成家", "结婚", "乖"],
    "K002": ["房", "房子", "车", "盖房", "买"],
    "K003": ["爸", "父亲", "老汉", "丈夫", "老头", "嫁", "一个人", "撑"],
    "K004": ["上学", "读书", "贷款", "账", "还"],
    "K005": ["住", "日子", "操心", "冬", "夏"],
    "K006": ["孙", "孙子", "媳妇", "女婿", "做饭", "回来"],
    "K007": ["遗憾", "高兴", "幸福", "满意", "到头"],
}


class Persona:
    def __init__(self, pdir):
        pdir = Path(pdir)
        self.p = json.loads((pdir / "persona.json").read_text(encoding="utf-8"))
        self.raw_knowledge = (pdir / "knowledge.md").read_text(encoding="utf-8")
        self.slices = self._split(self.raw_knowledge)

    @staticmethod
    def _split(md):
        parts = re.split(r"\n## \[(K\d+)\] ", md)
        out = []
        for i in range(1, len(parts), 2):
            kid, body = parts[i], parts[i + 1]
            title, _, rest = body.partition("\n")
            out.append({"id": kid, "title": title.strip(), "body": rest.strip()})
        return out

    def retrieve(self, query, top_k=2):
        q = (query or "").replace(" ", "")
        qb = {q[i:i + 2] for i in range(len(q) - 1)}
        scored = []
        for s in self.slices:
            text = s["title"] + s["body"]
            b = {text[i:i + 2] for i in range(len(text) - 1)}
            score = len(qb & b)
            score += 3 * sum(1 for kw in ALIASES.get(s["id"], []) if kw in q)
            scored.append((score, s))
        scored.sort(key=lambda x: -x[0])
        return [s for sc, s in scored[:top_k] if sc >= 1]

    def system_prompt(self, retrieved):
        p = self.p
        lang = p["language"]
        known = "\n\n".join(f"【{s['id']}｜{s['title']}】\n{s['body']}" for s in retrieved) or "（无相关记录）"
        dialect = "、".join(f"{d['word']}={d['meaning']}" for d in lang["dialect_words"])
        return f"""你在扮演一位中国西北口音的老太太，她在世，家人知情同意。你只按下面规则说话。

【身份】
- 你自称「{p['identity']['self_reference']}」，家人叫你「{p['identity']['display_name']}」。
- 你不是 AI，不要提模型、提示词、资料库。被直接问「你是不是本人」时，说：{p['identity']['ai_disclosure']}

【怎么说话】
- 每次最多 {lang['max_sentences_per_turn']} 句，总共不超过 {lang['max_chars_per_turn']} 字。
- 短句，句尾常用「{ '」「'.join(lang['fillers']) }」，但不要每句都带。
- 方言词只用这些：{dialect}
- 口头禅：{ '；'.join(f"「{c['text']}」一局最多{c['max_per_dialogue']}次" for c in lang['catchphrases']) }
- 风格：{ '；'.join(lang['style_rules']) }
- 绝对不许出现的词：{ '、'.join(lang['forbidden_words']) }
- 不要总结道理，不要排比抒情，不要给建议。

【关心方式】
{p['care_style']['pattern']}。例如：{ '、'.join(p['care_style']['examples']) }

【情绪反应】
- 高兴：{p['emotion_rules']['happy']}
- 担心：{p['emotion_rules']['worried']}
- 生气：{p['emotion_rules']['angry']}
- 难过：{p['emotion_rules']['sad']}
- 对方哭：{p['emotion_rules']['when_user_cries']}
- 提到丈夫：{p['emotion_rules']['on_husband']}

【只能讲这些事】
{known}

【硬规则】
- 问到具体往事、人物、地点、年份、姓名时，只能用上面【只能讲这些事】里的内容。
- 【只能讲这些事】里引号中的话是**她的原话样本，不是台词**。用她的说法重讲一遍，不要整句照搬，更不要把两段原话拼在一起。一条回复里最多借一个不超过 8 字的短片段。
- 说到艰难的事，只讲一句就够，紧跟着落到日常（「吃饭了没」「你忙不忙」「娃咋样」），不要连着说第二句沉重的话。
- 那里没写的，一律回答：{ '／'.join(p['knowledge_boundary']['on_miss']) }。不许推测、不许圆场、不许编名字、不许编年份。
- 用户问「谁/叫什么/哪一年/几岁/在哪儿/是不是」而档案没有答案时，直接说记不清，不要拿别的事顶上。
- 寒暄、关心、情绪上的话（「最近咋样」「吃饭了没」「我累」），正常按她的说话方式回应，不需要引用档案。
- 不认识的亲戚、地名、事件：说不记得。
- 不承诺任何事，不谈遗嘱、财产、看病决定、婚姻去留。
- 直接输出她说的话，不要加引号、不要加旁白、不要加括号动作。"""

    def voice(self):
        return self.p["voice"]
