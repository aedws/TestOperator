"""분류 작업용 입력 파일 생성: 과목별 고유 문항을 비슷한 것끼리 이웃하도록 정렬해 data/raw/tagging/에 쓴다."""
import json, os, re
from collections import defaultdict
import math
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = {'소방원론': 'wonron', '소방전기일반': 'jeongi', '소방관계법규': 'beopgyu', '소방전기시설의 구조 및 원리': 'gujo'}
data = json.load(open(os.path.join(ROOT, 'data/raw/dataset.json'), encoding='utf-8'))
uniq = defaultdict(list)
for q in data:
    uniq[q['uid']].append(q)
os.makedirs(os.path.join(ROOT, 'data/raw/tagging'), exist_ok=True)
for subj, code in CODE.items():
    items = []
    for uid, qs in uniq.items():
        if qs[0]['subject'] != subj:
            continue
        q = max(qs, key=lambda x: len(x['hint']))
        text = q['alt'] or (q['question'] + ' / ' + ' / '.join(q['choices']))
        items.append({'uid': uid, 'n': len(qs), 'latest': max(x['year'] for x in qs), 'q': text[:360],
                      'ans': q['choices'][int(q['answer']) - 1][:120], 'hint': q['hint'][:110]})
    grams = [Counter(t[k:k + 2] for t in [re.sub(r'\s+', '', i['q'])] for k in range(len(t) - 1)) for i in items]
    df = Counter(g for c in grams for g in c)
    vecs = []
    for c in grams:  # 글자 2-gram TF-IDF, 단위 벡터
        v = {g: n * math.log(len(items) / df[g]) for g, n in c.items()}
        z = math.sqrt(sum(x * x for x in v.values())) or 1
        vecs.append({g: x / z for g, x in v.items()})
    S = [[sum(x * b.get(g, 0) for g, x in a.items()) if len(a) <= len(b) else sum(x * a.get(g, 0) for g, x in b.items())
          for b in vecs] for a in vecs]
    left, cur, order = set(range(len(items))), 0, []
    while left:  # 가장 비슷한 문항을 다음에 놓는다
        order.append(cur)
        left.discard(cur)
        if left:
            cur = max(left, key=lambda j: S[order[-1]][j])
    with open(os.path.join(ROOT, f'data/raw/tagging/{code}_items.jsonl'), 'w', encoding='utf-8') as f:
        for i in order:
            f.write(json.dumps(items[i], ensure_ascii=False) + '\n')
    print(subj, len(items), os.path.getsize(os.path.join(ROOT, f'data/raw/tagging/{code}_items.jsonl')))
