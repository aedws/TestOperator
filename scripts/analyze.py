"""기출 빈도 분석: 원본 CSV + 산출물 2~6 생성.

입력
  data/raw/q_YYYYMMDD.json   parse_cbtbank.py 결과 (저장소 미포함)
  data/raw/xc_YYYYMMDD.json  crosscheck_answers.py 결과 (저장소 미포함)
  data/tags/*_tags.csv       문항별 태그(개념ID, 요지, 개정무효)
  data/tags/concepts.csv     개념 사전(출제기준 항목, 핵심내용, 공식, 법조문)
출력: output/

사용: python3 scripts/analyze.py [--subject 소방원론] [--regular 0.5] [--sometimes 0.15]
"""
import argparse, csv, glob, json, os, re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAM = '소방설비기사(전기)'
# 시험일 → (연도, 회차). 2단계에서 회차가 늘면 여기에 추가한다.
ROUNDS = {'20220305': (2022, 1), '20220424': (2022, 2)}
RESTORED = set()  # CBT 복원 회차의 시험일 키

ap = argparse.ArgumentParser()
ap.add_argument('--subject', default='소방원론', help='분석 과목(쉼표 구분, all=전체)')
ap.add_argument('--regular', type=float, default=0.5, help='단골 기준(출제 회차 비율 이상)')
ap.add_argument('--sometimes', type=float, default=0.15, help='가끔 기준(출제 회차 비율 이상)')
ap.add_argument('--killer-max-rounds', type=int, default=2, help='이 회차 수 이하로만 나오면 킬러')
ap.add_argument('--min-rounds-for-count-rule', type=int, default=10,
                help='전체 회차가 이보다 적으면 "1~2회만 출제=킬러" 규칙을 끄고 등급을 잠정으로 표시')
ap.add_argument('--backtest-rounds', type=int, default=5, help='과락 점검에 쓸 최근 회차 수')
ap.add_argument('--pass-line', type=int, default=8, help='과목당 과락 기준 문항 수')
args = ap.parse_args()


def read_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_csv(path, header, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def difficulty(rate):
    if rate is None:
        return '미상'
    return '상' if rate < 65 else ('중' if rate < 80 else '하')


# ---------- 1. 원본 데이터 ----------
questions = []
for path in sorted(glob.glob(os.path.join(ROOT, 'data/raw/q_*.json'))):
    day = re.search(r'q_(\d{8})', path).group(1)
    year, rnd = ROUNDS[day]
    xc = json.load(open(path.replace('q_', 'xc_'), encoding='utf-8'))
    for q in json.load(open(path, encoding='utf-8')):
        chk = xc.get(str(q['num']))
        if chk and chk['match']:
            status = '확정(2개 출처 일치: cbtbank, comcbt)'
        elif chk and chk['comcbt']:
            status = f"정답 불확실(cbtbank {chk['cbtbank']} / comcbt {chk['comcbt']})"
        else:
            status = '단일 출처(미대조)'
        questions.append({
            'day': day, 'year': year, 'round': rnd, 'subject': q['subject'], 'num': q['num'],
            'question': q['question'], 'choices': (q['choices'] + [''] * 4)[:4], 'answer': q['answer'],
            'url': f'https://cbtbank.kr/exam/nc{day}', 'restored': 'Y' if day in RESTORED else 'N',
            'image': 'Y' if q['has_image'] else 'N', 'status': status, 'rate': q['correct_rate'],
        })

subjects = None if args.subject == 'all' else set(args.subject.split(','))
scope = [q for q in questions if subjects is None or q['subject'] in subjects]
os.makedirs(os.path.join(ROOT, 'output'), exist_ok=True)
write_csv(os.path.join(ROOT, 'output/1_원본데이터.csv'),
          ['시험', '연도', '회차', '과목', '문항번호', '문제', '보기1', '보기2', '보기3', '보기4', '정답',
           '출처URL', '복원여부', '그림포함여부', '정답확인상태'],
          [[EXAM, q['year'], q['round'], q['subject'], q['num'], q['question'], *q['choices'], q['answer'],
            q['url'], q['restored'], q['image'], q['status']] for q in scope])

# ---------- 태그 결합 ----------
concepts = {c['개념ID']: c for c in read_csv(os.path.join(ROOT, 'data/tags/concepts.csv'))}
tags = {}
for path in glob.glob(os.path.join(ROOT, 'data/tags/*_tags.csv')):
    for t in read_csv(path):
        tags[(int(t['연도']), int(t['회차']), concepts[t['개념ID']]['과목'], int(t['문항번호']))] = t

rows, untagged, void = [], [], []
for q in scope:
    t = tags.get((q['year'], q['round'], q['subject'], q['num']))
    if not t:
        untagged.append(q)
        continue
    q = dict(q, cid=t['개념ID'], gist=t['요지'], note=t['비고'], rk=(q['year'], q['round']))
    (void if t['개정무효'] == 'Y' else rows).append(q)

all_rounds = sorted({q['rk'] for q in rows + void})
N = len(all_rounds)
provisional = N < args.min_rounds_for_count_rule


def grade_table(use_rounds):
    """개념ID → 등급. use_rounds에 속한 회차만으로 계산."""
    n = len(use_rounds)
    seen = defaultdict(set)
    for q in rows:
        if q['rk'] in use_rounds:
            seen[q['cid']].add(q['rk'])
    out = {}
    for cid, rs in seen.items():
        ratio = len(rs) / n
        if n >= args.min_rounds_for_count_rule and len(rs) <= args.killer_max_rounds:
            g = '킬러'
        elif ratio >= args.regular:
            g = '단골'
        elif ratio >= args.sometimes:
            g = '가끔'
        else:
            g = '킬러'
        out[cid] = g
    return out


grades = grade_table(set(all_rounds))
by_c = defaultdict(list)
for q in rows:
    by_c[q['cid']].append(q)


def ref(q):
    return f"{q['year']}년 {q['round']}회 {q['num']}번"


def stats(cid):
    qs = by_c[cid]
    rs = {q['rk'] for q in qs}
    rates = [q['rate'] for q in qs if q['rate'] is not None]
    avg = round(sum(rates) / len(rates)) if rates else None
    rep = max(qs, key=lambda q: q['rk'] + (-q['num'],))  # 가장 최근 회차의 문항
    return len(rs), len(qs), avg, rep


order = sorted(by_c, key=lambda c: (-stats(c)[0], -stats(c)[1], concepts[c]['과목'], c))
gl = lambda cid: grades[cid] + ('(잠정)' if provisional else '')

# ---------- 2. 개념 빈도표 ----------
write_csv(os.path.join(ROOT, 'output/2_개념빈도표.csv'),
          ['개념ID', '개념명', '과목', '출제기준 항목', '등급', '출제 회차 수', '전체 회차 수', '출제 비율(%)',
           '문항 수', '평균 정답률(%)', '난이도', '대표 문항', '대표 문항 요지'],
          [[c, concepts[c]['개념명'], concepts[c]['과목'],
            ' > '.join([concepts[c]['주요항목'], concepts[c]['세부항목'], concepts[c]['세세항목']]),
            gl(c), stats(c)[0], N, round(100 * stats(c)[0] / N), stats(c)[1], stats(c)[2],
            difficulty(stats(c)[2]), ref(stats(c)[3]), stats(c)[3]['gist']] for c in order])

# ---------- 과락 점검(표본 외 역산) ----------
subj_list = sorted({q['subject'] for q in rows})
recent = all_rounds[-args.backtest_rounds:]
backtest = []  # (과목, 회차, 단골 적중, 단골+가끔 적중, 문항 수)
for s in subj_list:
    for rk in recent:
        g = grade_table(set(all_rounds) - {rk})
        target = [q for q in rows if q['rk'] == rk and q['subject'] == s]
        hit_r = sum(1 for q in target if g.get(q['cid']) == '단골')
        hit_s = sum(1 for q in target if g.get(q['cid']) in ('단골', '가끔'))
        backtest.append((s, rk, hit_r, hit_s, len(target)))
widen = {s: any(b[2] < args.pass_line for b in backtest if b[0] == s) for s in subj_list}
study_grades = lambda s: ('단골', '가끔') if widen[s] else ('단골',)

# ---------- 3. 압축 학습 목록 ----------
md = ['# 과목별 압축 학습 목록', '',
      f'- 대상: {EXAM} 필기 / 분석 회차 {N}개 ({", ".join(f"{y}년 {r}회" for y, r in all_rounds)})',
      f'- 등급 기준: 단골 ≥ {args.regular:.0%}, 가끔 ≥ {args.sometimes:.0%}, 그 미만 킬러'
      + (f' — 회차가 {N}개뿐이라 등급은 **잠정**입니다.' if provisional else ''), '']
for s in subj_list:
    gs = study_grades(s)
    md += [f'## {s}', '', f'학습 범위: {" + ".join(gs)}'
           + (' (단골만으로는 과락 기준 미달 → 가끔까지 확대)' if widen[s] else ''), '']
    cur = None
    for c in sorted([c for c in order if concepts[c]['과목'] == s and grades[c] in gs],
                    key=lambda c: (concepts[c]['주요항목'], concepts[c]['세부항목'], -stats(c)[0])):
        k = concepts[c]
        head = f"{k['주요항목']} > {k['세부항목']}"
        if head != cur:
            md += [f'### {head}', '']
            cur = head
        n_r, n_q, avg, rep = stats(c)
        md.append(f"- **{k['개념명']}** `{c}` — {gl(c)}, {n_r}/{N}회 출제({n_q}문항), 평균 정답률 {avg}%")
        md.append(f"  - 핵심: {k['핵심내용']}")
        if k['공식']:
            md.append(f"  - 공식: `{k['공식']}`")
        if k['법조문']:
            md.append(f"  - 법조문: {k['법조문']}")
        md.append(f"  - 대표 문제: {ref(rep)} — {rep['gist']}")
    md.append('')
open(os.path.join(ROOT, 'output/3_압축학습목록.md'), 'w', encoding='utf-8').write('\n'.join(md))

# ---------- 4. 공식 모음 ----------
write_csv(os.path.join(ROOT, 'output/4_공식모음.csv'),
          ['과목', '공식', '개념명', '개념ID', '등급', '출제 회차 수', '문항 수', '대표 문항', '쓰임'],
          [[concepts[c]['과목'], concepts[c]['공식'], concepts[c]['개념명'], c, gl(c), stats(c)[0], stats(c)[1],
            ref(stats(c)[3]), stats(c)[3]['gist']]
           for c in sorted(order, key=lambda c: (concepts[c]['과목'], -stats(c)[0], -stats(c)[1]))
           if concepts[c]['공식']])

# ---------- 5. 킬러 목록 ----------
if provisional:
    # 회차가 적어 비율로는 킬러가 나오지 않는다 → 1회만 출제된 개념 중 정답률 70% 미만을 후보로 표시
    killers = [c for c in order if stats(c)[0] == 1 and (stats(c)[2] or 100) < 70]
    k_label = '킬러 후보(잠정: 1회 출제 + 정답률 70% 미만)'
else:
    killers = [c for c in order if grades[c] == '킬러']
    k_label = '킬러'
killers.sort(key=lambda c: (stats(c)[2] if stats(c)[2] is not None else 100))
write_csv(os.path.join(ROOT, 'output/5_킬러목록.csv'),
          ['개념ID', '개념명', '과목', '구분', '출제 회차 수', '전체 회차 수', '평균 정답률(%)', '난이도',
           '유형', '대표 문항', '대표 문항 요지', '판단 참고'],
          [[c, concepts[c]['개념명'], concepts[c]['과목'], k_label, stats(c)[0], N, stats(c)[2],
            difficulty(stats(c)[2]),
            '계산(공식)' if concepts[c]['공식'] else ('법령·기준' if concepts[c]['법조문'] else '암기'),
            ref(stats(c)[3]), stats(c)[3]['gist'], concepts[c]['핵심내용']] for c in killers])

# ---------- 6. 요약 리포트 ----------
rp = ['# 요약 리포트', '', f'- 시험: {EXAM} 필기', f'- 분석 과목: {", ".join(subj_list)}',
      f'- 분석 회차: {N}개 ({", ".join(f"{y}년 {r}회" for y, r in all_rounds)})',
      f'- 문항: 수집 {len(scope)} / 분석 {len(rows)} / 개정무효 제외 {len(void)} / 미분류 {len(untagged)}',
      f'- 개념ID: {len(by_c)}개 (2회 이상 출제 {sum(1 for c in by_c if stats(c)[0] >= 2)}개)',
      f'- 정답 확인: 확정 {sum(1 for q in scope if q["status"].startswith("확정"))}'
      f' / 불확실 {sum(1 for q in scope if q["status"].startswith("정답 불확실"))}'
      f' / 미대조 {sum(1 for q in scope if q["status"].startswith("단일"))}',
      f'- 그림 포함 문항: {sum(1 for q in scope if q["image"] == "Y")}', '']
if provisional:
    rp += [f'> 회차가 {N}개뿐이라 등급·커버율은 형식 확인용입니다. '
           f'{args.min_rounds_for_count_rule}회차 이상이 모이면 "1~2회만 출제 = 킬러" 규칙이 자동으로 켜집니다.', '']
rp += ['## 과목별 예상 커버율 (과락 점검)', '',
       '점검 대상 회차를 **빼고** 나머지 회차만으로 등급을 매긴 뒤, 그 회차에서 맞힐 수 있었던 문항 수를 셉니다.', '',
       '| 과목 | 점검 회차 | 단골만 | 단골+가끔 | 과락 기준 | 판정 |', '|---|---|---|---|---|---|']
for s, rk, hr, hs, n in backtest:
    rp.append(f'| {s} | {rk[0]}년 {rk[1]}회 | {hr}/{n} | {hs}/{n} | {args.pass_line} | '
              f'{"미달 → 가끔까지 확대" if hr < args.pass_line else "충족"} |')
rp += ['', '## 과락 위험 과목', '']
rp += [f'- {s}: ' + ('단골만으로는 8문제 미만 → 학습 범위를 가끔 등급까지 넓힘' if widen[s] else '단골만으로 충족')
       for s in subj_list]
rp += ['', '## 출제기준 주요항목별 문항 분포', '', '| 과목 | 주요항목 | 세부항목 | 문항 수 | 비율 |', '|---|---|---|---|---|']
dist = defaultdict(int)
for q in rows:
    k = concepts[q['cid']]
    dist[(k['과목'], k['주요항목'], k['세부항목'])] += 1
for (s, a, b), n in sorted(dist.items()):
    tot = sum(v for (s2, _, _), v in dist.items() if s2 == s)
    rp.append(f'| {s} | {a} | {b} | {n} | {100 * n / tot:.0f}% |')
rp += ['', '## 수집 사이트 현황', '', '| 사이트 | 용도 | robots.txt | 상태 | 비고 |', '|---|---|---|---|---|']
for r in read_csv(os.path.join(ROOT, 'data/sources.csv')):
    rp.append(f"| {r['사이트']} | {r['용도']} | {r['robots.txt']} | {r['수집상태']} | {r['비고']} |")
notes = os.path.join(ROOT, 'data/report_notes.md')
if os.path.exists(notes):
    rp += ['', open(notes, encoding='utf-8').read().rstrip()]
open(os.path.join(ROOT, 'output/6_요약리포트.md'), 'w', encoding='utf-8').write('\n'.join(rp) + '\n')

print(f'회차 {N} / 문항 {len(rows)} / 개념 {len(by_c)} / 미분류 {len(untagged)} / 킬러후보 {len(killers)}')
for b in backtest:
    print(b)
