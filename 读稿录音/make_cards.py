# -*- coding: utf-8 -*-
"""把 脚本.txt 生成大字朗读卡（HTML，可直接打印，A4 两页一组）。

用法： python make_cards.py
输出： 读稿卡.html
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "脚本.txt")
OUT = os.path.join(HERE, "读稿卡.html")
PER_GROUP = 40

TIP = ("念完一句，停一口气。<b>念错了别解释，把这句从头再念一遍。</b>"
       "跟咱家不一样的地方照着念，别改词；实在念不出口就整句跳过。")


def main():
    lines = [l.strip() for l in io.open(SRC, encoding="utf-8") if l.strip()]
    groups = [lines[i:i + PER_GROUP] for i in range(0, len(lines), PER_GROUP)]

    parts = []
    for gi, g in enumerate(groups, 1):
        rows = []
        for i, s in enumerate(g):
            no = (gi - 1) * PER_GROUP + i + 1
            rows.append(f'<li><span class="no">{no}</span><span class="tx">{s}</span></li>')
        parts.append(
            f'<section class="page">'
            f'<div class="hd"><span class="g">第 {gi} 组</span>'
            f'<span class="r">{TIP}</span></div>'
            f'<ol>{"".join(rows)}</ol>'
            f'<div class="ft">第 {gi} 组结束 · 休息 5 分钟 · 小口温水，别喝冰的，别清嗓子</div>'
            f'</section>')

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>夕语 · 读稿卡</title>
<style>
  @page {{ size: A4; margin: 14mm 12mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #f4f4f2; color: #111;
         font-family: "Source Han Serif SC", "Noto Serif SC", "Songti SC", SimSun, serif; }}
  .page {{ width: 186mm; min-height: 269mm; margin: 8mm auto; padding: 6mm 8mm;
           background: #fff; box-shadow: 0 2px 12px rgba(0,0,0,.12);
           page-break-after: always; }}
  .page:last-child {{ page-break-after: auto; }}
  .hd {{ border-bottom: 2px solid #111; padding-bottom: 3mm; margin-bottom: 4mm; }}
  .g {{ display: block; font-size: 26pt; font-weight: 700; letter-spacing: 1px; }}
  .r {{ display: block; margin-top: 2mm; font-size: 12pt; line-height: 1.6; color: #333; }}
  ol {{ list-style: none; margin: 0; padding: 0; }}
  li {{ display: flex; align-items: baseline; gap: 4mm; padding: 2.2mm 0;
        border-bottom: 1px dashed #e2e2e2; }}
  .no {{ flex: 0 0 12mm; text-align: right; font-size: 11pt; color: #999;
         font-family: Consolas, monospace; }}
  .tx {{ font-size: 21pt; line-height: 1.55; letter-spacing: .5px; }}
  .ft {{ margin-top: 4mm; padding-top: 3mm; border-top: 2px solid #111;
         font-size: 12pt; color: #333; text-align: center; }}
  @media print {{
    body {{ background: #fff; }}
    .page {{ box-shadow: none; margin: 0; width: auto; min-height: 0; padding: 0; }}
  }}
</style></head><body>
{''.join(parts)}
</body></html>
"""
    io.open(OUT, "w", encoding="utf-8").write(html)
    print("已生成", OUT, "｜共", len(lines), "句，", len(groups), "组")


if __name__ == "__main__":
    main()
