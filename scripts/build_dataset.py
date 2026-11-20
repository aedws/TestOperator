"""공개 기출(cbtbank+comcbt)과 모두CBT 전자책을 하나의 데이터셋으로 합친다.

사용: python3 -I build_dataset.py <다운로드 폴더> <modu_all.json> <출력 폴더(data/raw)>

- 공개 회차(2016~2022년 2회): cbtbank 문항이 1차 자료. 정답은 comcbt 정답표와 대조하고,
  전자책에 같은 문항이 있으면 그것도 대조한다.
- 복원 회차(2022년 3회~): 전자책이 유일한 출처. 공개 기출에 같은 문항·같은 정답이 있으면 확정으로 본다.
"""
import sys, os, re, json, hashlib, subprocess, difflib
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_cbtbank import parse  # noqa: E402

DL, MODU, OUT = sys.argv[1:4]
SUBJECTS = ['소방원론', '소방전기일반', '소방관계법규', '소방전기시설의 구조 및 원리']
# 시험일 → (연도, 공단 회차 표기, 전자책 회차 번호)
PUBLIC = {
    '20160306': (2016, '1', 1), '20160508': (2016, '2', 2), '20161001': (2016, '4', 3),
    '20170305': (2017, '1', 1), '20170507': (2017, '2', 2), '20170923': (2017, '4', 3),
    '20180304': (2018, '1', 1), '20180428': (2018, '2', 2), '20180915': (2018, '4', 3),
    '20190303': (2019, '1', 1), '20190427': (2019, '2', 2), '20190921': (2019, '4', 3),
    '20200606': (2020, '1·2', 1), '20200822': (2020, '3', 2), '20200926': (2020, '4', 3),
    '20210307': (2021, '1', 1), '20210515': (2021, '2', 2), '20210912': (2021, '4', 3),
    '20220305': (2022, '1', 1), '20220424': (2022, '2', 2),
}
norm = lambda s: re.sub(r'[^0-9A-Za-z가-힣]', '', s)
sim = lambda a, b: difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()
FIG = re.compile(r'그림|도면|회로도')


def comcbt_key(pdf):
    txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True).stdout
    m = {'①': '1', '②': '2', '③': '3', '④': '4'}
    key, lines = {}, txt.splitlines()
    for i, ln in enumerate(lines[:-1]):
        nums, marks = re.findall(r'\d+', ln), re.findall(r'[①②③④]', lines[i + 1])
        if len(nums) == 10 and len(marks) == 10 and not re.search(r'[가-힣]', ln + lines[i + 1]):
            key.update({int(n): m[a] for n, a in zip(nums, marks)})
    if len(key) < 80:  # 정답표가 본문과 같은 줄에 섞인 경우: 좌표로 번호 바로 아래의 정답 기호를 찾는다
        import pdfplumber, logging
        logging.disable(logging.CRITICAL)
        with pdfplumber.open(pdf) as doc:
            for page in doc.pages[-2:]:
                ws = page.extract_words()
                nums = [w for w in ws if re.fullmatch(r'\d{1,2}', w['text']) and 1 <= int(w['text']) <= 80]
                for w in ws:
                    if w['text'] in m:
                        cx = (w['x0'] + w['x1']) / 2
                        above = [n for n in nums if abs((n['x0'] + n['x1']) / 2 - cx) < 9 and 4 < w['top'] - n['top'] < 26]
                        if len(above) == 1:
                            key.setdefault(int(above[0]['text']), m[w['text']])
        if len(key) < 80:
            print('정답표 일부만 읽음:', pdf, len(key))
    return key


modu = defaultdict(dict)
for q in json.load(open(MODU, encoding='utf-8')):
    modu[(q['year'], q['round'])][q['num']] = q

data, order = [], 0
# ---------- 공개 회차 ----------
for day in sorted(PUBLIC):
    year, rnd, eb = PUBLIC[day]
    order += 1
    qs = parse(open(os.path.join(DL, f'cbtbank_{day}.html'), encoding='utf-8', errors='replace').read())
    key = comcbt_key(os.path.join(DL, f'comcbt_{day}_t.pdf'))
    assert len(qs) == 80, (day, len(qs))
    for q in qs:
        e = modu[(year, eb)].get(q['num'])
        same_q = bool(e) and sim(q['question'], e['question']) > 0.6
        srcs, conflict = ['cbtbank'], []
        if key.get(q['num']) == q['answer']:
            srcs.append('comcbt')
        elif key.get(q['num']):
            conflict.append(f"comcbt {key[q['num']]}")
        if same_q and not q['has_image']:
            ca, ea = q['choices'][int(q['answer']) - 1], e['choices'][int(e['answer']) - 1]
            if norm(ca) == norm(ea) or sim(ca, ea) > 0.75:
                srcs.append('모두CBT')
            else:
                conflict.append('모두CBT 다른 보기')
        if len(srcs) >= 2 and not conflict:
            status = f"확정({len(srcs)}개 출처 일치: {', '.join(srcs)})"
        elif len(srcs) >= 2:
            status = f"확정({', '.join(srcs)} 일치 / 이견: {', '.join(conflict)})"
        else:
            status = f"정답 불확실(cbtbank {q['answer']} / {', '.join(conflict) or '대조 자료 없음'})"
        data.append({
            'order': order, 'year': year, 'round': rnd, 'restored': 'N', 'num': q['num'],
            'subject': SUBJECTS[(q['num'] - 1) // 20], 'question': q['question'], 'choices': q['choices'],
            'answer': q['answer'], 'url': f'https://cbtbank.kr/exam/nc{day}',
            'image': 'Y' if q['has_image'] or FIG.search(q['question']) else 'N', 'status': status,
            'rate': q['correct_rate'], 'hint': e['expl'] if same_q else '',
            'alt': e['question'] + ' / ' + ' / '.join(e['choices']) if same_q and q['has_image'] else '',
        })

# ---------- 복원 회차 ----------
bank = defaultdict(set)  # 공개 기출: 문제 → 정답 지문
for q in data:
    if q['image'] == 'N':
        bank[norm(q['question'])].add(norm(q['choices'][int(q['answer']) - 1]))
pub_keys = {(v[0], v[2]) for v in PUBLIC.values()}
for (year, rnd) in sorted(k for k in modu if k not in pub_keys):
    order += 1
    for num in sorted(modu[(year, rnd)]):
        e = modu[(year, rnd)][num]
        ans = norm(e['choices'][int(e['answer']) - 1])
        hits = bank.get(norm(e['question']))
        if hits and ans and any(h == ans or sorted(h) == sorted(ans) or sim(h, ans) > 0.75 for h in hits):
            status = '확정(2개 출처 일치: 모두CBT, 공개 기출 동일 문항)'
        elif hits and ans:
            status = '정답 불확실(공개 기출 동일 문항과 정답 지문 다름)'
        else:
            status = '정답 불확실(단일 출처: 모두CBT, 대조 자료 없음)'
        data.append({
            'order': order, 'year': year, 'round': str(rnd), 'restored': 'Y', 'num': num, 'subject': e['subject'],
            'question': e['question'], 'choices': e['choices'], 'answer': e['answer'],
            'url': '모두CBT 전자책(2026.11판, 이용자 제공 파일)',
            'image': 'Y' if e['has_image'] or FIG.search(e['question']) else 'N', 'status': status,
            'rate': None, 'hint': e['expl'], 'alt': '',
        })

# ---------- 고유 문항 ID ----------
for q in data:
    base = norm(q['question']) + '|' + '|'.join(sorted(norm(c) for c in q['choices']))
    if '그림' in ''.join(q['choices']) or len(norm(q['question'])) < 8:
        base += f"|{q['year']}-{q['round']}-{q['num']}"  # 그림 보기는 내용 비교 불가 → 묶지 않음
    q['uid'] = hashlib.md5((q['subject'] + base).encode()).hexdigest()[:10]

os.makedirs(OUT, exist_ok=True)
json.dump(data, open(os.path.join(OUT, 'dataset.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print(len(data), '문항 /', order, '회차 / 고유', len({q['uid'] for q in data}))
print(Counter(q['status'].split('(')[0] + ('·복원' if q['restored'] == 'Y' else '·공개') for q in data))
print(Counter(q['status'] for q in data if '이견' in q['status'] or (q['restored'] == 'N' and '불확실' in q['status'])))
