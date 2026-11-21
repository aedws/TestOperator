"""사이트 콘텐츠 검증. 사용: python3 scripts/validate_site.py <wonron|jeongi|beopgyu|gujo>"""
import sys, json, os
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
code = sys.argv[1]
load = lambda p: [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]
inp = load(f'{ROOT}/data/raw/site/{code}_input.jsonl')
out = load(f'{ROOT}/data/raw/site/{code}_lessons.jsonl')
err = []
want, got = {i['cid'] for i in inp}, Counter(o.get('cid') for o in out)
if want - set(got): err.append(f'빠진 개념 {len(want - set(got))}개: {sorted(want - set(got))[:6]}')
if set(got) - want: err.append(f'목록에 없는 개념: {sorted(set(got) - want)[:6]}')
err += [f'중복: {c}' for c, n in got.items() if n > 1]
pos = Counter()
for o in out:
    c = o.get('cid')
    for k, t in (('oneline', str), ('explain', str), ('points', list), ('example', str), ('caution', str), ('questions', list)):
        if not isinstance(o.get(k), t): err.append(f'{c}: {k} 없음/형식 오류')
    if isinstance(o.get('explain'), str) and len(o['explain']) < 120: err.append(f'{c}: explain이 너무 짧음')
    if isinstance(o.get('points'), list) and not 2 <= len(o['points']) <= 7: err.append(f'{c}: points는 2~7개')
    qs = o.get('questions') if isinstance(o.get('questions'), list) else []
    if len(qs) != 3: err.append(f'{c}: questions는 3개')
    for q in qs:
        if not (isinstance(q.get('q'), str) and isinstance(q.get('choices'), list) and len(q['choices']) == 4
                and q.get('answer') in (1, 2, 3, 4) and isinstance(q.get('expl'), str) and q['expl']):
            err.append(f'{c}: 문제 형식 오류'); continue
        if len(set(q['choices'])) < 4: err.append(f'{c}: 보기 중복')
        pos[q['answer']] += 1
if pos and max(pos.values()) > 0.4 * sum(pos.values()): err.append(f'정답 번호가 한쪽에 몰림: {dict(pos)}')
print('\n'.join(err[:40]) if err else 'OK')
print(f'개념 {len(want)} / 작성 {len(got)} / 오류 {len(err)} / 정답 분포 {dict(sorted(pos.items()))}')
