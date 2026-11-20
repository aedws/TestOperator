"""cbtbank.kr 시험 페이지(HTML 파일)를 문항 리스트(JSON)로 변환한다.
사용: python3 -I parse_cbtbank.py <html> <out.json>
"""
import sys, re, json, html

def clean(s):
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'<img[^>]*>', '[그림]', s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()

def parse(t):
    out = []
    # 과목 제목 위치
    subs = [(m.start(), clean(m.group(1))) for m in
            re.finditer(r'<p class="text-center text-dark">(\d과목:[^<]+)</p>', t)]
    for m in re.finditer(r'question-id="([^"]+)" question-num="(\d+)">(.*?)<span class="exam-cpercent">(.*?)</span>', t, re.S):
        body = m.group(3)
        subj = [s for p, s in subs if p < m.start()][-1].split(':', 1)[1].strip()
        title = re.search(r'<p class="exam-title">(.*?)</p>\s*</div>\s*</div>\s*<div class="row"><div class="col-12 question-choice">', body, re.S)
        qraw = title.group(1) if title else body.split('question-choice')[0]
        qraw = re.sub(r'<span class="exam-number">\d+</span>\.', '', qraw, count=1)
        ol = re.search(r'<ol class="circlednumbers" correct="(\d*)">(.*?)</ol>', body, re.S)
        choices = [c for c in re.findall(r'<li[^>]*>(.*?)</li>', ol.group(2), re.S)]
        pre = body.split('<ol class="circlednumbers"')[0]
        rate = re.search(r'(\d+)%', m.group(4))
        out.append({
            'id': m.group(1), 'num': int(m.group(2)), 'subject': subj,
            'question': clean(qraw), 'choices': [clean(c) for c in choices],
            'answer': ol.group(1),
            'has_image': bool(re.search(r'<img', pre + ol.group(2))),
            'correct_rate': int(rate.group(1)) if rate else None,
        })
    return out

if __name__ == '__main__':
    t = open(sys.argv[1], encoding='utf-8', errors='replace').read()
    q = parse(t)
    json.dump(q, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(q), Counter(x['subject'] for x in q))
