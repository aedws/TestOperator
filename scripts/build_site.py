"""학습 사이트 데이터 생성: docs/data/content.json(개념 설명+연습 문제), docs/data/tags.json(기출 문항→개념 연결표).
기출 원문은 넣지 않는다."""
import csv, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = {'소방원론': 'wonron', '소방전기일반': 'jeongi', '소방관계법규': 'beopgyu', '소방전기시설의 구조 및 원리': 'gujo'}
rd = lambda p: list(csv.DictReader(open(os.path.join(ROOT, p), encoding='utf-8-sig')))
load = lambda p: [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()] if os.path.exists(p) else []
freq = rd('output/2_개념빈도표.csv')
con = {r['개념ID']: r for r in rd('data/tags/concepts.csv')}
N = int(freq[0]['전체 회차 수'])
subjects = []
for subj, code in CODE.items():
    lessons = {l['cid']: l for l in load(f'{ROOT}/data/raw/site/{code}_lessons.jsonl')}
    cs = []
    for r in freq:
        if r['과목'] != subj or r['등급'] != '단골' or r['개념ID'] not in lessons:
            continue
        l, c = lessons[r['개념ID']], con[r['개념ID']]
        cs.append({'cid': r['개념ID'], 'name': r['개념명'], 'group': r['출제기준 항목'].split(' > ')[-1],
                   'rounds': int(r['출제 회차 수']), 'recent': int(r['최근 10회차 중 출제']), 'formula': c['공식'], 'law': c['법조문'],
                   'oneline': l['oneline'], 'explain': l['explain'], 'points': l['points'], 'example': l['example'],
                   'caution': l['caution'], 'questions': l['questions']})
    subjects.append({'code': code, 'name': subj, 'concepts': cs})
    print(subj, len(cs), '개념', sum(len(c['questions']) for c in cs), '문제')
json.dump({'rounds': N, 'subjects': subjects}, open(f'{ROOT}/docs/data/content.json', 'w', encoding='utf-8'), ensure_ascii=False)
grade = {r['개념ID']: [r['등급'], r['개념명']] for r in freq}
tags = {f"{t['연도']}|{t['회차']}|{CODE[t['과목']]}|{t['문항번호']}": [t['개념ID'], 1 if t['개정무효'] == 'Y' else 0] for t in rd('data/tags/tags.csv')}
json.dump({'concepts': grade, 'tags': tags}, open(f'{ROOT}/docs/data/tags.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('연결표', len(tags), '문항')
