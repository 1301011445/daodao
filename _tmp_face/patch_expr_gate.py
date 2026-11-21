# -*- coding: utf-8 -*-
"""表情白名单：只有「表情图跟立绘是同一个角色、同一画风」的形象才换表情图。
其余形象（橘猫/白兔/狐狸/熊猫/蓝发/黑发/机械）一换表情就变成动物/卡通/半身图，宁可不换。"""
import io

SRC = r'F:\Daodao\src\_apk\assets\dao.html'
html = io.open(SRC, encoding='utf-8').read()

old = """  function spriteFor(sp) {
    if (emo >= 0 && emoLeft > 0) {"""
new = """  // v0.107：表情图白名单。0 橘猫/1 白兔/2 狐狸/3 熊猫 的表情是动物卡通，6 蓝发/11 机械是另一种画风，
  // 7 黑发只有头肩特写——这些形象一律不换表情图，宁可只靠姿势和动作，也不要"少女一秒变熊猫"。
  var EXPR_OK = { 4: 1, 5: 1, 8: 1, 9: 1, 10: 1 };
  function spriteFor(sp) {
    if (emo >= 0 && emoLeft > 0 && EXPR_OK[sp]) {"""
assert old in html
html = html.replace(old, new)

io.open(SRC, 'w', encoding='utf-8', newline='').write(html)
print('手机端白名单写完')
