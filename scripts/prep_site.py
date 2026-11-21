"""사이트 콘텐츠 작성용 입력 생성: 과목별 단골 개념 목록(data/raw/site/<code>_input.jsonl)."""
import csv, json, os
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = {'소방원론': 'wonron', '소방전기일반': 'jeongi', '소방관계법규': 'beopgyu', '소방전기시설의 구조 및 원리': 'gujo'}
rd = lambda p: list(csv.DictReader(open(os.path.join(ROOT, p), encoding='utf-8-sig')))
freq = {r['개념ID']: r for r in rd('output/2_개념빈도표.csv')}
con = {r['개념ID']: r for r in rd('data/tags/concepts.csv')}
gists = defaultdict(list)
for t in rd('data/tags/tags.csv'):
    if t['개정무효'] != 'Y' and t['요지'] not in gists[t['개념ID']]:
        gists[t['개념ID']].append(t['요지'])
samples = defaultdict(list)  # 참고용 원문(비공개)
load = lambda p: [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]
for code in CODE.values():
    items = {i['uid']: i for i in load(f'{ROOT}/data/raw/tagging/{code}_items.jsonl')}
    for t in load(f'{ROOT}/data/raw/tagging/{code}_tags.jsonl'):
        if t['void'] != 'Y':
            samples[t['cid']].append(items[t['uid']])
for subj, code in CODE.items():
    rows = [c for c in freq if freq[c]['과목'] == subj and freq[c]['등급'] == '단골']
    with open(f'{ROOT}/data/raw/site/{code}_input.jsonl', 'w', encoding='utf-8') as f:
        for c in rows:
            ss = sorted(samples[c], key=lambda i: (-i['n'], -i['latest']))[:3]
            f.write(json.dumps({'cid': c, '개념명': con[c]['개념명'], '항목': freq[c]['출제기준 항목'], '출제회차수': int(freq[c]['출제 회차 수']),
                                '핵심내용': con[c]['핵심내용'], '공식': con[c]['공식'], '법조문': con[c]['법조문'],
                                '출제유형': gists[c][:10],
                                '참고기출': [{'q': i['q'][:300], 'ans': i['ans'], 'hint': i['hint']} for i in ss]}, ensure_ascii=False) + '\n')
    print(subj, len(rows), os.path.getsize(f'{ROOT}/data/raw/site/{code}_input.jsonl'))
