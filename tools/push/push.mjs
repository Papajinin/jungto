// 맥에서 바로 Firebase에 강의 올리기 (브라우저 로그인 없이)
// 열쇠: data/firebase-key.json (Firebase 서비스 계정 키. GitHub에 절대 안 올림, data/는 .gitignore)
// 쓰는 법: node tools/push/push.mjs          → data/out의 모든 강의 + 큰 그림
//          node tools/push/push.mjs 13 14    → 그 강의만 (+ 큰 그림)
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import admin from 'firebase-admin';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const KEY = path.join(ROOT, 'data', 'firebase-key.json');
const OUT = path.join(ROOT, 'data', 'out');
if (!existsSync(KEY)) { console.error('열쇠 파일이 없어요: data/firebase-key.json'); process.exit(1); }

admin.initializeApp({ credential: admin.credential.cert(JSON.parse(readFileSync(KEY, 'utf8'))) });
const db = admin.firestore();

const only = process.argv.slice(2).map(Number).filter(Boolean);
const ns = only.length ? only : Array.from({ length: 40 }, (_, i) => i + 1);
const done = [];
for (const n of ns) {
  const id = String(n).padStart(2, '0');
  const f = path.join(OUT, id + '.json');
  if (!existsSync(f)) continue;
  await db.collection('lectures').doc(id).set(JSON.parse(readFileSync(f, 'utf8')));
  done.push(id);
}
const bp = path.join(OUT, 'bigpicture.json');
if (existsSync(bp)) await db.collection('meta').doc('bigpicture').set(JSON.parse(readFileSync(bp, 'utf8')));
console.log('올림:', done.join(', ') || '없음', existsSync(bp) ? '+ 큰 그림' : '');
process.exit(0);
