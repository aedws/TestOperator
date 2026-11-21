"""기출 원문을 비밀번호로 암호화해 docs/data/mine.enc 로 만든다(AES-256-GCM, 키는 PBKDF2-SHA256).
비밀번호는 환경변수 MINE_PASSWORD 로만 받고 어디에도 저장하지 않는다.
사용: MINE_PASSWORD='...' python3 scripts/encrypt_mine.py"""
import os, json, csv, gzip, base64, re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITER = 600_000
CODE = {'소방원론': 'wonron', '소방전기일반': 'jeongi', '소방관계법규': 'beopgyu', '소방전기시설의 구조 및 원리': 'gujo'}
pw = os.environ['MINE_PASSWORD']
rd = lambda p: list(csv.DictReader(open(os.path.join(ROOT, p), encoding='utf-8-sig')))
grade = {r['개념ID']: r['등급'] for r in rd('output/2_개념빈도표.csv')}
tags = {(int(t['회차순번']), int(t['문항번호'])): t for t in rd('data/tags/tags.csv')}
out = []
for q in json.load(open(os.path.join(ROOT, 'data/raw/dataset.json'), encoding='utf-8')):
    t = tags[(q['order'], q['num'])]
    if t['개정무효'] == 'Y':
        continue
    code = CODE[q['subject']]
    out.append({'id': f"g|{q['year']}|{q['round']}|{code}|{q['num']}", 'code': code, 'cid': t['개념ID'], 'grade': grade.get(t['개념ID']),
                'q': f"[{q['year']}년 {q['round']}회{' 복원' if q['restored'] == 'Y' else ''} {q['num']}번] {q['question']}",
                'choices': q['choices'], 'answer': int(q['answer']), 'expl': q['hint'], 'status': q['status'],
                'img': bool(re.search(r'\[그림\]', q['question'] + ''.join(q['choices'])))})
plain = gzip.compress(json.dumps(out, ensure_ascii=False, separators=(',', ':')).encode(), 9)
salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pw.encode())
ct = AESGCM(key).encrypt(iv, plain, None)
b64 = lambda b: base64.b64encode(b).decode()
json.dump({'v': 1, 'kdf': 'PBKDF2-SHA256', 'iter': ITER, 'salt': b64(salt), 'iv': b64(iv), 'ct': b64(ct)},
          open(os.path.join(ROOT, 'docs/data/mine.enc'), 'w'))
print(len(out), '문항 /', len(ct) // 1024, 'KB / 그림 빠진 문항', sum(q['img'] for q in out))
