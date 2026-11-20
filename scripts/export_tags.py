"""분류 작업 결과(data/raw/tagging/*_tags.jsonl, *_concepts.jsonl)를 저장소용 CSV로 내보낸다.
문항 원문은 넣지 않는다(직접 쓴 요지만). 출력: data/tags/tags.csv, data/tags/concepts.csv"""
import json, csv, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'data/raw/tagging')
CODE = {'소방원론': 'wonron', '소방전기일반': 'jeongi', '소방관계법규': 'beopgyu', '소방전기시설의 구조 및 원리': 'gujo'}
load = lambda p: [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]
data = json.load(open(os.path.join(ROOT, 'data/raw/dataset.json'), encoding='utf-8'))
tags, cons = {}, []
for subj, code in CODE.items():
    if not os.path.exists(f'{T}/{code}_tags.jsonl'):
        print('아직 없음:', subj)
        continue
    tags.update({t['uid']: t for t in load(f'{T}/{code}_tags.jsonl')})
    cons += [dict(c, 과목=subj) for c in load(f'{T}/{code}_concepts.jsonl')]
one = lambda s: ' '.join(str(s).split())
with open(os.path.join(ROOT, 'data/tags/tags.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['회차순번', '연도', '회차', '복원여부', '과목', '문항번호', '개념ID', '요지', '개정무효', '비고'])
    for q in data:
        t = tags.get(q['uid'])
        if t:
            w.writerow([q['order'], q['year'], q['round'], q['restored'], q['subject'], q['num'], t['cid'],
                        one(t['gist']), t['void'], one(t['note'])])
with open(os.path.join(ROOT, 'data/tags/concepts.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['개념ID', '과목', '주요항목', '세부항목', '세세항목', '개념명', '핵심내용', '공식', '법조문'])
    for c in cons:
        w.writerow([c['cid'], c['과목']] + [one(c[k]) for k in ('주요항목', '세부항목', '세세항목', '개념명', '핵심내용', '공식', '법조문')])
print('문항', sum(1 for q in data if q['uid'] in tags), '/', len(data), '개념', len(cons))
