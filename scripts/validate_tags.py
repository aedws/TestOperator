"""분류 결과 검증. 사용: python3 scripts/validate_tags.py <wonron|jeongi|beopgyu|gujo>
data/raw/tagging/<code>_items.jsonl 의 모든 uid가 <code>_tags.jsonl 에 한 번씩 있고,
개념ID가 <code>_concepts.jsonl 에 있으며, 출제기준 항목이 data/taxonomy/출제기준_필기.csv 와 맞는지 본다."""
import sys, json, csv, os
from collections import Counter
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
code = sys.argv[1]
SUBJ = {'wonron': '소방원론', 'jeongi': '소방전기일반', 'beopgyu': '소방관계법규', 'gujo': '소방전기시설의 구조 및 원리'}[code]
PREFIX = {'wonron': '원론-', 'jeongi': '전기-', 'beopgyu': '법규-', 'gujo': '구조-'}[code]
T = os.path.join(ROOT, 'data/raw/tagging')
load = lambda p: [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]
items, tags, cons = load(f'{T}/{code}_items.jsonl'), load(f'{T}/{code}_tags.jsonl'), load(f'{T}/{code}_concepts.jsonl')
tax = {(r['주요항목'], r['세부항목']) for r in csv.DictReader(open(f'{ROOT}/data/taxonomy/출제기준_필기.csv', encoding='utf-8')) if r['과목'] == SUBJ}
err = []
uids = {i['uid'] for i in items}
tc = Counter(t['uid'] for t in tags)
err += [f'분류 안 된 uid {len(uids - set(tc))}개: {sorted(uids - set(tc))[:8]}'] if uids - set(tc) else []
err += [f'없는 uid: {sorted(set(tc) - uids)[:8]}'] if set(tc) - uids else []
err += [f'중복 uid: {[u for u, n in tc.items() if n > 1][:8]}'] if any(n > 1 for n in tc.values()) else []
cc = Counter(c['cid'] for c in cons)
err += [f'개념ID 중복: {[c for c, n in cc.items() if n > 1]}'] if any(n > 1 for n in cc.values()) else []
for c in cons:
    miss = [k for k in ('cid', '주요항목', '세부항목', '세세항목', '개념명', '핵심내용', '공식', '법조문') if k not in c]
    if miss: err.append(f"{c.get('cid')}: 필드 없음 {miss}")
    elif (c['주요항목'], c['세부항목']) not in tax: err.append(f"{c['cid']}: 출제기준에 없는 항목 {c['주요항목']} > {c['세부항목']}")
    if not c.get('cid', '').startswith(PREFIX): err.append(f"{c.get('cid')}: 접두어는 {PREFIX}")
for t in tags:
    miss = [k for k in ('uid', 'cid', 'gist', 'void', 'note') if k not in t]
    if miss: err.append(f"{t.get('uid')}: 필드 없음 {miss}")
    elif t['cid'] not in cc: err.append(f"{t['uid']}: 개념 사전에 없는 {t['cid']}")
    elif t['void'] not in ('N', 'Y', '확인필요'): err.append(f"{t['uid']}: void 값 {t['void']}")
unused = set(cc) - {t.get('cid') for t in tags}
err += [f'쓰이지 않는 개념ID: {sorted(unused)[:10]}'] if unused else []
print('\n'.join(err[:40]) if err else 'OK')
print(f'문항 {len(items)} / 분류 {len(tc)} / 개념 {len(cc)} / 오류 {len(err)}')
