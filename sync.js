// Jungto: 로그인 + 강의 내용 불러오기 (Firebase Auth + Firestore)
//  - 클라우드 위치: lectures/{01..} 문서 = 강의 하나 (원문·설명·연결), meta/bigpicture = 큰 그림
//    (tools/upload.html로 올림. 누가 읽을 수 있는지는 firestore.rules에서 내 계정만 허락)
//  - sync-config.js 설정값이 비어 있으면 로그인 없이 이 컴퓨터의 data/out/ 폴더에서 읽음 (맥에서 만들며 확인용)
//    data/ 폴더는 저작권 자료라 GitHub에 올리지 않으므로, 인터넷 주소에서는 Firebase를 연결해야 내용이 보임

const cloud = { auth: null, db: null, user: null };
const UID_KEY = 'jungto.uid';
function cloudConfigured() { return !!FIREBASE_CONFIG.apiKey; }

function loadingScreen(text) {
  showOnly(home);
  $('weeks').innerHTML = `<div class="loading">${text}</div>`;
  $('resume').classList.add('hidden');
  $('bigBtn').classList.add('hidden');
  $('foot').textContent = '';
}

function boot() {
  if (!cloudConfigured()) return loadLocal();
  if (!window.firebase) return loadingScreen('인터넷 연결을 확인해 주세요.');
  firebase.initializeApp(FIREBASE_CONFIG);
  cloud.auth = firebase.auth();
  cloud.db = firebase.firestore();
  cloud.db.settings({ experimentalAutoDetectLongPolling: true, merge: true }); // Safari·아이폰에서 연결이 멈추는 것 막기
  cloud.db.enablePersistence({ synchronizeTabs: true }).catch(() => {});      // 한 번 받은 내용은 기기에 보관
  cloud.auth.getRedirectResult().catch(showLoginError);
  if (localStorage.getItem(UID_KEY)) loadingScreen('강의를 불러오는 중…');
  else showLogin();
  cloud.auth.onAuthStateChanged(user => {
    if (user) startCloud(user);
    else showLogin();
  });
}

// 맥에서 만들 때: data/out/NN.json 직접 읽기
function loadLocal() {
  loadingScreen('맥에 있는 강의를 읽는 중…');
  const ns = [];
  for (let n = 1; n <= 40; n++) ns.push(n);
  Promise.all(ns.map(n => fetch(`data/out/${String(n).padStart(2, '0')}.json`, { cache: 'no-store' })
    .then(r => r.ok ? r.json() : null).catch(() => null)))
    .then(list => fetch('data/out/bigpicture.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null)
      .then(bigp => {
        const lectures = list.filter(Boolean);
        if (!lectures.length) return loadingScreen('강의 파일이 없어요.<br>Firebase 연결(sync-config.js)을 확인해 주세요.');
        setContent(lectures, bigp);
      }));
}

// ---------- 로그인 ----------
function showLogin(msg) {
  showOnly($('login'));
  $('loginError').textContent = msg || '';
  $('loginError').classList.toggle('hidden', !msg);
}
function showLoginError(err) {
  console.warn(err);
  showLogin('로그인하지 못했어요. 잠시 뒤 다시 해 주세요.' + (err && err.code ? ` (${err.code})` : ''));
}
$('loginBtn').addEventListener('click', () => {
  if (!cloud.auth) return;
  const provider = new firebase.auth.GoogleAuthProvider();
  provider.setCustomParameters({ prompt: 'select_account' });
  cloud.auth.signInWithPopup(provider).catch(err => {
    // 팝업이 막힌 환경(홈 화면 앱 등)이면 페이지 이동 방식으로 다시
    if (err.code === 'auth/popup-blocked' || err.code === 'auth/operation-not-supported-in-this-environment') {
      return cloud.auth.signInWithRedirect(provider).catch(showLoginError);
    }
    if (err.code !== 'auth/popup-closed-by-user' && err.code !== 'auth/cancelled-popup-request') showLoginError(err);
  });
});

// ---------- 강의 불러오기 ----------
function startCloud(user) {
  cloud.user = user;
  try { localStorage.setItem(UID_KEY, user.uid); } catch (e) {}
  $('acct').classList.remove('hidden');
  $('acctEmail').textContent = user.email || '';
  if (!LECS.length) loadingScreen('강의를 불러오는 중…<br>처음 한 번은 조금 걸려요.');
  const slow = setTimeout(() => {
    if (!LECS.length) loadingScreen('강의를 불러오지 못하고 있어요.<br>인터넷 연결을 확인하고 앱을 다시 열어 주세요.');
  }, 20000);
  Promise.all([
    cloud.db.collection('lectures').get(),
    cloud.db.collection('meta').doc('bigpicture').get().catch(() => null)
  ]).then(([snap, bp]) => {
    clearTimeout(slow);
    const lectures = [];
    snap.forEach(d => lectures.push(d.data()));
    if (!lectures.length) return loadingScreen('아직 올린 강의가 없어요.<br>맥에서 tools/upload.html로 올려 주세요.');
    const keep = cur ? { n: cur.n } : null;
    setContent(lectures, bp && bp.exists ? bp.data() : null);
    if (keep) openLecture(keep.n);
  }).catch(err => {
    clearTimeout(slow);
    console.warn(err);
    if (err.code === 'permission-denied') {
      try { localStorage.removeItem(UID_KEY); } catch (e) {}
      cloud.auth.signOut();
      showLogin('이 계정은 사용할 수 없어요.');
    } else loadingScreen('강의를 불러오지 못했어요.<br>인터넷 연결을 확인하고 앱을 다시 열어 주세요.');
  });
}

$('logoutBtn').addEventListener('click', () => {
  if (!cloud.auth) return;
  try { localStorage.removeItem(UID_KEY); } catch (e) {}
  closeOv($('optOv'));
  LECS = [];
  $('acct').classList.add('hidden');
  cloud.auth.signOut();
});

boot();
