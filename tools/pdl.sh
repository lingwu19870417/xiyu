#!/bin/bash
# 并行分段下载器：把大文件切成 N 段并发拉取，再合并。
# 用途：单线程只有几百 KB/s 时，8 线程通常能到 8~10 倍。
#
# 用法：
#   bash pdl.sh <URL> <总字节数> <输出路径> [线程数=8]
#
# 前提：服务端支持 Range 请求（返回 206）。可用
#   curl -sI -r 0-1023 <URL> | grep -i "206\|content-range"
# 先确认。
set -u
URL="$1"
SIZE="$2"
OUT="$3"
N="${4:-8}"
DIR="$(dirname "$OUT")"
mkdir -p "$DIR"
CHUNK=$(( (SIZE + N - 1) / N ))
echo "总大小 $SIZE 字节，分 $N 段，每段 $CHUNK"
seq 0 $((N-1)) | xargs -P "$N" -I{} bash -c '
  i={}
  S='"$CHUNK"'
  T='"$SIZE"'
  U="'"$URL"'"
  D="'"$DIR"'"
  start=$(( i * S ))
  end=$(( start + S - 1 ))
  if [ "$end" -ge "$T" ]; then end=$(( T - 1 )); fi
  curl -sL --retry 5 --retry-delay 2 -r "$start-$end" -o "$D/part_$i" "$U"
  echo "  段 $i 完成 $(stat -c%s "$D/part_$i" 2>/dev/null || echo 0) 字节"
' 2>&1 | tail -20
cat "$DIR"/part_* > "$OUT"
rm -f "$DIR"/part_*
ACTUAL=$(stat -c%s "$OUT")
echo "合并完成: $OUT  实际 $ACTUAL / 期望 $SIZE"
if [ "$ACTUAL" -eq "$SIZE" ]; then echo "✅ 大小一致"; else echo "❌ 大小不符"; fi
