// v0.106 语音分流复测：正则从页面取，「这条」指哪条与页面同逻辑
const fs = require('fs');
const html = fs.readFileSync('F:/Daodao/src/_apk/assets/dao.html', 'utf8');
const names = ['EXPLAIN_RE','NOTE_RE','NOTE_READ_RE','NOTE_MAIL_RE','NOTE_DONE_RE','NOTE_DEL_RE'];
const R = {};
for (const n of names) {
  const m = html.match(new RegExp('var ' + n + ' ?= ?(\\/.*?\\/[gimsuy]*);'));
  if (!m) { console.log('缺 ' + n); process.exit(1); }
  R[n] = eval(m[1]);
}
const guardSrc = 'text.length <= 14 && (/^(把|帮我|请|第)/.test(text) || /^(这条|那条|这件事|那件事)/.test(text)) && !/陪|聊|笑话|天气|吃饭|睡觉|你好|谢谢/.test(text)';
if (html.indexOf(guardSrc) < 0) { console.log('页面的判定串和测试不一致'); process.exit(1); }
const G1 = /^(把|帮我|请|第)/, G2 = /^(这条|那条|这件事|那件事)/, G3 = /陪|聊|笑话|天气|吃饭|睡觉|你好|谢谢/;

const LIST = [{id:'2',when:'2026-11-21 15:30',done:'0',text:'开会'},
              {id:'3',when:'2026-11-22 09:00',done:'0',text:'交材料'},
              {id:'9',when:'2026-11-23 10:00',done:'0',text:'体检'},
              {id:'4',when:'2026-11-22 08:00',done:'0',text:'打卡'}];
function noteStripCmd(t){ return String(t||'').replace(/把|帮我|请|这条|那条|一下|标记|已经|算|做完了|完成了|办完了|弄完了|搞定|搞定了|删掉|删除|去掉|拿掉|划掉|取消|别(再|又)?提醒|不用(再)?提醒|了|吧|。|，|、|！|？/g,'').replace(/\s+/g,''); }
function noteMatchTodo(t){
  const s = String(t||'');
  if (/第\s*([0-9]{1,3}|[一二三四五六七八九十]{1,3})\s*条/.test(s)) return 'id';
  const key = noteStripCmd(s);
  if (!key) return /这条|那条|这件事|那件事/.test(s) ? 'latest' : '';
  for (const it of LIST){ if(it.done==='1') continue; if(String(it.text).indexOf(key)>=0) return 'name'; }
  for (const it of LIST){ if(it.done==='1') continue; const x=String(it.text); if(x && key.indexOf(x)>=0) return 'name'; }
  if (/这条|那条|这件事|那件事/.test(s)) return 'latest';
  return '';
}
function route(t){
  if (/精确闹钟|闹钟不准|提醒不准|闹钟权限/.test(t)) return '闹钟设置';
  if (R.NOTE_MAIL_RE.test(t)) return '邮箱设置';
  if (R.NOTE_DONE_RE.test(t) || R.NOTE_DEL_RE.test(t)) {
    const hit = noteMatchTodo(t), isDone = R.NOTE_DONE_RE.test(t);
    if (hit === 'latest') return isDone ? '标记完成(最近一条)' : '删除(最近一条)';
    if (hit) return isDone ? '标记完成' : '删除';
    if (t.length <= 14 && (G1.test(t) || G2.test(t)) && !G3.test(t)) return '提示没找到';
  }
  if (R.NOTE_READ_RE.test(t)) return '念待办';
  if (R.NOTE_RE.test(t)) return '登记';
  if (R.EXPLAIN_RE.test(t)) return '讲题';
  return '闲聊';
}
const cases = [
  ['提醒我 明天九点 交材料','登记'],['记一下 后天 十点 体检','登记'],
  ['每天 早上八点 打卡','登记'],['每周日 十点 休息','登记'],['每月20号 九点 交房租','登记'],
  ['九点 交材料','登记'],['早上八点 打卡','登记'],['晚上八点半 交材料','登记'],
  ['开会做完了','标记完成'],['第3条删掉','删除'],['把体检去掉','删除'],
  ['别再提醒开会了','删除'],['打卡搞定了','标记完成'],
  ['这条做完了','标记完成(最近一条)'],['这条删掉','删除(最近一条)'],
  ['今天工作完成了，陪我聊会','闲聊'],['这个需求总算搞定了','闲聊'],
  ['把这件事删掉','删除(最近一条)'],['第7条做完了','标记完成'],
  ['念一下今天有什么','念待办'],['这题怎么做','讲题'],['今天累不累','闲聊'],
  ['提醒发到 a@b.com','邮箱设置'],['清空收件人','邮箱设置'],['说得对','闲聊']
];
let bad = 0;
for (const [t,w] of cases) {
  const got = route(t);
  if (got !== w) bad++;
  console.log((got===w?'ok  ':'BAD ') + t + '  → ' + got + (got===w?'':'  (期望 '+w+')'));
}
console.log('\n不符合预期 ' + bad + ' / ' + cases.length);
