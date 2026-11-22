# -*- coding: utf-8 -*-
import sys, importlib
sys.path.insert(0, r'F:\Daodao\tools')
qb = importlib.import_module('问题库')
qb.register('手机端形象抠图有品红残影（头顶左侧一片紫、鞋底粉色光晕）',
            来源='2026-11-22 手机截图', 严重度='P2',
            说明='用户 12:14 截图里企鹅少年头顶左上有紫色残留、鞋底有粉色晕；说明第13条的 despill/边带清理没干净，下一批切帧要把 alpha 边带和品红分量一起判',
            key='image:despill')
qb.summary()
