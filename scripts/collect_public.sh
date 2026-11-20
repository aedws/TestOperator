#!/bin/bash
# 공단 공개 기출(2016~2022년 2회) 수집: cbtbank 시험 페이지 + comcbt 교사용 PDF(정답표).
# 사용: collect_public.sh <다운로드 폴더>   (요청 사이 4초 간격)
set -u
OUT="$1"; UA="Mozilla/5.0 (personal-study)"; mkdir -p "$OUT"
DATES="20160306 20160508 20161001 20170305 20170507 20170923 20180304 20180428 20180915 20190303 20190427 20190921 20200606 20200822 20200926 20210307 20210515 20210912 20220305 20220424"
[ -s "$OUT/comcbt_nc.html" ] || { curl -sS -L -m 40 -A "$UA" -o "$OUT/comcbt_nc.html" "https://www.comcbt.com/xe/nc"; sleep 4; }
for d in $DATES; do
  [ -s "$OUT/cbtbank_$d.html" ] || { curl -sS -L -m 60 --retry 2 --retry-delay 8 -A "$UA" -o "$OUT/cbtbank_$d.html" "https://cbtbank.kr/exam/nc$d"; sleep 4; }
  if [ ! -s "$OUT/comcbt_${d}_t.pdf" ]; then
    kd="${d:0:4}년 ${d:4:2}월 ${d:6:2}일"
    post=$(python3 -I -c "
import re,sys
c=open(sys.argv[1],encoding='utf-8',errors='replace').read()
m=re.search(r'<a href=\"(/xe/nc/\d+)\"[^>]*>\s*[^<]*'+re.escape(sys.argv[2]),c)
print(m.group(1) if m else '')" "$OUT/comcbt_nc.html" "$kd")
    [ -z "$post" ] && { echo "$d: comcbt 게시글 없음"; continue; }
    curl -sS -L -m 60 -A "$UA" -o "$OUT/comcbt_post_$d.html" "https://www.comcbt.com$post"; sleep 4
    url=$(python3 -I -c "
import re,html,sys
c=open(sys.argv[1],encoding='utf-8',errors='replace').read()
m=re.search(r'<a[^>]+href=\"([^\"]*procFileDownload[^\"]*)\"[^>]*>[^<]*교사용[^<]*\.pdf',c)
print(html.unescape(m.group(1)) if m else '')" "$OUT/comcbt_post_$d.html")
    [ -z "$url" ] && { echo "$d: 교사용 PDF 링크 없음"; continue; }
    curl -sS -L -m 90 -A "$UA" -e "https://www.comcbt.com$post" -o "$OUT/comcbt_${d}_t.pdf" "$url"; sleep 4
  fi
  echo "$d ok $(stat -c %s "$OUT/cbtbank_$d.html" 2>/dev/null) $(stat -c %s "$OUT/comcbt_${d}_t.pdf" 2>/dev/null)"
done
