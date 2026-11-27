#!/usr/bin/env python3
"""Jungto 내용 만들기 (맥에서만 씀)

data/raw/  : 드라이브·채팅에서 옮긴 원본 (원문 NN-orig*.md, 설명 NN-exp*.md)
data/diet.json : 강의별 정리 규칙 (설명에서 앞 강의 이야기를 '연결'로 옮김)
data/bigpicture.json : 큰 그림 (주제별로 여러 강의를 잇는 목록)
→ data/out/NN.json, data/out/bigpicture.json  (tools/upload.html이 Firebase에 올림)

data/ 폴더는 저작권 자료라 GitHub에 올리지 않는다 (.gitignore).
쓰는 법: python3 tools/build.py   (끝에 정리 규칙이 안 맞은 곳을 알려 줌)
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
OUT = os.path.join(ROOT, 'data', 'out')
warnings = []


def warn(n, msg):
    warnings.append(f'{n}강: {msg}')


# ---------------------------------------------------------------- 원본 읽기
def raw_path(n, kind):
    for name in (f'{n:02d}-{kind}.md', f'{n:02d}-{kind}-drive.md'):
        p = os.path.join(RAW, name)
        if os.path.exists(p):
            return p, name.endswith('-drive.md')
    return None, False


def unescape_drive(t):
    """구글 드라이브가 붙인 역슬래시 떼기"""
    t = t.replace('\\\\\\', '\\')
    t = re.sub(r'\\([*!~\[\]<>().\-_#|`])', r'\1', t)
    t = t.replace('\u00a0', ' ')
    return t


def fix_drive_tables(lines):
    """드라이브 표: 빈 머리줄 + :-: 줄 + 굵은 글씨 첫 줄 → 보통 표"""
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith('|') and i + 2 < len(lines) and re.match(r'^\|\s*:?-+:?\s*\|', lines[i + 1].strip()) \
                and not re.sub(r'[|\s]', '', ln):
            out.append(lines[i + 2])
            out.append('|' + '---|' * (lines[i + 2].count('|') - 1))
            i += 3
            continue
        out.append(ln)
        i += 1
    return out


def load_exp(n):
    p, drive = raw_path(n, 'exp')
    t = open(p, encoding='utf-8').read()
    if drive:
        t = unescape_drive(t)
        lines = [ln.rstrip() for ln in t.split('\n')]
        lines = fix_drive_tables(lines)
        t = '\n'.join(lines)
        t = re.sub(r'\n-{5,}\n', '\n---\n', t)
    return t


def load_orig(n):
    p, drive = raw_path(n, 'orig')
    t = open(p, encoding='utf-8').read()
    if drive:
        t = unescape_drive(t)
    t = t.replace('\u00a0', ' ')
    # 원문 문서 뒤에 붙은 다른 AI 설명([설명 및 해석])은 뺀다
    t = re.split(r'\n\s*-{10,}\s*\n', t)[0]
    return t


# ---------------------------------------------------------------- 글자 꾸밈
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\w)', r'<i>\1</i>', s)
    return s


def plain(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('**', '').replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    return s


def norm(s):
    """비교용: 꾸밈·띄어쓰기·따옴표 없앰"""
    s = plain(s)
    return re.sub(r'[\s"\'“”‘’「」『』.,!?·:()\[\]~\-…]', '', s)


# ---------------------------------------------------------------- 설명(마크다운) → 덩어리
def parse_md(text):
    """블록 목록: {t: h1|h2|h3|p|quote|ul|ol|table|hr, ...}"""
    lines = text.split('\n')
    blocks, i = [], 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        m = re.match(r'^(#{1,4})\s+(.*)$', s)
        if m:
            lvl = len(m.group(1))
            title = m.group(2).strip()
            title = re.sub(r'^\*\*(.*)\*\*$', r'\1', title)
            blocks.append({'t': 'h%d' % min(lvl, 4), 'md': title})
            i += 1
            continue
        if s.startswith('```'):
            # 그림처럼 줄을 맞춘 부분 (화살표 흐름도 등)
            buf = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                buf.append(lines[i].rstrip())
                i += 1
            i += 1
            blocks.append({'t': 'pre', 'md': '\n'.join(buf)})
            continue
        if re.match(r'^-{3,}$', s) or re.match(r'^\*{3,}$', s):
            blocks.append({'t': 'hr'})
            i += 1
            continue
        if s.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                r = lines[i].strip()
                if not re.match(r'^\|[\s:|-]+\|$', r):
                    cells = [c.strip() for c in r.strip('|').split('|')]
                    rows.append(cells)
                i += 1
            blocks.append({'t': 'table', 'rows': rows})
            continue
        if s.startswith('>'):
            buf = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                buf.append(lines[i].strip().lstrip('>').strip())
                i += 1
            blocks.append({'t': 'quote', 'md': '\n'.join(b for b in buf)})
            continue
        if re.match(r'^([-*+]|\d+\.)\s+', s):
            items, ordered = [], bool(re.match(r'^\d+\.', s))
            base = len(ln) - len(ln.lstrip())
            while i < len(lines):
                l2 = lines[i]
                s2 = l2.strip()
                if not s2:
                    # 빈 줄 뒤에도 목록이 이어지면 계속
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines) and re.match(r'^\s*([-*+]|\d+\.)\s+', lines[j]):
                        i = j
                        continue
                    break
                ind = len(l2) - len(l2.lstrip())
                m2 = re.match(r'^([-*+]|\d+\.)\s+(.*)$', s2)
                if m2 and ind <= base + 1:
                    items.append({'md': m2.group(2), 'sub': []})
                elif m2 and items:
                    items[-1]['sub'].append(m2.group(2))
                elif items:
                    items[-1]['md'] += ' ' + s2
                else:
                    break
                i += 1
            blocks.append({'t': 'ol' if ordered else 'ul', 'items': items})
            continue
        buf = [s]
        i += 1
        while i < len(lines):
            s2 = lines[i].strip()
            if not s2 or re.match(r'^(#{1,4}\s|>|\||([-*+]|\d+\.)\s|-{3,}$)', s2):
                break
            buf.append(s2)
            i += 1
        md = '\n'.join(buf)
        # 교재 문장을 통째로 따옴표에 넣은 문단 → 인용
        if re.match(r'^["“].*["”]$', plain(md).strip(), re.S) and len(plain(md)) < 400:
            blocks.append({'t': 'quote', 'md': md, 'q': True})
        else:
            blocks.append({'t': 'p', 'md': md})
    return blocks


def block_text(b):
    if b['t'] in ('ul', 'ol'):
        return ' '.join(it['md'] + ' ' + ' '.join(it['sub']) for it in b['items'])
    if b['t'] == 'table':
        return ' '.join(' '.join(r) for r in b['rows'])
    return b.get('md', '')


def render_block(b):
    t = b['t']
    if t in ('h2', 'h3', 'h4'):
        return f'<{t}>{inline(b["md"])}</{t}>'
    if t == 'pre':
        return '<pre class="flow">' + html.escape(b['md'], quote=False) + '</pre>'
    if t == 'hr':
        return ''
    if t == 'p':
        return '<p>' + inline(b['md']).replace('\n', '<br>') + '</p>'
    if t == 'quote':
        return '<p class="quote">' + inline(b['md']).replace('\n', '<br>') + '</p>'
    if t in ('ul', 'ol'):
        lis = []
        for it in b['items']:
            sub = ''
            if it['sub']:
                sub = '<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in it['sub']) + '</ul>'
            lis.append(f'<li>{inline(it["md"])}{sub}</li>')
        return f'<{t} class="dot">' + ''.join(lis) + f'</{t}>'
    if t == 'table':
        rows = b['rows']
        if not rows:
            return ''
        head = ''.join(f'<th>{inline(c)}</th>' for c in rows[0])
        body = ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in rows[1:])
        return f'<div class="tbl"><table><tr>{head}</tr>{body}</table></div>'
    return ''


# ---------------------------------------------------------------- 정리 규칙 적용
def split_sentences(md):
    parts = re.split(r'(?<=[.!?。])(?:\*\*)?\s+(?=\S)', md)
    # (?:\*\*)? 때문에 굵은 글씨 닫힘이 잘리지 않도록 다시 맞춤
    out = []
    pos = 0
    for p in parts:
        idx = md.find(p, pos)
        if idx > pos and out:
            out[-1] += md[pos:idx].rstrip()
        out.append(p)
        pos = idx + len(p)
    return [p.strip() for p in out if p.strip()]


def apply_diet(n, blocks, rules):
    """blocks에서 규칙대로 빼고, 뺀 것은 link 목록(섹션 제목, 블록)으로 모음"""
    link = []          # [(섹션 제목, block)]
    used = set()

    def sec_title_at(idx):
        sub = ''
        for j in range(idx, -1, -1):
            if blocks[j] and blocks[j]['t'] == 'h3' and not sub:
                sub = plain(blocks[j]['md'])
            if blocks[j] and blocks[j]['t'] in ('h1', 'h2') and j > 0:
                return plain(blocks[j]['md']) + ('\u0000' + sub if sub else '')
        return '들어가며'

    first_h2 = next((k for k, b in enumerate(blocks) if k > 0 and b['t'] in ('h1', 'h2')), len(blocks))

    for r in rules:
        kind, _, arg = r.partition(':')
        arg = arg.strip()
        if kind == 'I':
            keep = [x.partition(':')[2].strip() for x in rules if x.startswith('K:')]
            moved = []
            for k in range(1, first_h2):
                b = blocks[k]
                if not b or b['t'] in ('hr', 'h1'):
                    continue
                if any(norm(kp) in norm(block_text(b)) for kp in keep):
                    continue
                moved.append(b)
                blocks[k] = None
            for b in moved:
                link.append(('들어가며 (앞 강의 요약)', b))
            if arg:
                blocks.insert(1, {'t': 'p', 'md': arg, 'intro': True})
                first_h2 += 1
            used.add(r)
            continue
        if kind in ('K', 'M'):
            used.add(r)
            continue
        a = norm(arg)
        hit = False
        for k, b in enumerate(blocks):
            if b is None or b['t'] in ('h1', 'hr'):
                continue
            if kind == 'H':
                if b['t'] == 'h2' and a in norm(b['md']):
                    end = k + 1
                    while end < len(blocks) and not (blocks[end] and blocks[end]['t'] == 'h2'):
                        end += 1
                    title = plain(b['md'])
                    for j in range(k + 1, end):
                        if blocks[j] and blocks[j]['t'] != 'hr':
                            link.append((title, blocks[j]))
                        blocks[j] = None
                    blocks[k] = None
                    hit = True
                    break
                continue
            if kind == 'C':
                if b['t'] == 'table' and b['rows']:
                    head = [norm(c) for c in b['rows'][0]]
                    if a in head:
                        ci = head.index(a)
                        b['rows'] = [row[:ci] + row[ci + 1:] for row in b['rows']]
                        hit = True
                continue
            if a not in norm(block_text(b)):
                continue
            if kind == 'P':
                link.append((sec_title_at(k), b))
                blocks[k] = None
                hit = True
                break
            if kind == 'S':
                if b['t'] in ('p', 'quote'):
                    sents = split_sentences(b['md'])
                    keep, cut = [], []
                    for s in sents:
                        (cut if a in norm(s) and not cut else keep).append(s)
                    if cut:
                        link.append((sec_title_at(k), {'t': 'p', 'md': ' '.join(cut)}))
                        if keep:
                            b['md'] = ' '.join(keep)
                        else:
                            blocks[k] = None
                        hit = True
                        break
                if b['t'] in ('ul', 'ol'):
                    for it in b['items']:
                        if a in norm(it['md']):
                            sents = split_sentences(it['md'])
                            cut = [s for s in sents if a in norm(s)][:1]
                            keep = [s for s in sents if s not in cut]
                            link.append((sec_title_at(k), {'t': 'p', 'md': ' '.join(cut)}))
                            it['md'] = ' '.join(keep)
                            hit = True
                            break
                    if hit:
                        break
                if b['t'] == 'table':
                    for row in b['rows'][1:]:
                        for ci, c in enumerate(row):
                            if a in norm(c):
                                link.append((sec_title_at(k), {'t': 'p', 'md': c}))
                                row[ci] = ''
                                hit = True
                                break
                        if hit:
                            break
                    if hit:
                        break
        if hit or kind == 'C':
            used.add(r)
        if not hit:
            warn(n, f'규칙이 맞지 않음 → {r[:60]}')
    return [b for b in blocks if b is not None], link


# ---------------------------------------------------------------- 설명 HTML
def build_exp(n, text, rules):
    blocks = parse_md(text)
    title_md = blocks[0]['md'] if blocks and blocks[0]['t'] == 'h1' else ''
    blocks, link = apply_diet(n, blocks, rules)
    out, secs, sid = [], [], 0
    secs_h2, sub = [], 0
    open_sec = False
    seen_h1 = False
    for b in blocks:
        if b['t'] == 'h1':
            if not seen_h1:
                seen_h1 = True
                continue
            b = dict(b, t='h2', big=True)   # 강의 안의 큰 묶음 (첫째 계율, 둘째 계율 …)
        if b['t'] == 'hr':
            continue
        if b['t'] == 'h2':
            if open_sec:
                out.append('</section>')
            sid += 1
            label = plain(b['md'])
            out.append(f'<section class="sec" data-sec="e{sid}" data-label="{html.escape(label)}">')
            out.append(f'<h2 class="big">{inline(b["md"])}</h2>' if b.get('big') else render_block(b))
            secs.append({'id': f'e{sid}', 'label': label, 'text': '', 'lv': 0 if b.get('big') else 1})
            secs_h2.append(f'e{sid}')
            sub = 0
            open_sec = True
            continue
        if not open_sec:
            out.append('<section class="sec" data-sec="e0" data-label="들어가며">')
            secs.append({'id': 'e0', 'label': '들어가며', 'text': '', 'lv': 1})
            secs_h2.append('e0')
            sub = 0
            open_sec = True
        if b['t'] == 'h3':
            sub += 1
            label = plain(b['md'])
            hid = f'{secs_h2[-1]}-{sub}'
            out.append(f'<h3 data-sec="{hid}" data-label="{html.escape(label)}">{inline(b["md"])}</h3>')
            secs.append({'id': hid, 'label': label, 'text': '', 'lv': 2})
            continue
        out.append(render_block(b))
        if b['t'] == 'quote':
            secs[-1].setdefault('quotes', []).append(b['md'])
        elif b['t'] == 'p':
            secs[-1]['text'] += ' ' + b['md']
    if open_sec:
        out.append('</section>')
    return ''.join(out), secs, link, title_md


def build_link(n, link, exp_secs):
    """연결 탭: 설명 섹션 이름별로 옮긴 이야기 + 맨 끝 연결 표"""
    if not link:
        return '', []
    groups, order = {}, []
    label_to_id = {s['label']: s['id'] for s in exp_secs if s.get('lv', 1) <= 1}
    for title, b in link:
        title, _, sub = title.partition('\u0000')
        b = dict(b, sub=sub)
        if title not in groups:
            groups[title] = []
            order.append(title)
        groups[title].append(b)
    out, secs = [], []
    for k, title in enumerate(order):
        lid = 'l%d' % k
        eid = label_to_id.get(title, '')
        is_table = '연결' in title and all(b['t'] == 'table' for b in groups[title])
        label = '앞 강의와 연결 (표)' if is_table else title
        out.append(f'<section class="sec" data-sec="{lid}" data-e="{eid}" data-label="{html.escape(label)}">')
        out.append(f'<h2>{inline(label)}</h2>')
        if not is_table and title != '들어가며 (앞 강의 요약)':
            out.append('<p class="from">설명의 이 부분에서 옮겼어요</p>')
        last_sub = ''
        for b in groups[title]:
            if b.get('sub') and b['sub'] != last_sub:
                out.append(f'<p class="subfrom">{inline(b["sub"])}</p>')
                last_sub = b['sub']
            out.append(render_block(b))
        out.append('</section>')
        secs.append({'id': lid, 'label': label, 'e': eid})
    return ''.join(out), secs


# ---------------------------------------------------------------- 원문 → HTML
CIRC = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱'


def tagify(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'【\s*([^】]+?)\s*】', r'<span class="tagk">\1</span>', s)
    return s


def build_orig(n, text):
    lines = [ln.rstrip() for ln in text.split('\n')]
    nonempty = [ln.strip() for ln in lines if ln.strip()]
    # 머리: "N강", 제목(1~2줄), 학습 목표
    k = 0
    unit = ''
    if len(nonempty) > 1 and not re.match(r'^\d+강$', nonempty[0]) and re.match(r'^\d+강$', nonempty[1]):
        unit = nonempty[0]   # 대단원 이름 (예: 인간 붓다)
        k = 1
    if re.match(r'^\d+강$', nonempty[k]):
        k += 1
    title_lines = []
    while k < len(nonempty) and nonempty[k] != '학습 목표':
        title_lines.append(nonempty[k])
        k += 1
    k += 1
    goals = []
    while k < len(nonempty) and not nonempty[k].startswith('주제 질문'):
        goals.append(nonempty[k].lstrip('▶').strip())
        k += 1
    while k < len(nonempty) and nonempty[k] in ('주제 질문 나누기', '법문 나누기', '수행 연습 나누기'):
        k += 1
    body = nonempty[k:]
    # 빈 줄 바로 뒤에 오는 줄 (경전 인용 같은 긴 글이 앞 항목에 붙지 않게)
    after_blank, prev_blank = [], False
    for ln in lines:
        if not ln.strip():
            prev_blank = True
            continue
        after_blank.append(prev_blank)
        prev_blank = False
    after_blank = after_blank[k:]

    out, secs = [], []
    part_no, sub_no = 0, 0
    cur_list = None   # 'sq' 목록을 열어 둔 상태
    in_numlist = False
    sec_open = False

    def close_list():
        nonlocal cur_list
        if cur_list:
            out.append('</ul>')
            cur_list = None

    def open_sec(sid, label, h):
        nonlocal sec_open
        close_list()
        if sec_open:
            out.append('</section>')
        out.append(f'<section class="sec" data-sec="{sid}" data-label="{html.escape(label)}">{h}')
        sec_open = True

    def is_heading_line(s):
        # 번호 없는 큰 제목은 정해진 것만 (수행문·사홍서원·계본·"제목 | 부제")
        if s[0] in CIRC:
            return False
        return s in ('수행문', '사홍서원') or s.endswith('계본') or (' | ' in s and len(s) < 40)

    for idx, s in enumerate(body):
        raw = s
        m_part = re.match(r'^(\d+)\.\s*(.+)$', s)
        if m_part and not in_numlist:
            part_no += 1
            sub_no = 0
            label = s
            open_sec(f'o{part_no}', label, f'<h2 class="part">{tagify(s)}</h2>')
            secs.append({'id': f'o{part_no}', 'label': label, 'lv': 1})
            continue
        if m_part and in_numlist == 'sub':
            sub_no += 1
            sid = f'o{part_no}-{sub_no}'
            open_sec(sid, s, f'<h3>{tagify(s)}</h3>')
            secs.append({'id': sid, 'label': s, 'lv': 2})
            continue
        if m_part and in_numlist:
            close_list()
            out.append(f'<p class="num"><b>{m_part.group(1)}.</b> {tagify(m_part.group(2))}</p>')
            continue
        m_sub = re.match(r'^(\d+)\)\s*(.+)$', s)
        if m_sub:
            sub_no += 1
            sid = f'o{part_no}-{sub_no}'
            open_sec(sid, s, f'<h3>{tagify(s)}</h3>')
            secs.append({'id': sid, 'label': re.sub(r'【.*?】', '', s).strip(), 'lv': 2})
            continue
        # 번호 없는 큰 제목 (수행문, 사홍서원, 발심행자 18계본, 십이연기 …)
        if is_heading_line(s):
            part_no += 1
            sub_no = 0
            label = s.replace(' | ', ' · ')
            in_numlist = 'list' if '계본' in s else ('sub' if ' | ' in s and '십이연기' in s else False)
            open_sec(f'o{part_no}', label, f'<h2 class="part">{tagify(label)}</h2>')
            secs.append({'id': f'o{part_no}', 'label': label, 'lv': 1})
            continue
        if s.startswith('[') and s.endswith(']'):
            close_list()
            out.append(f'<h4>{tagify(s.strip("[] "))}</h4>')
            continue
        m_pt = re.match(r'^\((\d+)\)\s*(.+)$', s)
        if m_pt:
            close_list()
            out.append(f'<p class="pt">{tagify(s)}</p>')
            continue
        if s.startswith('■'):
            if not cur_list:
                out.append('<ul class="sq">')
                cur_list = 'sq'
            out.append(f'<li>{tagify(s.lstrip("■").strip())}</li>')
            continue
        if s.startswith('▶') or s.startswith('→'):
            close_list()
            out.append(f'<p class="arrow">{tagify(s)}</p>')
            continue
        if re.match(r'^예\s', s):
            close_list()
            out.append(f'<p class="ex"><span>예</span>{tagify(s[1:].strip())}</p>')
            continue
        if s.startswith(':') or (s.startswith('(') and s.endswith(')') and cur_list):
            # 앞 줄에 붙는 작은 설명
            if out and out[-1].endswith('</li>'):
                out[-1] = out[-1][:-5] + f'<small>{tagify(s)}</small></li>'
            else:
                out.append(f'<p class="small">{tagify(s)}</p>')
            continue
        if s[0] in CIRC:
            close_list()
            if len(re.findall('[' + CIRC + ']', s)) >= 3:
                items = [x.strip() for x in re.split('[' + CIRC + ']', s) if x.strip()]
                out.append('<div class="emo">' + ''.join(f'<span>{CIRC[i]} {tagify(x)}</span>' for i, x in enumerate(items)) + '</div>')
            else:
                out.append(f'<p class="ci">{tagify(s)}</p>')
            continue
        if s.startswith('- ') and ' | ' in s:
            # 표 한 줄: "- 이름 : 값 | 칸 이름: 값 | …"
            close_list()
            cells = [c.strip() for c in s[2:].split(' | ')]
            name, _, first = cells[0].partition(' : ')
            heads, vals = ['', ''], [name.strip(), first.strip()]
            for c in cells[1:]:
                h, _, v = c.partition(':')
                heads.append(h.strip())
                vals.append(v.strip())
            row = '<tr>' + ''.join(f'<td>{tagify(v)}</td>' for v in vals) + '</tr>'
            if out and out[-1].endswith('</tbody></table></div>'):
                out[-1] = out[-1][:-len('</tbody></table></div>')] + row + '</tbody></table></div>'
            else:
                head = '<tr>' + ''.join(f'<th>{tagify(h)}</th>' for h in heads) + '</tr>'
                out.append(f'<div class="tbl"><table><thead>{head}</thead><tbody>{row}</tbody></table></div>')
            continue
        if s.startswith('- ') or s.startswith('* '):
            close_list()
            out.append(f'<p class="dash">{tagify(s[2:])}</p>')
            continue
        # 경전 이름 『…』 줄
        if s.startswith('『') and s.endswith('』'):
            close_list()
            out.append(f'<p class="src">{tagify(s)}</p>')
            continue
        # 빈 줄 뒤에서 시작하는 긴 글은 새 문단 (앞 목록에 붙이지 않음)
        if after_blank[idx] and len(s) > 60:
            close_list()
            out.append(f'<p class="line">{tagify(s)}</p>')
            continue
        # 보통 줄: 목록 안이면 앞 항목에 이어 붙임
        if cur_list and out[-1].endswith('</li>'):
            out[-1] = out[-1][:-5] + '<br>' + tagify(s) + '</li>'
            continue
        if out and out[-1].startswith('<p class="line">') and not re.match(r'^["“]', s):
            out[-1] = out[-1][:-4] + '<br>' + tagify(s) + '</p>'
            continue
        out.append(f'<p class="line">{tagify(s)}</p>')
    close_list()
    if sec_open:
        out.append('</section>')
    title = ' '.join(title_lines)
    return ''.join(out), secs, title, goals, unit


# ---------------------------------------------------------------- 원문 ↔ 설명 맞추기
def map_sections(exp_secs, orig_html, orig_secs):
    """설명 섹션 속 교재 인용문을 원문에서 찾아 같은 자리끼리 짝지음"""
    chunks = re.findall(r'<section class="sec" data-sec="([^"]+)"[^>]*>(.*?)</section>', orig_html, re.S)
    nchunks = [(sid, norm(c)) for sid, c in chunks]

    def find(q):
        nq = norm(q)
        for piece in (nq[:18], nq[-18:]):
            if len(piece) < 7:
                continue
            for sid, nc in nchunks:
                if piece in nc:
                    return sid
        return None

    own = {}
    for s in exp_secs:
        cands = [x for x in s.get('quotes', [])]
        cands += re.findall(r'["“]([^"”]{8,})["”]', s.get('text', ''))
        for q in cands:
            f = find(q)
            if f:
                own[s['id']] = f
                break
    emap = {}
    last = chunks[0][0] if chunks else ''
    for i, s in enumerate(exp_secs):
        m = own.get(s['id'])
        if not m and s.get('lv', 1) <= 1:
            # 큰 제목에 인용이 없으면 바로 아래 소제목의 짝을 씀
            for t in exp_secs[i + 1:]:
                if t.get('lv', 1) <= 1:
                    break
                if own.get(t['id']):
                    m = own[t['id']]
                    break
        emap[s['id']] = m or last
        last = emap[s['id']]
    return emap


# ---------------------------------------------------------------- 실행
def main():
    diet = json.load(open(os.path.join(ROOT, 'data', 'diet.json'), encoding='utf-8')) \
        if os.path.exists(os.path.join(ROOT, 'data', 'diet.json')) else {}
    os.makedirs(OUT, exist_ok=True)
    index = []
    unit, no = '실천적 불교사상', 0
    for n in range(1, 41):
        if not raw_path(n, 'orig')[0] or not raw_path(n, 'exp')[0]:
            continue
        orig_html, orig_secs, title, goals, unit_name = build_orig(n, load_orig(n))
        # 대단원: 원문 맨 위에 이름이 있으면 새 단원 시작, 강의 번호는 단원 안에서 1부터
        if unit_name and unit_name != unit:
            unit, no = unit_name, 0
        no += 1
        exp_html, exp_secs, link, exp_title = build_exp(n, load_exp(n), diet.get(str(n), []))
        link_html, link_secs = build_link(n, link, exp_secs)
        emap = map_sections(exp_secs, orig_html, orig_secs)
        for r in diet.get(str(n), []):
            # M: 자동 짝이 틀린 곳 바로잡기 (예: "M: e4-1=o3-1")
            if r.startswith('M:'):
                e, _, o = r[2:].strip().partition('=')
                emap[e.strip()] = o.strip()
        for s in exp_secs:
            s.pop('text', None)
            s.pop('quotes', None)
        doc = {
            'n': n, 'unit': unit, 'no': no, 'title': title, 'goals': goals,
            'orig': orig_html, 'origToc': orig_secs,
            'exp': exp_html, 'expToc': exp_secs,
            'link': link_html, 'linkToc': link_secs,
            'emap': emap,
        }
        json.dump(doc, open(os.path.join(OUT, f'{n:02d}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        index.append((n, title, len(orig_html), len(exp_html), len(link_html)))
    bp = os.path.join(ROOT, 'data', 'bigpicture.json')
    if os.path.exists(bp):
        big = json.load(open(bp, encoding='utf-8'))
        big.pop('_설명', None)
        tocs = {}
        for t in big['themes']:
            for st in t['steps']:
                if st['n'] not in tocs:
                    tocs[st['n']] = json.load(open(os.path.join(OUT, '%02d.json' % st['n']), encoding='utf-8'))['expToc']
                hit = next((x['id'] for x in tocs[st['n']] if norm(st['at']) in norm(x['label'])), None)
                if not hit:
                    warn(st['n'], f'큰 그림 자리를 못 찾음 → {st["at"]}')
                st['sec'] = hit or ''
        json.dump(big, open(os.path.join(OUT, 'bigpicture.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    for row in index:
        print('%2d강 %-24s 원문 %6d  설명 %6d  연결 %6d' % row)
    if warnings:
        print('\n확인할 것:')
        for w in warnings:
            print(' -', w)
    return 1 if warnings else 0


if __name__ == '__main__':
    sys.exit(main())
