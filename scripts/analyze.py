"""기출 빈도 분석: 산출물 1~6 생성.

입력
  data/tags/tags.csv      문항별 개념ID·요지·개정무효 (export_tags.py가 생성)
  data/tags/concepts.csv  개념 사전(출제기준 항목, 핵심내용, 공식, 법조문)
  data/raw/dataset.json   문항 원문·정답·정답률 (저장소 미포함. 없으면 1번 산출물과 난이도는 생략)
출력: output/

등급
  킬러: 한 회차에만 나온 개념(--killer-max-rounds 1)
  단골: 출제 회차 비율이 기준 이상. 기준을 주지 않으면 '단골만 공부해도 최근 회차에서 합격'하는
        가장 높은 기준을 자동으로 찾는다(과목당 과락 기준 이상 + 전체 60% 이상).
  가끔: 그 사이

사용: python3 scripts/analyze.py [--regular 0.13] [--killer-max-rounds 1] [--pass-total 0.6]
"""
import argparse, csv, json, os
from collections import defaultdict, Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAM = '소방설비기사(전기분야)'
SUBJ_ORDER = ['소방원론', '소방전기일반', '소방관계법규', '소방전기시설의 구조 및 원리']

ap = argparse.ArgumentParser()
ap.add_argument('--regular', type=float, default=None, help='단골 기준(출제 회차 비율 이상). 생략하면 자동 탐색')
ap.add_argument('--pass-total', type=float, default=0.6, help='합격 기준(전체 문항 대비 비율)')
ap.add_argument('--killer-max-rounds', type=int, default=1, help='이 회차 수 이하로만 나오면 킬러')
ap.add_argument('--backtest-rounds', type=int, default=5, help='과락 점검에 쓸 최근 회차 수')
ap.add_argument('--pass-line', type=int, default=8, help='과목당 과락 기준 문항 수')
args = ap.parse_args()
OUT = os.path.join(ROOT, 'output')
os.makedirs(OUT, exist_ok=True)


def read_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write_csv(name, header, rows):
    with open(os.path.join(OUT, name), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def difficulty(rate):
    if rate is None:
        return '미상'
    return '상' if rate < 65 else ('중' if rate < 80 else '하')


concepts = {c['개념ID']: c for c in read_csv(os.path.join(ROOT, 'data/tags/concepts.csv'))}
tags = read_csv(os.path.join(ROOT, 'data/tags/tags.csv'))
for t in tags:
    t['o'] = int(t['회차순번'])
    t['num'] = int(t['문항번호'])
    t['rate'] = None

# ---------- 1. 원본 데이터 ----------
raw_path = os.path.join(ROOT, 'data/raw/dataset.json')
raw = json.load(open(raw_path, encoding='utf-8')) if os.path.exists(raw_path) else []
if raw:
    key = {(t['o'], t['num']): t for t in tags}
    for q in raw:
        t = key.get((q['order'], q['num']))
        if t:
            t['rate'] = q['rate']
    write_csv('1_원본데이터.csv',
              ['시험', '연도', '회차', '과목', '문항번호', '문제', '보기1', '보기2', '보기3', '보기4', '정답',
               '출처URL', '복원여부', '그림포함여부', '정답확인상태'],
              [[EXAM, q['year'], q['round'], q['subject'], q['num'], q['question'], *(q['choices'] + [''] * 4)[:4],
                q['answer'], q['url'], q['restored'], q['image'], q['status']] for q in raw])

rounds = {}
for t in tags:
    rounds[t['o']] = f"{t['연도']}년 {t['회차']}회" + ('(복원)' if t['복원여부'] == 'Y' else '')
ORD = sorted(rounds)
N = len(ORD)
subjects = [s for s in SUBJ_ORDER if any(t['과목'] == s for t in tags)]
valid = [t for t in tags if t['개정무효'] != 'Y']
void = [t for t in tags if t['개정무효'] == 'Y']
check = [t for t in tags if t['개정무효'] == '확인필요']


def grade_table(use, regular):
    """개념ID → 등급. use(회차순번 집합)에 속한 회차만으로 계산."""
    n = len(use)
    seen = defaultdict(set)
    for t in valid:
        if t['o'] in use:
            seen[t['개념ID']].add(t['o'])
    out = {}
    for cid, rs in seen.items():
        if len(rs) <= args.killer_max_rounds:
            out[cid] = '킬러'
        elif len(rs) / n >= regular - 1e-9:
            out[cid] = '단골'
        else:
            out[cid] = '가끔'
    return out


def run_backtest(regular):
    """최근 회차마다 그 이전 회차만으로 등급을 매겨 역산. (과목, 회차순번, 단골 적중, 단골+가끔 적중, 문항 수)"""
    out = []
    for s in subjects:
        for o in ORD[-args.backtest_rounds:]:
            g = grade_table({x for x in ORD if x < o}, regular)
            target = [t for t in tags if t['o'] == o and t['과목'] == s]
            ok = lambda t, gs: t['개정무효'] != 'Y' and g.get(t['개념ID']) in gs
            out.append((s, o, sum(ok(t, ('단골',)) for t in target), sum(ok(t, ('단골', '가끔')) for t in target), len(target)))
    return out


def passes(bt):
    """단골만으로 모든 점검 회차에서 과목별 과락 기준과 전체 합격 기준을 넘는가."""
    for o in ORD[-args.backtest_rounds:]:
        bs = [b for b in bt if b[1] == o]
        if any(b[2] < args.pass_line for b in bs) or sum(b[2] for b in bs) < args.pass_total * sum(b[4] for b in bs):
            return False
    return True


scan = []  # (출제 회차 수 기준 k, 단골 개념 수, 과목별 최저, 합계 최저, 합격 여부)
full_cnt = Counter()
for cid, rs in {c: {t['o'] for t in valid if t['개념ID'] == c} for c in {t['개념ID'] for t in valid}}.items():
    full_cnt[cid] = len(rs)
for k in range(min(N, 12), args.killer_max_rounds, -1):
    bt = run_backtest(k / N)
    tot = [sum(b[2] for b in bt if b[1] == o) for o in ORD[-args.backtest_rounds:]]
    scan.append((k, sum(1 for v in full_cnt.values() if v >= k),
                 min(b[2] for b in bt), min(tot), max(tot), passes(bt)))
if args.regular is None:
    ok_k = [x[0] for x in scan if x[5]]
    REG_K = max(ok_k) if ok_k else args.killer_max_rounds + 1
    REGULAR, AUTO = REG_K / N, True
else:
    REGULAR, AUTO = args.regular, False
    REG_K = next(k for k in range(1, N + 1) if k / N >= REGULAR - 1e-9)

grades = grade_table(set(ORD), REGULAR)
by_c = defaultdict(list)
for t in valid:
    by_c[t['개념ID']].append(t)
ref = lambda t: f"{rounds[t['o']]} {t['num']}번"
ST = {}
for cid, ts in by_c.items():
    rates = [t['rate'] for t in ts if t['rate'] is not None]
    ST[cid] = {'rounds': len({t['o'] for t in ts}), 'qs': len(ts),
               'avg': round(sum(rates) / len(rates)) if rates else None,
               'rep': max(ts, key=lambda t: (t['o'], -t['num'])),
               'last': rounds[max(t['o'] for t in ts)],
               'recent': len({t['o'] for t in ts if t['o'] in ORD[-10:]})}
GORD = {'단골': 0, '가끔': 1, '킬러': 2}
order = sorted(by_c, key=lambda c: (SUBJ_ORDER.index(concepts[c]['과목']), GORD[grades[c]], -ST[c]['rounds'], -ST[c]['qs'], c))
item = lambda c: ' > '.join([concepts[c]['주요항목'], concepts[c]['세부항목']])

# ---------- 2. 개념 빈도표 ----------
write_csv('2_개념빈도표.csv',
          ['개념ID', '개념명', '과목', '출제기준 항목', '등급', '출제 회차 수', '전체 회차 수', '출제 비율(%)',
           '문항 수', '최근 10회차 중 출제', '마지막 출제', '평균 정답률(%)', '난이도', '대표 문항', '대표 문항 요지'],
          [[c, concepts[c]['개념명'], concepts[c]['과목'], item(c), grades[c], ST[c]['rounds'], N,
            round(100 * ST[c]['rounds'] / N), ST[c]['qs'], ST[c]['recent'], ST[c]['last'], ST[c]['avg'],
            difficulty(ST[c]['avg']), ref(ST[c]['rep']), ST[c]['rep']['요지']] for c in order])

# ---------- 과락 점검: 그 회차 이전 회차만으로 등급을 매겨 역산 ----------
backtest = run_backtest(REGULAR)
widen = {s: any(b[2] < args.pass_line for b in backtest if b[0] == s) for s in subjects}
study = lambda s: ('단골', '가끔') if widen[s] else ('단골',)

# ---------- 3. 압축 학습 목록 ----------
md = ['# 과목별 압축 학습 목록', '',
      f'- 대상: {EXAM} 필기 / 분석 회차 {N}개 ({rounds[ORD[0]]} ~ {rounds[ORD[-1]]})',
      f'- 등급 기준: 단골 = {N}회차 중 {REG_K}회 이상 출제({REGULAR:.0%}), '
      f'킬러 = {args.killer_max_rounds}회만 출제, 가끔 = 그 사이',
      '- 각 개념의 "핵심"은 분류 과정에서 정리한 요약입니다. 수치는 교재·현행 법령과 대조해 쓰세요.', '']
for s in subjects:
    gs = study(s)
    cs = [c for c in order if concepts[c]['과목'] == s and grades[c] in gs]
    md += [f'## {s}', '', f'학습 범위: **{" + ".join(gs)}** — 개념 {len(cs)}개'
           + (' (단골만으로는 최근 회차에서 과락 기준에 못 미쳐 가끔까지 넓힘)' if widen[s] else ''), '']
    cur = None
    for c in sorted(cs, key=lambda c: (concepts[c]['주요항목'], concepts[c]['세부항목'], GORD[grades[c]], -ST[c]['rounds'])):
        k = concepts[c]
        if item(c) != cur:
            cur = item(c)
            md += [f'### {cur}', '']
        st = ST[c]
        md.append(f"- **{k['개념명']}** `{c}` — {grades[c]}, {st['rounds']}/{N}회 출제({st['qs']}문항)"
                  + (f", 평균 정답률 {st['avg']}%" if st['avg'] is not None else ''))
        md.append(f"  - 핵심: {k['핵심내용']}")
        if k['공식']:
            md.append(f"  - 공식: `{k['공식']}`")
        if k['법조문']:
            md.append(f"  - 법조문: {k['법조문']}")
        md.append(f"  - 대표 문제: {ref(st['rep'])} — {st['rep']['요지']}")
    md.append('')
open(os.path.join(OUT, '3_압축학습목록.md'), 'w', encoding='utf-8').write('\n'.join(md))

# ---------- 4. 공식 모음 ----------
write_csv('4_공식모음.csv',
          ['과목', '공식', '개념명', '개념ID', '등급', '출제 회차 수', '문항 수', '대표 문항', '쓰임'],
          [[concepts[c]['과목'], concepts[c]['공식'], concepts[c]['개념명'], c, grades[c], ST[c]['rounds'], ST[c]['qs'],
            ref(ST[c]['rep']), ST[c]['rep']['요지']]
           for c in sorted(by_c, key=lambda c: (SUBJ_ORDER.index(concepts[c]['과목']), -ST[c]['rounds'], -ST[c]['qs']))
           if concepts[c]['공식']])

# ---------- 5. 킬러 목록 ----------
kind = lambda c: '계산(공식)' if concepts[c]['공식'] else ('법령·기준' if concepts[c]['법조문'] else '암기')
killers = sorted([c for c in by_c if grades[c] == '킬러'],
                 key=lambda c: (SUBJ_ORDER.index(concepts[c]['과목']), -ST[c]['rounds'],
                                ST[c]['avg'] if ST[c]['avg'] is not None else 101))
write_csv('5_킬러목록.csv',
          ['개념ID', '개념명', '과목', '출제 회차 수', '전체 회차 수', '출제 비율(%)', '최근 10회차 중 출제', '마지막 출제',
           '평균 정답률(%)', '난이도', '유형', '대표 문항', '대표 문항 요지', '핵심내용'],
          [[c, concepts[c]['개념명'], concepts[c]['과목'], ST[c]['rounds'], N, round(100 * ST[c]['rounds'] / N),
            ST[c]['recent'], ST[c]['last'], ST[c]['avg'], difficulty(ST[c]['avg']), kind(c), ref(ST[c]['rep']),
            ST[c]['rep']['요지'], concepts[c]['핵심내용']] for c in killers])

# ---------- 6. 요약 리포트 ----------
status = Counter((q['restored'], q['status'].split('(')[0]) for q in raw)
rp = ['# 요약 리포트', '', f'- 시험: {EXAM} 필기 4과목',
      f'- 분석 회차: {N}개 ({rounds[ORD[0]]} ~ {rounds[ORD[-1]]}) — 공단 공개 기출 '
      f'{sum(1 for o in ORD if "복원" not in rounds[o])}회차 + CBT 복원 {sum(1 for o in ORD if "복원" in rounds[o])}회차',
      f'- 문항: 분류 {len(tags)} / 분석 {len(valid)} / 개정무효 제외 {len(void)} / 개정 확인필요(분석에는 포함) {len(check)}',
      f'- 개념ID: {len(by_c)}개']
if raw:
    rp += [f"- 정답 확인: 공개 회차 확정 {status[('N', '확정')]} · 불확실 {status[('N', '정답 불확실')]} / "
           f"복원 회차 확정 {status[('Y', '확정')]} · 불확실 {status[('Y', '정답 불확실')]}",
           f"- 그림 포함 문항: {sum(1 for q in raw if q['image'] == 'Y')}"]
rp += ['', '## 과목별 예상 커버율', '',
       '전체 회차의 문항 중 각 등급 개념에 속하는 비율입니다. "학습 범위 커버율"은 아래 과락 점검 결과로 정한 범위 기준입니다.', '',
       '| 과목 | 개념 수(단골/가끔/킬러) | 단골 문항 | 가끔 문항 | 킬러 문항 | 개정무효 | 학습 범위 | 학습 범위 커버율 |', '|---|---|---|---|---|---|---|---|']
for s in subjects:
    ts = [t for t in tags if t['과목'] == s]
    gc = Counter(grades[c] for c in by_c if concepts[c]['과목'] == s)
    qc = Counter(grades[t['개념ID']] for t in ts if t['개정무효'] != 'Y')
    nv = sum(1 for t in ts if t['개정무효'] == 'Y')
    cov = sum(qc[g] for g in study(s)) / len(ts)
    rp.append(f"| {s} | {gc['단골']}/{gc['가끔']}/{gc['킬러']} | {qc['단골'] / len(ts):.0%} | {qc['가끔'] / len(ts):.0%} | "
              f"{qc['킬러'] / len(ts):.0%} | {nv / len(ts):.0%} | {'+'.join(study(s))} | **{cov:.0%}** (20문항 중 약 {cov * 20:.1f}) |")
rp += ['', '## 과락 점검 (최근 5회차 역산)', '',
       '점검 회차 **이전** 회차만으로 등급을 매긴 뒤, 그 회차 20문항 중 학습한 개념에서 나온 문항 수를 셉니다. '
       '개념을 알면 맞힌다고 가정한 상한선입니다.', '',
       '| 과목 | ' + ' | '.join(rounds[o] for o in ORD[-args.backtest_rounds:]) + ' | 판정 |',
       '|---|' + '---|' * (min(args.backtest_rounds, N) + 1)]
for s in subjects:
    bs = [b for b in backtest if b[0] == s]
    rp.append(f'| {s} (단골만) | ' + ' | '.join(f'{b[2]}/{b[4]}' for b in bs) + ' | '
              + ('과락 기준 미달 회차 있음 → 가끔까지 확대' if widen[s] else '충족') + ' |')
    rp.append(f'| {s} (단골+가끔) | ' + ' | '.join(f'{b[3]}/{b[4]}' for b in bs) + ' | '
              + ('**과락 위험**' if any(b[3] < args.pass_line for b in bs) else '충족') + ' |')
last = ORD[-args.backtest_rounds:]
rp.append('| **4과목 합계 (단골만)** | ' + ' | '.join(
    f"**{sum(b[2] for b in backtest if b[1] == o)}/{sum(b[4] for b in backtest if b[1] == o)}**" for o in last)
    + f' | 합격선 {args.pass_total:.0%} ' + ('충족' if passes(backtest) else '**미달 회차 있음**') + ' |')
rp.append('| 4과목 합계 (단골+가끔) | ' + ' | '.join(
    f"{sum(b[3] for b in backtest if b[1] == o)}/{sum(b[4] for b in backtest if b[1] == o)}" for o in last) + ' | |')
rp += ['', '## 단골 기준을 정한 근거', '',
       f'킬러는 {args.killer_max_rounds}회만 출제된 개념으로 고정하고, 단골 기준(출제 회차 수)을 바꿔 가며 "단골만 공부했을 때" 최근 '
       f'{len(last)}회차 결과를 역산했습니다. '
       + (f'모든 회차에서 과목당 {args.pass_line}문제 이상, 합계 {args.pass_total:.0%} 이상이 되는 가장 좁은 범위인 '
          f'**{REG_K}회 이상**을 단골로 잡았습니다.' if AUTO else f'단골 기준은 직접 지정한 {REGULAR:.0%}({REG_K}회 이상)입니다.'), '',
       '| 단골 기준 | 단골 개념 수 | 과목별 최저 문항 | 4과목 합계(최저~최고) | 단골만으로 합격 |', '|---|---|---|---|---|']
for k, n, mn, tlo, thi, ok in scan:
    rp.append(f"| {'**' if k == REG_K else ''}{k}회 이상{'**' if k == REG_K else ''} | {n} | {mn} | {tlo}~{thi} | {'가능' if ok else '불가'} |")
rp += ['', '## 과락 위험 과목', '']
for s in subjects:
    bs = [b for b in backtest if b[0] == s]
    if any(b[3] < args.pass_line for b in bs):
        rp.append(f'- **{s}**: 단골+가끔까지 공부해도 8문제에 못 미친 회차가 있습니다. 킬러 일부까지 필요합니다.')
    elif widen[s]:
        rp.append(f'- {s}: 단골만으로는 부족(최저 {min(b[2] for b in bs)}문제) → 가끔까지 넓히면 최저 {min(b[3] for b in bs)}문제.')
    else:
        rp.append(f'- {s}: 단골만으로 충족(최저 {min(b[2] for b in bs)}문제).')
rp += ['', '## 출제기준 항목별 문항 분포', '', '| 과목 | 주요항목 | 세부항목 | 문항 수 | 과목 내 비율 |', '|---|---|---|---|---|']
dist = Counter((concepts[t['개념ID']]['과목'], concepts[t['개념ID']]['주요항목'], concepts[t['개념ID']]['세부항목']) for t in valid)
for (s, a, b), n in sorted(dist.items(), key=lambda x: (SUBJ_ORDER.index(x[0][0]), x[0][1], x[0][2])):
    rp.append(f"| {s} | {a} | {b} | {n} | {n / sum(v for k, v in dist.items() if k[0] == s):.0%} |")
rp += ['', '## 수집 사이트 현황', '', '| 사이트 | 용도 | robots.txt | 상태 | 비고 |', '|---|---|---|---|---|']
for r in read_csv(os.path.join(ROOT, 'data/sources.csv')):
    rp.append(f"| {r['사이트']} | {r['용도']} | {r['robots.txt']} | {r['수집상태']} | {r['비고']} |")
notes = os.path.join(ROOT, 'data/report_notes.md')
if os.path.exists(notes):
    rp += ['', open(notes, encoding='utf-8').read().rstrip()]
open(os.path.join(OUT, '6_요약리포트.md'), 'w', encoding='utf-8').write('\n'.join(rp) + '\n')

print(f'회차 {N} / 문항 {len(tags)} (무효 {len(void)}, 확인필요 {len(check)}) / 개념 {len(by_c)} / '
      f'등급 {dict(Counter(grades.values()))}')
for s in subjects:
    print(s, [(b[2], b[3]) for b in backtest if b[0] == s], '확대' if widen[s] else '')
