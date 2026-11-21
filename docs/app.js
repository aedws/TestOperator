/* 소방설비기사(전기) 필기 학습 사이트 — 빌드 없이 동작하는 단일 페이지 앱 */
(() => {
  'use strict';
  const $app = document.getElementById('app');
  const PASS_SUBJECT = 8, PASS_TOTAL = 0.6, PER_SUBJECT = 20;
  let DATA = null, TAGS = null, MINE = null; // MINE: 불러온 기출(이 브라우저에만 저장)
  const BY_CID = {}, SUBJ = {};

  // ---------- 저장소 ----------
  const store = {
    get(k, d) { try { return JSON.parse(localStorage.getItem('fe.' + k)) ?? d; } catch { return d; } },
    set(k, v) { try { localStorage.setItem('fe.' + k, JSON.stringify(v)); } catch { /* 저장 불가 환경 */ } },
  };
  let done = store.get('done', {});   // cid → true
  let hist = store.get('hist', {});   // 문항ID → [맞힌 횟수, 틀린 횟수]
  const idb = {
    open() {
      return new Promise((res, rej) => {
        const r = indexedDB.open('fe-mine', 1);
        r.onupgradeneeded = () => r.result.createObjectStore('kv');
        r.onsuccess = () => res(r.result);
        r.onerror = () => rej(r.error);
      });
    },
    async get(k) { const db = await this.open(); return new Promise((res, rej) => { const q = db.transaction('kv').objectStore('kv').get(k); q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error); }); },
    async set(k, v) { const db = await this.open(); return new Promise((res, rej) => { const t = db.transaction('kv', 'readwrite'); t.objectStore('kv').put(v, k); t.oncomplete = res; t.onerror = () => rej(t.error); }); },
    async del(k) { const db = await this.open(); return new Promise((res, rej) => { const t = db.transaction('kv', 'readwrite'); t.objectStore('kv').delete(k); t.oncomplete = res; t.onerror = () => rej(t.error); }); },
  };

  // ---------- 도우미 ----------
  const clean = (kids) => kids.flat(Infinity).filter((k) => k != null && k !== false && k !== '');
  const h = (tag, attrs = {}, ...kids) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === false || v == null) continue;
      if (k === 'class') e.className = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else if (k === 'html') e.innerHTML = v;
      else e.setAttribute(k, v === true ? '' : v);
    }
    e.append(...clean(kids));
    return e;
  };
  const paras = (text) => String(text || '').split(/\n\s*\n/).filter(Boolean).map((p) => h('p', {}, p));
  const shuffle = (a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);
  const meter = (ratio, cls = '') => h('div', { class: 'meter ' + cls }, h('i', { style: `width:${Math.max(0, Math.min(100, ratio * 100))}%` }));
  const render = (...nodes) => { $app.replaceChildren(...clean(nodes)); window.scrollTo(0, 0); };
  const record = (qid, ok) => { const r = hist[qid] || [0, 0]; r[ok ? 0 : 1]++; hist[qid] = r; store.set('hist', hist); };
  const practiceQs = (codes) => DATA.subjects.filter((s) => codes.includes(s.code)).flatMap((s) =>
    s.concepts.flatMap((c) => c.questions.map((q, i) => ({ id: `${c.cid}#${i}`, code: s.code, cid: c.cid, q: q.q, choices: q.choices, answer: q.answer, expl: q.expl }))));

  // ---------- 홈 ----------
  function home() {
    const total = DATA.subjects.reduce((n, s) => n + s.concepts.length, 0);
    const nDone = Object.keys(done).filter((c) => BY_CID[c]).length;
    const nq = DATA.subjects.reduce((n, s) => n + s.concepts.length * 3, 0);
    const tried = Object.entries(hist).filter(([k]) => k.includes('#'));
    const right = tried.filter(([, v]) => v[0] > 0).length;
    render(
      h('h1', {}, '자주 나오는 것만, 처음 보는 사람도 알 수 있게'),
      h('p', { class: 'muted' }, `최근 10년 기출 ${DATA.rounds}회차 2,480문항을 개념별로 묶어 세어 보니, 4회 이상 나온 "단골" 개념 ${total}개에서 문제의 약 4분의 3이 나왔습니다. 이 사이트는 그 단골 개념만 다룹니다.`),
      h('div', { class: 'stats' },
        h('div', { class: 'stat' }, h('b', {}, `${nDone} / ${total}`), h('span', {}, '학습한 개념')),
        h('div', { class: 'stat' }, h('b', {}, `${tried.length} / ${nq}`), h('span', {}, '풀어 본 연습 문제')),
        h('div', { class: 'stat' }, h('b', {}, tried.length ? pct(right, tried.length) + '%' : '–'), h('span', {}, '맞힌 적 있는 문제 비율'))),
      h('div', { class: 'btns' }, h('a', { class: 'btn primary', href: '#/learn' }, '개념 학습 시작'), h('a', { class: 'btn', href: '#/quiz' }, '문제 풀기')),
      h('h2', {}, '과목'),
      h('div', { class: 'grid' }, DATA.subjects.map((s) => {
        const d = s.concepts.filter((c) => done[c.cid]).length;
        return h('a', { class: 'card subj', href: `#/learn/${s.code}` }, h('b', {}, s.name),
          h('span', { class: 'small muted' }, `단골 개념 ${s.concepts.length}개 · 연습 문제 ${s.concepts.length * 3}개`),
          meter(d / (s.concepts.length || 1), 'ok'), h('span', { class: 'small muted' }, `${d}개 학습함`));
      })),
      h('h2', {}, '합격 기준'),
      h('p', {}, '4과목 각 20문항. 과목마다 8문제(40점) 이상, 전체 평균 60점(80문항 중 48문제) 이상이면 합격입니다.'),
      h('p', { class: 'muted small' }, '분석에서 단골 개념만 공부했다고 가정하고 최근 5회차를 되짚어 보면 80문항 중 51~61문제가 이 범위에서 나왔습니다. 공부한 개념을 모두 맞힌다고 가정한 수치라 여유가 크지는 않습니다.'));
  }

  // ---------- 개념 학습 ----------
  function learnIndex() {
    render(h('h1', {}, '개념 학습'), h('p', { class: 'muted' }, '과목을 고르세요. 출제 빈도가 높은 개념부터 보여 줍니다.'),
      h('div', { class: 'grid' }, DATA.subjects.map((s) => {
        const d = s.concepts.filter((c) => done[c.cid]).length;
        return h('a', { class: 'card subj', href: `#/learn/${s.code}` }, h('b', {}, s.name),
          h('span', { class: 'small muted' }, `${d} / ${s.concepts.length} 학습`), meter(d / (s.concepts.length || 1), 'ok'));
      })));
  }

  function learnSubject(code) {
    const s = SUBJ[code];
    if (!s) return learnIndex();
    const order = store.get('order', 'freq');
    const groups = {};
    const list = order === 'freq' ? s.concepts.slice().sort((a, b) => b.rounds - a.rounds) : s.concepts;
    if (order === 'group') for (const c of s.concepts) (groups[c.group] = groups[c.group] || []).push(c);
    const row = (c) => h('a', { class: 'row', href: `#/learn/${code}/${encodeURIComponent(c.cid)}` },
      h('span', { class: 'check' + (done[c.cid] ? ' on' : '') }, '✓'),
      h('span', { class: 'txt' }, h('b', {}, c.name), h('span', {}, c.oneline)),
      h('span', { class: 'freq' }, `${c.rounds}/${DATA.rounds}회`, meter(c.rounds / DATA.rounds)));
    const setOrder = (v) => { store.set('order', v); learnSubject(code); };
    render(
      h('p', { class: 'crumb' }, h('a', { href: '#/learn' }, '개념 학습'), ' › ', s.name),
      h('h1', {}, s.name),
      h('p', { class: 'muted' }, `단골 개념 ${s.concepts.length}개. 오른쪽 숫자는 ${DATA.rounds}회차 중 그 개념이 나온 회차 수입니다.`),
      h('div', { class: 'btns' },
        h('button', { class: 'btn' + (order === 'freq' ? ' primary' : ''), onclick: () => setOrder('freq') }, '많이 나온 순'),
        h('button', { class: 'btn' + (order === 'group' ? ' primary' : ''), onclick: () => setOrder('group') }, '단원별'),
        h('a', { class: 'btn', href: `#/quiz?s=${code}` }, '이 과목 문제 풀기')),
      order === 'freq' ? list.map(row) : Object.entries(groups).map(([g, cs]) => [h('h3', {}, g), cs.sort((a, b) => b.rounds - a.rounds).map(row)]));
  }

  function lesson(code, cid) {
    const s = SUBJ[code], c = BY_CID[cid];
    if (!s || !c) return learnSubject(code);
    const list = s.concepts.slice().sort((a, b) => b.rounds - a.rounds);
    const i = list.findIndex((x) => x.cid === cid);
    const prev = list[i - 1], next = list[i + 1];
    const toggle = () => { if (done[cid]) delete done[cid]; else done[cid] = true; store.set('done', done); lesson(code, cid); };
    const qs = c.questions.map((q, k) => ({ id: `${cid}#${k}`, code, cid, ...q }));
    render(
      h('p', { class: 'crumb' }, h('a', { href: '#/learn' }, '개념 학습'), ' › ', h('a', { href: `#/learn/${code}` }, s.name), ' › ', c.group),
      h('h1', {}, c.name),
      h('p', {}, h('span', { class: 'tag' }, `${DATA.rounds}회차 중 ${c.rounds}회 출제`), h('span', { class: 'tag gray' }, `최근 10회차 중 ${c.recent}회`)),
      h('div', { class: 'lesson' }, h('p', { class: 'muted' }, c.oneline), paras(c.explain)),
      h('div', { class: 'box' }, h('h4', {}, '시험에 나오는 포인트'), h('ul', {}, c.points.map((p) => h('li', {}, p)))),
      c.formula && h('div', { class: 'box formula' }, c.formula),
      c.example && h('div', { class: 'box pre' }, h('h4', {}, '풀이 예시 · 외우는 요령'), c.example),
      c.law && h('p', { class: 'small muted' }, '근거: ' + c.law),
      c.caution && h('div', { class: 'box warn' }, '확인 필요 — ' + c.caution),
      h('h2', {}, '바로 풀어 보기'),
      qs.map((q, k) => questionCard(q, k + 1, { instant: true })),
      h('div', { class: 'btns' }, h('button', { class: 'btn' + (done[cid] ? '' : ' primary'), onclick: toggle }, done[cid] ? '학습 완료 취소' : '학습 완료로 표시')),
      h('div', { class: 'navlr' },
        prev ? h('a', { class: 'btn', href: `#/learn/${code}/${encodeURIComponent(prev.cid)}` }, '‹ ' + prev.name) : h('span'),
        next ? h('a', { class: 'btn', href: `#/learn/${code}/${encodeURIComponent(next.cid)}` }, next.name + ' ›') : h('span')));
  }

  // ---------- 문제 카드 ----------
  // opts.instant: 고르면 바로 채점 / opts.onPick: 선택 콜백 / opts.review: {picked} 결과 보기
  function questionCard(q, no, opts = {}) {
    const box = h('div', { class: 'card q' });
    const draw = (picked, reveal) => {
      const c = BY_CID[q.cid];
      box.replaceChildren(...clean([
        h('div', { class: 'stem' }, h('span', { class: 'no' }, no + '.'), q.q),
        q.choices.map((t, i) => {
          const n = i + 1;
          let cls = 'opt';
          if (reveal) { if (n === q.answer) cls += ' right'; else if (n === picked) cls += ' wrong'; } else if (n === picked) cls += ' sel';
          return h('button', { class: cls, disabled: reveal, onclick: () => { if (opts.instant) { record(q.id, n === q.answer); draw(n, true); } else { draw(n, false); } opts.onPick && opts.onPick(n); } },
            h('span', { class: 'n' }, n), h('span', {}, t));
        }),
        reveal && h('div', { class: 'expl ' + (picked === q.answer ? 'ok' : 'no') },
          h('b', {}, picked === q.answer ? '정답입니다. ' : picked ? `오답입니다. 정답은 ${q.answer}번. ` : `풀지 않음. 정답은 ${q.answer}번. `), q.expl || '',
          q.status && q.status.startsWith('정답 불확실') && h('div', { class: 'small muted' }, '이 문항의 정답은 한 출처로만 확인된 것입니다.'),
          c && !opts.noLink && h('div', { class: 'small' }, h('a', { href: `#/learn/${c.code}/${encodeURIComponent(q.cid)}` }, '개념 보기: ' + c.name)))]));
    };
    draw(opts.review ? opts.review.picked : null, !!opts.review);
    return box;
  }

  // ---------- 문제 은행 ----------
  function quizSetup(params) {
    const cfg = store.get('quizcfg', { src: 'practice', codes: DATA.subjects.map((s) => s.code), n: 20, mode: 'instant', wrong: false, regular: true });
    if (params.get('s') && SUBJ[params.get('s')]) cfg.codes = [params.get('s')];
    if (cfg.src === 'mine' && !MINE) cfg.src = 'practice';
    const pool = () => {
      let qs = cfg.src === 'mine' ? MINE.filter((q) => cfg.codes.includes(q.code) && (!cfg.regular || q.grade === '단골')) : practiceQs(cfg.codes);
      if (cfg.wrong) qs = qs.filter((q) => hist[q.id] && hist[q.id][1] > 0 && hist[q.id][1] >= hist[q.id][0]);
      return qs;
    };
    const draw = () => {
      store.set('quizcfg', cfg);
      const qs = pool();
      const pick = (name, value, label, checked, on, type = 'radio') => h('label', { class: 'pick' }, h('input', { type, name, checked, onchange: on }), label);
      render(
        h('h1', {}, '문제 은행'),
        h('p', { class: 'muted' }, '사이트에 실린 문제는 단골 개념마다 새로 만든 연습 문제입니다. 실제 기출로 풀려면 "내 기출"에서 파일을 불러오세요.'),
        h('fieldset', {}, h('legend', {}, '문제 종류'),
          pick('src', 'practice', '연습 문제', cfg.src === 'practice', () => { cfg.src = 'practice'; draw(); }),
          MINE ? pick('src', 'mine', `내 기출 (${MINE.length}문항)`, cfg.src === 'mine', () => { cfg.src = 'mine'; draw(); })
            : h('a', { class: 'small', href: '#/import' }, '내 기출 파일 불러오기 ›')),
        h('fieldset', {}, h('legend', {}, '과목'), DATA.subjects.map((s) => pick('c', s.code, s.name, cfg.codes.includes(s.code), (e) => {
          cfg.codes = e.target.checked ? [...cfg.codes, s.code] : cfg.codes.filter((x) => x !== s.code); draw();
        }, 'checkbox'))),
        h('fieldset', {}, h('legend', {}, '방식'),
          pick('m', 'instant', '한 문제씩 바로 채점', cfg.mode === 'instant', () => { cfg.mode = 'instant'; draw(); }),
          pick('m', 'exam', `모의고사 (고른 과목마다 ${PER_SUBJECT}문항, 끝나고 채점)`, cfg.mode === 'exam', () => { cfg.mode = 'exam'; draw(); })),
        cfg.mode === 'instant' && h('fieldset', {}, h('legend', {}, '문항 수'), [10, 20, 40].map((n) => pick('n', n, n + '문항', cfg.n === n, () => { cfg.n = n; draw(); }))),
        h('fieldset', {}, h('legend', {}, '범위'),
          pick('w', 1, '틀렸던 문제만', cfg.wrong, (e) => { cfg.wrong = e.target.checked; draw(); }, 'checkbox'),
          cfg.src === 'mine' && pick('r', 1, '단골 개념 문제만', cfg.regular, (e) => { cfg.regular = e.target.checked; draw(); }, 'checkbox')),
        h('p', { class: 'small muted' }, `조건에 맞는 문제 ${qs.length}개`),
        h('div', { class: 'btns' }, h('button', { class: 'btn primary', disabled: !qs.length, onclick: () => start(cfg, qs) }, '시작')));
    };
    draw();
  }

  function start(cfg, pool) {
    let qs;
    if (cfg.mode === 'exam') qs = DATA.subjects.filter((s) => cfg.codes.includes(s.code)).flatMap((s) => shuffle(pool.filter((q) => q.code === s.code)).slice(0, PER_SUBJECT));
    else qs = shuffle(pool).slice(0, cfg.n);
    const picks = new Array(qs.length).fill(null);
    cfg.mode === 'exam' ? examView(qs, picks) : instantView(qs, picks, 0);
  }

  function instantView(qs, picks, i) {
    const q = qs[i];
    const nextBtn = h('button', { class: 'btn primary', disabled: true, onclick: () => (i + 1 < qs.length ? instantView(qs, picks, i + 1) : result(qs, picks, false)) }, i + 1 < qs.length ? '다음 문제' : '결과 보기');
    render(
      h('div', { class: 'progress' }, h('span', {}, `${i + 1} / ${qs.length} · ${SUBJ[q.code].name}`), h('span', {}, `맞힌 문제 ${picks.filter((p, k) => p === qs[k].answer).length}`)),
      meter((i + 1) / qs.length),
      questionCard(q, i + 1, { instant: true, onPick: (n) => { picks[i] = n; nextBtn.disabled = false; } }),
      h('div', { class: 'btns' }, nextBtn, h('button', { class: 'btn', onclick: () => result(qs, picks, false) }, '그만하고 결과 보기')));
  }

  function examView(qs, picks) {
    const left = h('span', {}, '');
    const upd = () => { left.textContent = `${picks.filter((p) => p != null).length} / ${qs.length} 문항 답함`; };
    upd();
    let last = null;
    const parts = [];
    qs.forEach((q, i) => {
      if (q.code !== last) { parts.push(h('h2', {}, SUBJ[q.code].name)); last = q.code; }
      parts.push(questionCard(q, i + 1, { onPick: (n) => { picks[i] = n; upd(); } }));
    });
    render(h('h1', {}, '모의고사'), h('p', { class: 'muted' }, '모두 고른 뒤 맨 아래에서 채점하세요. 실제 시험은 과목당 30분입니다.'), parts,
      h('div', { class: 'btns' }, h('button', { class: 'btn primary', onclick: () => { qs.forEach((q, i) => record(q.id, picks[i] === q.answer)); result(qs, picks, true); } }, '채점하기'), left));
  }

  function result(qs, picks, exam) {
    const rows = DATA.subjects.map((s) => {
      const idx = qs.map((q, i) => i).filter((i) => qs[i].code === s.code && (exam || picks[i] != null));
      return { s, n: idx.length, ok: idx.filter((i) => picks[i] === qs[i].answer).length };
    }).filter((r) => r.n);
    const N = rows.reduce((a, r) => a + r.n, 0), OK = rows.reduce((a, r) => a + r.ok, 0);
    const full = exam && rows.length === 4 && rows.every((r) => r.n === PER_SUBJECT);
    const cut = rows.some((r) => r.ok < Math.ceil(r.n * PASS_SUBJECT / PER_SUBJECT));
    const passed = !cut && OK >= N * PASS_TOTAL;
    const wrong = qs.map((q, i) => i).filter((i) => (exam || picks[i] != null) && picks[i] !== qs[i].answer);
    render(
      h('h1', {}, `${N}문항 중 ${OK}문항 정답 (${pct(OK, N)}점)`),
      N ? h('p', { class: passed ? 'pass' : 'fail' }, exam
        ? (passed ? (full ? '합격 기준을 넘었습니다.' : '고른 과목 기준으로 합격선을 넘었습니다.') : cut ? '과락(40점 미만) 과목이 있습니다.' : '평균 60점에 못 미쳤습니다.')
        : (pct(OK, N) >= 60 ? '60점 이상입니다.' : '60점에 못 미쳤습니다.')) : h('p', { class: 'muted' }, '푼 문제가 없습니다.'),
      N && h('div', { class: 'card' }, h('table', {}, h('thead', {}, h('tr', {}, h('th', {}, '과목'), h('th', { class: 'num' }, '정답'), h('th', { class: 'num' }, '점수'), h('th', {}, ''))),
        h('tbody', {}, rows.map((r) => h('tr', {}, h('td', {}, r.s.name), h('td', { class: 'num' }, `${r.ok} / ${r.n}`), h('td', { class: 'num' }, pct(r.ok, r.n)),
          h('td', { class: pct(r.ok, r.n) < 40 ? 'fail' : '' }, pct(r.ok, r.n) < 40 ? '과락' : '')))))),
      h('div', { class: 'btns' }, h('a', { class: 'btn primary', href: '#/quiz', onclick: () => setTimeout(route) }, '다시 풀기'), h('a', { class: 'btn', href: '#/learn' }, '개념 학습으로')),
      wrong.length ? [h('h2', {}, `틀린 문제 ${wrong.length}개`), wrong.map((i) => questionCard(qs[i], i + 1, { review: { picked: picked(picks[i]) } }))] : null);
  }
  const picked = (p) => (p == null ? 0 : p);

  // ---------- 내 기출 불러오기 ----------
  function parseCSV(text) {
    const rows = []; let row = [], cur = '', q = false;
    text = text.replace(/^﻿/, '');
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (q) { if (ch === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += ch; }
      else if (ch === '"') q = true;
      else if (ch === ',') { row.push(cur); cur = ''; }
      else if (ch === '\n' || ch === '\r') { if (ch === '\r' && text[i + 1] === '\n') i++; row.push(cur); cur = ''; if (row.length > 1 || row[0]) rows.push(row); row = []; }
      else cur += ch;
    }
    if (cur || row.length) { row.push(cur); rows.push(row); }
    return rows;
  }
  const NAME2CODE = () => Object.fromEntries(DATA.subjects.map((s) => [s.name, s.code]));
  function toMine(rows) {
    const head = rows[0], col = (n) => head.indexOf(n);
    const need = ['연도', '회차', '과목', '문항번호', '문제', '보기1', '보기2', '보기3', '보기4', '정답'];
    const miss = need.filter((n) => col(n) < 0);
    if (miss.length) throw new Error('열이 없습니다: ' + miss.join(', '));
    const n2c = NAME2CODE(), out = [];
    for (const r of rows.slice(1)) {
      const code = n2c[r[col('과목')]], ans = parseInt(r[col('정답')], 10);
      if (!code || !(ans >= 1 && ans <= 4)) continue;
      const key = `${r[col('연도')]}|${r[col('회차')]}|${code}|${r[col('문항번호')]}`;
      const t = TAGS.tags[key];
      if (t && t[1]) continue; // 개정무효 문항 제외
      const restored = col('복원여부') >= 0 && r[col('복원여부')] === 'Y';
      out.push({ id: 'g|' + key, code, cid: t ? t[0] : null, grade: t && TAGS.concepts[t[0]] ? TAGS.concepts[t[0]][0] : null,
        q: `[${r[col('연도')]}년 ${r[col('회차')]}회${restored ? ' 복원' : ''} ${r[col('문항번호')]}번] ${r[col('문제')]}`,
        choices: [1, 2, 3, 4].map((k) => r[col('보기' + k)]), answer: ans, expl: '',
        status: col('정답확인상태') >= 0 ? r[col('정답확인상태')] : '' });
    }
    return out;
  }
  function importView(msg) {
    const file = h('input', { type: 'file', accept: '.csv,text/csv' });
    file.addEventListener('change', async () => {
      const f = file.files[0];
      if (!f) return;
      try {
        const qs = toMine(parseCSV(await f.text()));
        if (!qs.length) throw new Error('읽을 수 있는 문항이 없습니다.');
        await idb.set('mine', qs); MINE = qs;
        importView(`${qs.length}문항을 불러왔습니다.`);
      } catch (e) { importView('불러오지 못했습니다: ' + e.message); }
    });
    const by = MINE ? DATA.subjects.map((s) => `${s.name} ${MINE.filter((q) => q.code === s.code).length}`).join(' · ') : '';
    render(
      h('h1', {}, '내 기출 불러오기'),
      h('p', {}, '실제 기출 문제는 저작권 때문에 이 사이트에 싣지 않았습니다. 갖고 있는 기출 파일(1_원본데이터.csv)을 여기서 고르면 실제 기출로 문제 은행을 쓸 수 있습니다.'),
      h('p', { class: 'muted small' }, '파일은 이 브라우저 안에만 저장되고 어디로도 전송되지 않습니다. 다른 기기에서는 다시 불러와야 합니다.'),
      msg && h('div', { class: 'box' }, msg),
      h('div', { class: 'card' }, MINE ? h('p', {}, h('b', {}, `불러온 기출 ${MINE.length}문항`), h('br'), h('span', { class: 'small muted' }, by),
        h('br'), h('span', { class: 'small muted' }, `단골 개념 문항 ${MINE.filter((q) => q.grade === '단골').length}개 · 개정으로 답이 달라진 문항은 뺐습니다.`)) : h('p', { class: 'muted' }, '아직 불러온 파일이 없습니다.'), file),
      h('div', { class: 'btns' }, MINE && h('a', { class: 'btn primary', href: '#/quiz' }, '기출로 문제 풀기'),
        MINE && h('button', { class: 'btn', onclick: async () => { await idb.del('mine'); MINE = null; importView('불러온 기출을 지웠습니다.'); } }, '불러온 기출 지우기')),
      h('h2', {}, '필요한 열'),
      h('p', { class: 'small muted' }, '연도, 회차, 과목, 문항번호, 문제, 보기1~보기4, 정답 (선택: 복원여부, 정답확인상태). 연도·회차·과목·문항번호가 분석 자료와 같으면 문항마다 개념이 연결됩니다.'));
  }

  // ---------- 라우팅 ----------
  function route() {
    const [path, query] = (location.hash.slice(1) || '/').split('?');
    const p = path.split('/').filter(Boolean).map(decodeURIComponent);
    document.querySelectorAll('[data-nav]').forEach((a) => a.classList.toggle('on', a.dataset.nav === p[0]));
    if (p[0] === 'learn') return p[2] ? lesson(p[1], p[2]) : p[1] ? learnSubject(p[1]) : learnIndex();
    if (p[0] === 'quiz') return quizSetup(new URLSearchParams(query || ''));
    if (p[0] === 'import') return importView();
    return home();
  }

  Promise.all([fetch('data/content.json').then((r) => r.json()), fetch('data/tags.json').then((r) => r.json()), idb.get('mine').catch(() => null)])
    .then(([d, t, m]) => {
      DATA = d; TAGS = t; MINE = m || null;
      for (const s of d.subjects) { SUBJ[s.code] = s; for (const c of s.concepts) BY_CID[c.cid] = { ...c, code: s.code }; }
      window.addEventListener('hashchange', route);
      route();
    })
    .catch((e) => render(h('p', { class: 'fail' }, '자료를 불러오지 못했습니다: ' + e.message)));
})();
