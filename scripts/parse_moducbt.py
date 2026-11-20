"""모두CBT '정답·해설집' PDF(여러 권으로 나뉜 것)를 문항 JSON으로 변환한다.

정답은 텍스트가 아니라 보기 번호 글자색(흰색 = 정답)으로만 표시되어 있어 글자 속성을 읽는다.

사용:
  python3 -I parse_moducbt.py pages <a01.pdf> <a01.items.json>   # 권별 1차 추출(병렬 실행 가능)
  python3 -I parse_moducbt.py merge <out.json> <a01.items.json> <a02.items.json> ...
"""
import sys, re, json, logging

logging.disable(logging.CRITICAL)
SUBJECTS = ['소방원론', '소방전기일반', '소방관계법규', '소방전기시설의 구조 및 원리']


def pages(pdf_path, out_path):
    import pdfplumber
    items = []
    with pdfplumber.open(pdf_path) as pdf:
        for pn, page in enumerate(pdf.pages):
            marks = []  # (top, kind, value)

            def is_marker(o):
                if o.get('object_type') != 'char':
                    return True
                if o['top'] > 800:  # 바닥글
                    return False
                if 'ExtraBold' in o['fontname'] and 30 < o['x0'] < 45 and o['text'] in '1234' and o['size'] < 9:
                    marks.append((o['top'], 'choice', o['text'], o['non_stroking_color'] == (1.0, 1.0, 1.0)))
                    return False
                return True

            body = page.filter(is_marker)
            lines = body.extract_text_lines(return_chars=True)
            for top, kind, val, white in marks:
                items.append({'p': pn, 'top': top - 9, 'k': 'choice', 'n': val, 'ans': white})
            for ln in lines:
                t = ln['text'].strip()
                bold = all('ExtraBold' in c['fontname'] for c in ln['chars'] if c['text'].strip())
                if bold and re.fullmatch(r'Q\d{2,3}', t):
                    items.append({'p': pn, 'top': ln['top'] - 5, 'k': 'q', 'n': int(t[1:])})
                elif bold and t.replace(' ', '') == '정답·해설':
                    items.append({'p': pn, 'top': ln['top'] - 5, 'k': 'expl'})
                elif re.search(r'\[.*필기\]\s*\d\d년\s*\d회차', t):
                    m = re.search(r'(\d\d)년\s*(\d)회차', t)
                    items.append({'p': pn, 'top': ln['top'], 'k': 'round', 'y': 2000 + int(m.group(1)), 'r': int(m.group(2))})
                else:
                    math = any('KaTeX' in c['fontname'] for c in ln['chars'])
                    items.append({'p': pn, 'top': ln['top'], 'k': 'text', 't': t, 'math': math})
            for im in page.images:
                items.append({'p': pn, 'top': im['top'], 'k': 'img'})
    json.dump(items, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False)
    print(pdf_path, len(items))


def merge(out_path, paths):
    qs, cur, seg, rnd = [], None, None, None
    for path in paths:
        items = json.load(open(path, encoding='utf-8'))
        items.sort(key=lambda i: (i['p'], i['top']))
        for it in items:
            k = it['k']
            if k == 'round':
                rnd, cur, seg = (it['y'], it['r']), None, None
            elif k == 'q':
                cur = {'year': rnd[0], 'round': rnd[1], 'num': it['n'], 'question': [], 'choices': [[], [], [], []],
                       'answer': '', 'expl': [], 'has_image': False, 'has_math': False}
                qs.append(cur)
                seg = 'question'
            elif cur is None:
                continue
            elif k == 'choice':
                seg = int(it['n']) - 1
                if it['ans']:
                    cur['answer'] += it['n']
            elif k == 'expl':
                seg = 'expl'
            elif k in ('text', 'img'):
                tgt = cur[seg] if isinstance(seg, str) else cur['choices'][seg]
                if k == 'img':
                    if seg != 'expl':
                        cur['has_image'] = True
                        tgt.append('[그림]')
                else:
                    tgt.append(it['t'])
                    if it['math'] and seg != 'expl':
                        cur['has_math'] = True
    for q in qs:
        q['question'] = ' '.join(q['question']).strip()
        q['choices'] = [' '.join(c).strip() for c in q['choices']]
        q['expl'] = ' '.join(q['expl']).strip()
        q['subject'] = SUBJECTS[min((q['num'] - 1) // 20, 3)]
    json.dump(qs, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(qs), '문항')


if __name__ == '__main__':
    if sys.argv[1] == 'pages':
        pages(sys.argv[2], sys.argv[3])
    else:
        merge(sys.argv[2], sys.argv[3:])
