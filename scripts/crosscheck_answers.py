"""cbtbank 파싱 결과(JSON)와 comcbt 교사용 PDF(pdftotext -layout 텍스트)의 정답표를 대조한다.
사용: python3 -I crosscheck_answers.py <q.json> <comcbt.txt>
출력: 문항번호별 일치 여부(JSON, stdout)
"""
import sys, re, json
q = json.load(open(sys.argv[1], encoding='utf-8'))
txt = open(sys.argv[2], encoding='utf-8').read()
m = {'①': '1', '②': '2', '③': '3', '④': '4'}
key = {}
lines = txt.splitlines()
for i, ln in enumerate(lines[:-1]):
    nums = re.findall(r'\d+', ln)
    marks = re.findall(r'[①②③④]', lines[i + 1])
    if len(nums) == 10 and len(marks) == 10 and not re.search(r'[가-힣]', ln + lines[i + 1]):
        for n, a in zip(nums, marks):
            key[int(n)] = m[a]
res = {x['num']: {'cbtbank': x['answer'], 'comcbt': key.get(x['num']),
                  'match': x['answer'] == key.get(x['num'])} for x in q}
json.dump(res, sys.stdout, ensure_ascii=False)
bad = [n for n, r in res.items() if not r['match']]
print(f"\n정답표 {len(key)}문항, 불일치 {bad}", file=sys.stderr)
