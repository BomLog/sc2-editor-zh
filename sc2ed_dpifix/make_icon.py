#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成与 UI 同风格的程序图标 app.ico(深底圆角 + 锥形渐变辉光环 + 径向内核 + DPI)。"""
import io

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QImage,
                           QLinearGradient, QPainter, QPainterPath, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import QApplication
from PIL import Image

app = QApplication([])

S = 256
img = QImage(S, S, QImage.Format_ARGB32)
img.fill(Qt.transparent)
p = QPainter(img)
p.setRenderHint(QPainter.Antialiasing, True)
p.setRenderHint(QPainter.SmoothPixmapTransform, True)

cx = cy = S / 2

# ---- 圆角底 ----
pad = 10
r = 52
bg = QLinearGradient(0, pad, 0, S - pad)
bg.setColorAt(0.0, QColor("#122043"))
bg.setColorAt(0.55, QColor("#0a1122"))
bg.setColorAt(1.0, QColor("#05060f"))
body = QRectF(pad, pad, S - 2 * pad, S - 2 * pad)
path = QPainterPath()
path.addRoundedRect(body, r, r)
p.fillPath(path, QBrush(bg))
# 顶部辉光
topg = QLinearGradient(0, pad, 0, S * 0.55)
topg.setColorAt(0.0, QColor(80, 130, 255, 60))
topg.setColorAt(1.0, QColor(0, 0, 0, 0))
p.fillPath(path, QBrush(topg))
# 细边框
p.setPen(QPen(QColor(120, 170, 255, 60), 2))
p.setBrush(Qt.NoBrush)
p.drawRoundedRect(body.adjusted(1, 1, -1, -1), r - 1, r - 1)

# ---- 光晕 ----
halo = QRadialGradient(cx, cy, 96)
halo.setColorAt(0.0, QColor(34, 211, 238, 90))
halo.setColorAt(0.6, QColor(34, 211, 238, 24))
halo.setColorAt(1.0, QColor(34, 211, 238, 0))
p.setPen(Qt.NoPen)
p.setBrush(QBrush(halo))
p.drawEllipse(QPointF(cx, cy), 96, 96)

# ---- 假辉光:多层低透明外环 ----
for w, a in ((14, 26), (9, 40), (5, 70)):
    p.setPen(QPen(QColor(34, 211, 238, a), w, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(cx, cy), 78, 78)

# ---- 锥形渐变环(挖环 + 锥形笔刷)----
Ro, Ri = 82, 72
outer = QPainterPath(); outer.addEllipse(QPointF(cx, cy), Ro, Ro)
inner = QPainterPath(); inner.addEllipse(QPointF(cx, cy), Ri, Ri)
ring = outer.subtracted(inner)
conic = QConicalGradient(cx, cy, 90)
conic.setColorAt(0.00, QColor(34, 211, 238, 0))
conic.setColorAt(0.14, QColor(34, 211, 238, 255))
conic.setColorAt(0.40, QColor(34, 211, 238, 0))
conic.setColorAt(0.58, QColor(139, 92, 246, 255))
conic.setColorAt(0.70, QColor(139, 92, 246, 0))
conic.setColorAt(0.88, QColor(79, 125, 255, 255))
conic.setColorAt(1.00, QColor(79, 125, 255, 0))
p.setPen(Qt.NoPen)
p.fillPath(ring, QBrush(conic))

# ---- 内刻度虚线环 ----
p.setPen(QPen(QColor(122, 180, 255, 150), 3, Qt.DotLine, Qt.RoundCap))
p.setBrush(Qt.NoBrush)
p.drawEllipse(QPointF(cx, cy), 60, 60)

# ---- 内核 ----
core = QRadialGradient(cx, cy - 10, 58)
core.setColorAt(0.0, QColor(34, 211, 238, 110))
core.setColorAt(0.72, QColor(10, 18, 36, 235))
core.setColorAt(1.0, QColor(10, 18, 36, 255))
p.setPen(QPen(QColor(168, 246, 255, 150), 2))
p.setBrush(QBrush(core))
p.drawEllipse(QPointF(cx, cy), 50, 50)

# ---- 文字 DPI ----
f = QFont("Consolas", 40, QFont.Bold)
f.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
p.setFont(f)
trect = QRectF(0, cy - 34, S, 68)
# 辉光
p.setPen(QColor(34, 211, 238, 120))
for dx, dy in ((0, 0), (1, 0), (0, 1)):
    p.drawText(trect.translated(dx, dy), Qt.AlignCenter, "DPI")
# 主体
p.setPen(QColor("#eafcff"))
p.drawText(trect, Qt.AlignCenter, "DPI")

p.end()

# ---- 存 PNG -> PIL 合成多分辨率 ico ----
buf = io.BytesIO()
img.save_ptr = None
img.save("app_256.png", "PNG")
pil = Image.open("app_256.png").convert("RGBA")
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
pil.save("app.ico", format="ICO", sizes=sizes)
print("已生成 app.ico + app_256.png ; 尺寸:", sizes)
