// Jungto: 홈(강의 목록) · 읽기(원문/설명/연결) · 큰 그림 · 목차 · 보기 설정
// 강의 내용은 sync.js가 불러와 setContent()로 넘겨 줌 (Firebase, 또는 맥에서는 data/out)
// 읽던 곳·다 읽음·보기 설정은 이 기기에만 저장 (localStorage)

const STORE_KEY = 'jungto.state';
const MODES = { orig: '원문', exp: '설명', link: '연결' };
let S = { mode: 'exp', fs: 17, theme: 'auto', last: null, pos: {}, done: {} };
try { Object.assign(S, JSON.parse(localStorage.getItem(STORE_KEY)) || {}); } catch (e) {}
function save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(S)); } catch (e) {} }

let LECS = [];      // [{n, title, goals, orig, exp, link, origToc, expToc, linkToc, emap}]
let BIG = null;     // {themes:[{title, note, steps:[{n, text, sec}]}]}
let cur = null;     // 지금 읽는 강의

const $ = id => document.getElementById(id);
const home = $('home'), reader = $('reader'), big = $('big'), doc = $('doc');
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const lec = n => LECS.find(l => l.n === n);
// 대단원: 1~12는 실천적 불교사상, 그 뒤는 단원마다 1강부터 (옛 내용엔 unit·no가 없어 n을 씀)
const UNIT1 = '실천적 불교사상';
const unitOf = L => L.unit || UNIT1;
const noOf = L => L.no || L.n;
const nm = L => `${noOf(L)}강`;

function setContent(lectures, bigpicture) {
  LECS = lectures.slice().sort((a, b) => a.n - b.n);
  BIG = bigpicture || null;
  showHome();
}

function toast(t) {
  const m = $('msg');
  m.textContent = t;
  m.classList.add('show');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => m.classList.remove('show'), 2200);
}

// ---------------------------------------------------------------- 화면 바꾸기
function showOnly(el) {
  [home, reader, big, $('login')].forEach(x => x.classList.toggle('hidden', x !== el));
}

function showHome() {
  showOnly(home);
  cur = null;
  const r = $('resume');
  const L = S.last && lec(S.last.n);
  if (L) {
    const p = S.pos[L.n] || {};
    r.innerHTML = `<small>이어 읽기</small><b>${unitOf(L) === UNIT1 ? '' : esc(unitOf(L)) + ' '}${nm(L)} · ${esc(L.title)}</b><span>${MODES[p.mode] || '설명'} · ${esc(labelOf(L, p.mode, p.sec) || '처음부터')}</span>`;
    r.classList.remove('hidden');
  } else r.classList.add('hidden');
  $('bigBtn').classList.toggle('hidden', !BIG);
  let lastUnit = null;
  $('weeks').innerHTML = LECS.map(l => {
    const st = S.done[l.n] ? '✓ 다 읽음' : (S.pos[l.n] ? '읽는 중' : '');
    const head = unitOf(l) !== lastUnit ? `<div class="unit-h">${esc(unitOf(l))}</div>` : '';
    lastUnit = unitOf(l);
    return head + `<button class="week${S.done[l.n] ? ' done' : ''}" type="button" data-open="${l.n}"><span class="no">${noOf(l)}</span><span class="t"><b>${esc(l.title)}</b></span><span class="st">${st}</span></button>`;
  }).join('');
  const nDone = LECS.filter(l => S.done[l.n]).length;
  $('foot').textContent = LECS.length ? `강의 ${LECS.length}개 · 다 읽은 강의 ${nDone}개` : '아직 넣은 강의가 없어요';
  window.scrollTo(0, 0);
}

function labelOf(L, mode, sec) {
  if (!L || !sec) return '';
  const toc = tocOf(L, mode || 'exp');
  const t = toc.find(x => x.id === sec);
  return t ? t.label : '';
}
function tocOf(L, mode) {
  return mode === 'orig' ? L.origToc : mode === 'link' ? (L.linkToc || []) : L.expToc;
}

$('weeks').addEventListener('click', e => {
  const b = e.target.closest('[data-open]');
  if (b) openLecture(+b.dataset.open);
});
$('resume').addEventListener('click', () => S.last && openLecture(S.last.n));
$('back').addEventListener('click', showHome);

// ---------------------------------------------------------------- 읽기
function openLecture(n, mode, sec) {
  const L = lec(n);
  if (!L) return;
  cur = L;
  const p = S.pos[n] || {};
  S.mode = mode || p.mode || S.mode || 'exp';
  S.last = { n };
  save();
  showOnly(reader);
  $('ttl').textContent = `${nm(L)} · ${L.title}`;
  render();
  const target = sec || (mode ? null : p.sec);
  if (target) goSec(target); else window.scrollTo(0, 0);
  remember();
}

function render() {
  const L = cur;
  const top = `<div class="kicker">${esc(unitOf(L))} · ${nm(L)}</div><h1>${esc(L.title)}</h1>` +
    (L.goals && L.goals.length ? `<div class="box"><h2>학습 목표</h2><ul>${L.goals.map(g => `<li>${esc(g)}</li>`).join('')}</ul></div>` : '');
  let body;
  if (S.mode === 'orig') body = L.orig;
  else if (S.mode === 'link') {
    body = L.link
      ? `<p class="modehint">설명에서 앞 강의 이야기를 따로 모아 둔 곳이에요.</p>${L.link}`
      : `<div class="empty-note">${L.n === 1 ? '1강은 첫 강의라 앞 강의와 이어지는 이야기가 없어요.' : '이 강의는 따로 모아 둔 연결 이야기가 없어요.'}</div>`;
  } else body = L.exp;
  const next = lec(L.n + 1);
  doc.innerHTML = top + body +
    `<button class="done-btn" id="doneBtn" type="button">${S.done[L.n] ? `${nm(L)} 다 읽음 ✓` : `${nm(L)} 다 읽음`}</button>` +
    (next ? `<button class="next-btn" id="nextBtn" type="button">다음 강의 · ${unitOf(next) !== unitOf(L) ? esc(unitOf(next)) + ' ' : ''}${nm(next)} ${esc(next.title)}</button>` : '');
  document.querySelectorAll('#seg button').forEach(b => b.classList.toggle('on', b.dataset.m === S.mode));
  updateProg();
}

function anchors() { return [...doc.querySelectorAll('[data-sec]')]; }
function currentSec() {
  let c = null;
  for (const el of anchors()) {
    if (el.getBoundingClientRect().top <= 140) c = el; else break;
  }
  return c;
}
function barH() { return reader.querySelector('.bar').getBoundingClientRect().height; }
function goSec(id) {
  const el = doc.querySelector(`[data-sec="${id}"]`);
  if (!el) { window.scrollTo(0, 0); return; }
  window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - barH() - 8, behavior: 'auto' });
}

// 원문 ↔ 설명 ↔ 연결: 보던 자리를 따라감
function expToOrig(L, eid) { return L.emap[eid] || ''; }
function origToExp(L, oid) {
  const order = L.origToc.map(o => o.id);
  let i = order.indexOf(oid);
  for (; i >= 0; i--) {
    const hit = L.expToc.find(e => L.emap[e.id] === order[i]);
    if (hit) return hit.id;
  }
  return '';
}
function expToLink(L, eid) {
  const toc = L.linkToc || [];
  if (!eid) return '';
  // 지금 보던 설명 섹션 또는 그 앞의 가장 가까운 큰 섹션에서 옮긴 것
  const order = L.expToc.filter(e => (e.lv ?? 1) <= 1).map(e => e.id);
  const h2 = eid.split('-')[0];
  let i = order.indexOf(h2);
  for (; i >= 0; i--) {
    const hit = toc.find(l => l.e === order[i]);
    if (hit) return hit.id;
  }
  return '';
}
function linkToExp(L, lid) {
  const t = (L.linkToc || []).find(l => l.id === lid);
  return t && t.e ? t.e : '';
}
function switchMode(m) {
  if (m === S.mode || !cur) return;
  const c = currentSec();
  const id = c ? c.dataset.sec : '';
  let eid = '';
  if (id) eid = S.mode === 'exp' ? id : S.mode === 'orig' ? origToExp(cur, id) : linkToExp(cur, id);
  let target = '';
  if (m === 'exp') target = eid;
  else if (m === 'orig') target = eid ? expToOrig(cur, eid) : '';
  else target = expToLink(cur, eid);
  S.mode = m;
  save();
  render();
  if (target) goSec(target); else window.scrollTo(0, 0);
  remember();
}
$('seg').addEventListener('click', e => {
  const b = e.target.closest('button');
  if (b) switchMode(b.dataset.m);
});

// 스크롤: 진행 막대, 읽던 곳 기억
function updateProg() {
  const h = document.documentElement.scrollHeight - innerHeight;
  $('prog').style.width = (h > 0 ? Math.min(100, scrollY / h * 100) : 0) + '%';
}
function remember() {
  if (!cur) return;
  const c = currentSec();
  S.pos[cur.n] = { mode: S.mode, sec: c ? c.dataset.sec : '' };
  save();
}
let tick = 0;
window.addEventListener('scroll', () => {
  if (reader.classList.contains('hidden')) return;
  updateProg();
  clearTimeout(tick);
  tick = setTimeout(remember, 250);
}, { passive: true });

doc.addEventListener('click', e => {
  if (e.target.id === 'doneBtn') {
    S.done[cur.n] = !S.done[cur.n];
    save();
    e.target.textContent = S.done[cur.n] ? `${nm(cur)} 다 읽음 ✓` : `${nm(cur)} 다 읽음`;
    toast(S.done[cur.n] ? '다 읽음으로 표시했어요' : '다 읽음 표시를 지웠어요');
  }
  if (e.target.id === 'nextBtn') openLecture(cur.n + 1, S.mode);
});

// ---------------------------------------------------------------- 큰 그림
$('bigBtn').addEventListener('click', showBig);
$('bigBack').addEventListener('click', showHome);
function showBig() {
  if (!BIG) return;
  showOnly(big);
  $('bigDoc').innerHTML = `<p class="big-intro">강의를 넘나들며 이어지는 주제예요. 누르면 그 강의 설명의 그 자리로 가요.</p>` +
    BIG.themes.map(t => `<div class="theme"><h3>${esc(t.title)}</h3>${t.note ? `<p class="tnote">${esc(t.note)}</p>` : ''}` +
      t.steps.map(s => `<button class="step" type="button" data-n="${s.n}" data-sec="${esc(s.sec || '')}"${lec(s.n) ? '' : ' disabled'}><span class="sn">${lec(s.n) ? nm(lec(s.n)) : s.n + '강'}</span><span>${esc(s.text)}</span></button>`).join('') +
      `</div>`).join('');
  window.scrollTo(0, 0);
}
$('bigDoc').addEventListener('click', e => {
  const b = e.target.closest('.step');
  if (b && !b.disabled) openLecture(+b.dataset.n, 'exp', b.dataset.sec);
});

// ---------------------------------------------------------------- 목차 · 보기 설정
function openOv(id) {
  if (id === 'tocOv') buildToc();
  $(id).classList.add('show');
}
function closeOv(el) { el.classList.remove('show'); }
document.querySelectorAll('.ov').forEach(ov => ov.addEventListener('click', e => { if (e.target === ov) closeOv(ov); }));
$('tocBtn').addEventListener('click', () => openOv('tocOv'));
$('optBtn').addEventListener('click', () => openOv('optOv'));
$('homeOpt').addEventListener('click', () => openOv('optOv'));

function buildToc() {
  const L = cur;
  const c = currentSec();
  const toc = tocOf(L, S.mode);
  $('tocTitle').textContent = `목차 · ${MODES[S.mode]}`;
  $('toc').innerHTML = toc.length
    ? toc.map(t => `<a href="#" data-go="${t.id}" class="l${t.lv ?? 1}${c && c.dataset.sec === t.id ? ' cur' : ''}">${esc(t.label)}</a>`).join('')
    : '<p class="from">목차가 없어요.</p>';
  const on = $('toc').querySelector('.cur');
  if (on) setTimeout(() => on.scrollIntoView({ block: 'center' }), 0);
}
$('toc').addEventListener('click', e => {
  const a = e.target.closest('[data-go]');
  if (!a) return;
  e.preventDefault();
  closeOv($('tocOv'));
  goSec(a.dataset.go);
  remember();
});

function applyView() {
  document.documentElement.style.setProperty('--fs', S.fs + 'px');
  if (S.theme === 'auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', S.theme);
  const dark = S.theme === 'dark' || (S.theme === 'auto' && matchMedia('(prefers-color-scheme: dark)').matches);
  document.querySelector('meta[name="theme-color"]').setAttribute('content', dark ? '#1A1815' : '#F7F3EA');
  document.querySelectorAll('#fsBtns button').forEach(b => b.classList.toggle('on', +b.dataset.fs === S.fs));
  document.querySelectorAll('#thBtns button').forEach(b => b.classList.toggle('on', b.dataset.th === S.theme));
}
$('fsBtns').addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b) return;
  const c = cur && !reader.classList.contains('hidden') ? currentSec() : null;
  S.fs = +b.dataset.fs;
  save();
  applyView();
  if (c) goSec(c.dataset.sec);
});
$('thBtns').addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b) return;
  S.theme = b.dataset.th;
  save();
  applyView();
});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyView);
$('verNo').textContent = APP_VERSION;

// 시작 화면: 그림이 나타나고 약 1.4초 뒤 사라짐
(function () {
  const sp = $('splash');
  if (!sp) return;
  const img = new Image();
  let gone = false;
  const hide = () => { if (gone) return; gone = true; sp.classList.add('out'); setTimeout(() => sp.remove(), 750); };
  img.onload = () => setTimeout(hide, 1400);
  img.onerror = hide;
  img.src = 'splash.jpg';
  setTimeout(hide, 3500); // 그림이 늦게 오면 기다리지 않음
})();
applyView();
