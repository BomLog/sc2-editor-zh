#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC2 银河编辑器 DPI 修复 —— QML(Qt Quick)高级动画版 · 无 Chromium · 圆角无阴影
============================================================================
UI:  PySide6 Qt Quick。动画走场景图渲染线程(丝滑 60fps),GPU 合成。
     特效 = QtQuick.Shapes 真锥形/径向渐变 + QtQuick.Effects MultiEffect 真辉光/模糊
            + QtQuick.Particles 粒子火花。视觉对齐 web(CSS)版。
内核: dpifix_core.launch_patched —— 挂起启动 + 内存 NOP 两处 DPI 调用 + 恢复。
"""
import os
import sys
import threading

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QFileDialog

import dpifix_core as core

QML = r"""
import QtQuick
import QtQuick.Window
import QtQuick.Shapes
import QtQuick.Effects
import QtQuick.Particles

Window {
    id: root
    width: 520; height: 690
    visible: true
    flags: Qt.FramelessWindowHint | Qt.Window
    color: "transparent"                   // 透明 -> 配合圆角面板得到圆角窗口, frameless 无投影
    property string mode: "idle"           // idle|busy|ok|err  (UI 动画状态)
    property string selMode: "enhanced"   // crisp_fit|pmv2|enhanced|bitmap  (DPI 修复模式, 默认=系统增强)
    property int fontPct: 85               // 清晰适配的字体缩放 %(越小越紧)
    property bool dpiEnabled: true          // DPI 修复可独立关闭
    property bool l10nEnabled: true         // 官方依赖汉化可独立关闭
    property bool l10nStashed: false        // 外置汉化已暂存，可恢复
    property color cAccent: mode==="ok" ? "#34d399" : mode==="err" ? "#fb7185" : "#22d3ee"
    property color cVio: "#8b5cf6"
    property color cBlue: "#4f7dff"
    property color cMuted: "#63769a"

    function shortPath(p) {
        return p.length > 58 ? p.substring(0,28) + "…" + p.substring(p.length-28) : p
    }
    function setPath(p) {
        pathTxt.text = p ? ("» " + shortPath(p) + "   [更换]") : "» 点此选择 SC2Editor_x64.exe"
    }

    // 圆角遮罩源(黑色圆角矩形, 只用其 alpha 做 mask, 不显示)
    Rectangle {
        id: maskRect
        anchors.fill: parent
        radius: 22
        color: "black"
        antialiasing: true
        visible: false
        layer.enabled: true
    }

    // ============ 圆角裁剪面板(承载全部内容)============
    Rectangle {
        id: panel
        anchors.fill: parent
        radius: 22
        antialiasing: true
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0d1730" }
            GradientStop { position: 0.55; color: "#080d1a" }
            GradientStop { position: 1.0; color: "#05060f" }
        }
        border.width: 1
        border.color: Qt.rgba(0.47,0.66,1,0.14)
        // 用圆角 mask 裁剪整个子树 -> 真正的圆角(含顶部两角)
        layer.enabled: true
        layer.effect: MultiEffect {
            maskEnabled: true
            maskSource: maskRect
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0
        }

        // ---------- 旋转极光(锥形渐变 + 大模糊)----------
        Shape {
            id: aurora
            width: 620; height: 620
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top; anchors.topMargin: -180
            antialiasing: true
            opacity: 0.55
            layer.enabled: true
            layer.effect: MultiEffect {
                blurEnabled: true; blur: 1.0; blurMax: 64; blurMultiplier: 1.4
            }
            ShapePath {
                strokeWidth: 0; strokeColor: "transparent"
                fillGradient: ConicalGradient {
                    centerX: 310; centerY: 310; angle: 0
                    GradientStop { position: 0.00; color: "transparent" }
                    GradientStop { position: 0.16; color: Qt.rgba(root.cAccent.r,root.cAccent.g,root.cAccent.b,0.55) }
                    GradientStop { position: 0.34; color: "transparent" }
                    GradientStop { position: 0.56; color: Qt.rgba(root.cVio.r,root.cVio.g,root.cVio.b,0.50) }
                    GradientStop { position: 0.74; color: "transparent" }
                    GradientStop { position: 0.90; color: Qt.rgba(root.cBlue.r,root.cBlue.g,root.cBlue.b,0.45) }
                    GradientStop { position: 1.00; color: "transparent" }
                }
                PathAngleArc { centerX: 310; centerY: 310; radiusX: 300; radiusY: 300; startAngle: 0; sweepAngle: 360 }
            }
            RotationAnimator on rotation {
                from: 0; to: 360; loops: Animation.Infinite; running: true
                duration: root.mode==="busy" ? 6000 : 20000
            }
        }

        // 顶部辉光带(同样圆角, 避免方角盖住面板圆角)
        Rectangle {
            width: parent.width; height: 210; anchors.top: parent.top; radius: 22
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(0.31,0.49,1,0.14) }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }

        Text {
            id: versionTxt
            anchors.left: parent.left; anchors.top: parent.top
            anchors.leftMargin: 18; anchors.topMargin: 18
            text: "v" + backend.get_version()
            font.pixelSize: 10; font.family: "Consolas"; color: "#506587"
        }

        // 拖动区
        MouseArea {
            anchors.top: parent.top; width: parent.width; height: 120
            onPressed: root.startSystemMove()
        }
        // 关闭
        Rectangle {
            id: closeBtn; width: 28; height: 28; radius: 8
            anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14
            color: closeMa.containsMouse ? "#3a1e28" : "transparent"
            Behavior on color { ColorAnimation { duration: 150 } }
            rotation: closeMa.containsMouse ? 90 : 0
            Behavior on rotation { NumberAnimation { duration: 220; easing.type: Easing.OutBack } }
            Text { anchors.centerIn: parent; text: "✕"; font.pixelSize: 15
                   color: closeMa.containsMouse ? "#fb7185" : root.cMuted }
            MouseArea { id: closeMa; anchors.fill: parent; hoverEnabled: true
                        onClicked: backend.close() }
        }

        // 标题组
        Column {
            anchors.horizontalCenter: parent.horizontalCenter; y: 40; spacing: 0
            Text { text: "SC2 · DPI FIX"; font.pixelSize: 23; font.bold: true
                   font.letterSpacing: 3; color: "#a8f6ff"
                   anchors.horizontalCenter: parent.horizontalCenter
                   layer.enabled: true
                   layer.effect: MultiEffect {
                       shadowEnabled: true; shadowColor: root.cAccent
                       shadowBlur: 1.0; shadowVerticalOffset: 0; shadowHorizontalOffset: 0
                   } }
            Item { width: 1; height: 9 }
            Text { text: "银河编辑器 高DPI 字体溢出修复 · 外置内存补丁"
                   font.pixelSize: 12; color: "#8ea3c8"
                   anchors.horizontalCenter: parent.horizontalCenter }
            Item { width: 1; height: 5 }
            Text { text: "///  MEMORY  PATCH  ENGINE  ///"; font.pixelSize: 10
                   font.letterSpacing: 4; font.family: "Consolas"; color: "#41577f"
                   anchors.horizontalCenter: parent.horizontalCenter }
        }

        // ================= 反应堆 =================
        Item {
            id: reactor; width: 190; height: 190
            anchors.horizontalCenter: parent.horizontalCenter; y: 128

            // --- 光晕 halo(径向渐变 + 模糊)---
            Shape {
                id: halo; anchors.fill: parent; antialiasing: true; opacity: 0.5
                layer.enabled: true
                layer.effect: MultiEffect { blurEnabled: true; blur: 1.0; blurMax: 48 }
                ShapePath {
                    strokeWidth: 0; strokeColor: "transparent"
                    fillGradient: RadialGradient {
                        centerX: 95; centerY: 95; centerRadius: 95; focalX: 95; focalY: 95
                        GradientStop { position: 0.0; color: Qt.rgba(root.cAccent.r,root.cAccent.g,root.cAccent.b,0.55) }
                        GradientStop { position: 0.6; color: Qt.rgba(root.cAccent.r,root.cAccent.g,root.cAccent.b,0.10) }
                        GradientStop { position: 1.0; color: "transparent" }
                    }
                    PathAngleArc { centerX: 95; centerY: 95; radiusX: 95; radiusY: 95; startAngle: 0; sweepAngle: 360 }
                }
                SequentialAnimation on opacity {
                    loops: Animation.Infinite; running: true
                    NumberAnimation { from: 0.34; to: 0.62; duration: 1600; easing.type: Easing.InOutSine }
                    NumberAnimation { from: 0.62; to: 0.34; duration: 1600; easing.type: Easing.InOutSine }
                }
            }

            // --- 外环:锥形渐变环 + 辉光, 顺时针 ---
            Shape {
                id: outerRing; anchors.fill: parent; antialiasing: true
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true; shadowColor: root.cAccent
                    shadowBlur: 1.0; shadowScale: 1.02
                    shadowVerticalOffset: 0; shadowHorizontalOffset: 0; autoPaddingEnabled: true
                }
                ShapePath {
                    fillRule: ShapePath.OddEvenFill
                    strokeWidth: 0; strokeColor: "transparent"
                    fillGradient: ConicalGradient {
                        centerX: 95; centerY: 95; angle: 0
                        GradientStop { position: 0.00; color: "transparent" }
                        GradientStop { position: 0.14; color: root.cAccent }
                        GradientStop { position: 0.40; color: "transparent" }
                        GradientStop { position: 0.58; color: root.cVio }
                        GradientStop { position: 0.70; color: "transparent" }
                        GradientStop { position: 0.88; color: root.cBlue }
                        GradientStop { position: 1.00; color: "transparent" }
                    }
                    PathAngleArc { centerX: 95; centerY: 95; radiusX: 93; radiusY: 93; startAngle: 0; sweepAngle: 360 }
                    PathAngleArc { centerX: 95; centerY: 95; radiusX: 88; radiusY: 88; startAngle: 0; sweepAngle: 360 }
                }
                RotationAnimator on rotation {
                    from: 0; to: 360; loops: Animation.Infinite; running: true
                    duration: root.mode==="busy" ? 1500 : 8000
                }
            }

            // --- 中环:虚线圆环, 逆时针 ---
            Shape {
                id: midRing; anchors.centerIn: parent; width: 150; height: 150; antialiasing: true
                ShapePath {
                    fillColor: "transparent"
                    strokeColor: Qt.rgba(0.48,0.71,1,0.5)
                    strokeWidth: 1.6
                    strokeStyle: ShapePath.DashLine
                    dashPattern: [1, 4]
                    PathAngleArc { centerX: 75; centerY: 75; radiusX: 74; radiusY: 74; startAngle: 0; sweepAngle: 360 }
                }
                RotationAnimator on rotation {
                    from: 360; to: 0; loops: Animation.Infinite; running: true
                    duration: root.mode==="busy" ? 2600 : 15000
                }
            }

            // --- 内刻度环:细密虚线, 顺时针慢 ---
            Shape {
                id: tickRing; anchors.centerIn: parent; width: 128; height: 128; antialiasing: true
                opacity: 0.55
                ShapePath {
                    fillColor: "transparent"
                    strokeColor: "#a8f6ff"
                    strokeWidth: 4
                    strokeStyle: ShapePath.DashLine
                    dashPattern: [0.35, 1.4]
                    PathAngleArc { centerX: 64; centerY: 64; radiusX: 61; radiusY: 61; startAngle: 0; sweepAngle: 360 }
                }
                RotationAnimator on rotation {
                    from: 0; to: 360; loops: Animation.Infinite; running: true
                    duration: root.mode==="busy" ? 6000 : 30000
                }
            }

            // --- 内核:径向渐变 + 辉光 + 呼吸 ---
            Item {
                id: coreWrap; anchors.centerIn: parent; width: 100; height: 100
                SequentialAnimation on scale {
                    loops: Animation.Infinite; running: true
                    NumberAnimation { from: 1.0; to: 1.055
                        duration: root.mode==="busy" ? 500 : 1400; easing.type: Easing.InOutSine }
                    NumberAnimation { from: 1.055; to: 1.0
                        duration: root.mode==="busy" ? 500 : 1400; easing.type: Easing.InOutSine }
                }
                Shape {
                    id: core; anchors.fill: parent; antialiasing: true
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true; shadowColor: root.cAccent
                        shadowBlur: 1.0; shadowVerticalOffset: 0; shadowHorizontalOffset: 0
                        autoPaddingEnabled: true
                    }
                    ShapePath {
                        strokeColor: Qt.rgba(root.cAccent.r,root.cAccent.g,root.cAccent.b,0.55)
                        strokeWidth: 1.2
                        fillGradient: RadialGradient {
                            centerX: 50; centerY: 38; centerRadius: 62; focalX: 50; focalY: 38
                            GradientStop { position: 0.0; color: Qt.rgba(root.cAccent.r,root.cAccent.g,root.cAccent.b,0.34) }
                            GradientStop { position: 0.72; color: Qt.rgba(0.04,0.07,0.14,0.92) }
                            GradientStop { position: 1.0; color: "#0a1224" }
                        }
                        PathAngleArc { centerX: 50; centerY: 50; radiusX: 49; radiusY: 49; startAngle: 0; sweepAngle: 360 }
                    }
                }
                Text { id: coreTxt; anchors.centerIn: parent; text: "DPI"
                       font.pixelSize: 25; font.bold: true; font.family: "Consolas"
                       color: root.mode==="idle" ? "#eafcff" : root.cAccent
                       layer.enabled: true
                       layer.effect: MultiEffect {
                           shadowEnabled: true; shadowColor: root.cAccent; shadowBlur: 0.9
                           shadowVerticalOffset: 0; shadowHorizontalOffset: 0
                       } }
            }
        }

        // ================= 粒子火花(向上漂浮)=================
        ParticleSystem {
            id: pSys; anchors.fill: parent; running: true
            ImageParticle {
                groups: ["spark"]
                source: "qrc:///particleresources/glowdot.png"
                color: root.cAccent
                colorVariation: 0.35
                alpha: 0.0
                entryEffect: ImageParticle.Fade
            }
            Emitter {
                group: "spark"
                anchors.fill: parent
                emitRate: root.mode==="busy" ? 34 : 14
                lifeSpan: 4200; lifeSpanVariation: 1400
                size: 3; sizeVariation: 3; endSize: 0
                velocity: AngleDirection { angle: 270; angleVariation: 22
                    magnitude: 14; magnitudeVariation: 12 }
                acceleration: PointDirection { y: -6; xVariation: 5 }
            }
        }

        // ================= 功能开关行 =================
        Row {
            id: featureRow
            anchors.horizontalCenter: parent.horizontalCenter; y: 322; spacing: 28

            // ---- DPI 修复开关 ----
            Row {
                spacing: 8
                Text {
                    text: "清晰度修复"; font.pixelSize: 12; color: "#8ea3c8"
                    anchors.verticalCenter: parent.verticalCenter
                }
                Rectangle {
                    width: 42; height: 22; radius: 11
                    color: root.dpiEnabled ? "#168ba0" : "#26364f"
                    border.width: 1
                    border.color: root.dpiEnabled ? "#62e8f5" : "#50617d"
                    Behavior on color { ColorAnimation { duration: 150 } }
                    Rectangle {
                        width: 16; height: 16; radius: 8; y: 3
                        x: root.dpiEnabled ? 23 : 3
                        color: root.dpiEnabled ? "#d9fbff" : "#8494ad"
                        Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                    }
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.mode === "busy") return
                            root.dpiEnabled = !root.dpiEnabled
                            statusTxt.setMsg(
                                root.dpiEnabled ? "清晰度修复已启用" : "清晰度修复已关闭 · 仅启动编辑器",
                                root.cAccent)
                        }
                    }
                }
            }

            // 分隔竖线
            Rectangle { width: 1; height: 22; color: "#22314a"; anchors.verticalCenter: parent.verticalCenter }

            // ---- 官方依赖汉化开关 ----
            Row {
                spacing: 8
                Text {
                    text: "官方依赖汉化"; font.pixelSize: 12; color: "#8ea3c8"
                    anchors.verticalCenter: parent.verticalCenter
                }
                Rectangle {
                    width: 42; height: 22; radius: 11
                    color: root.l10nEnabled ? "#168ba0" : "#26364f"
                    border.width: 1
                    border.color: root.l10nEnabled ? "#62e8f5" : "#50617d"
                    Behavior on color { ColorAnimation { duration: 150 } }
                    Rectangle {
                        width: 16; height: 16; radius: 8; y: 3
                        x: root.l10nEnabled ? 23 : 3
                        color: root.l10nEnabled ? "#d9fbff" : "#8494ad"
                        Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                    }
                    MouseArea {
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.mode === "busy") return
                            if (root.l10nStashed) {
                                statusTxt.setMsg("汉化已暂时卸载，请先恢复", "#fbbf24")
                                return
                            }
                            root.l10nEnabled = !root.l10nEnabled
                            statusTxt.setMsg(
                                root.l10nEnabled ? "官方依赖汉化已启用" : "官方依赖汉化已关闭",
                                root.cAccent)
                        }
                    }
                }
            }
        }

        // ================= DPI 模式选择(仅 DPI 开启时显示)=================
        Row {
            id: modeRow
            visible: root.dpiEnabled
            anchors.horizontalCenter: parent.horizontalCenter; y: 358; spacing: 8
            Repeater {
                model: [
                    { k: "crisp_fit", t: "清晰适配", d: "原生清晰·缩字贴合" },
                    { k: "pmv2",     t: "PMv2 高清", d: "物理像素·系统缩放" },
                    { k: "enhanced", t: "系统增强",   d: "矢量·不溢出" },
                    { k: "bitmap",   t: "位图",       d: "最稳·最糊" }
                ]
                delegate: Rectangle {
                    width: 116; height: 46; radius: 12
                    property bool sel: root.selMode === modelData.k
                    color: sel ? Qt.rgba(0.13,0.83,0.93,0.15)
                                : (mma.containsMouse ? "#12233b" : "transparent")
                    border.width: sel ? 1.5 : 1
                    border.color: sel ? "#22d3ee" : "#22314a"
                    Behavior on color { ColorAnimation { duration: 150 } }
                    Column {
                        anchors.centerIn: parent; spacing: 2
                        Text { text: modelData.t; font.pixelSize: 12; font.bold: parent.parent.sel
                               color: parent.parent.sel ? "#a8f6ff" : "#8ea3c8"
                               anchors.horizontalCenter: parent.horizontalCenter }
                        Text { text: modelData.d; font.pixelSize: 8; font.family: "Consolas"
                               color: parent.parent.sel ? "#5fbfd0" : "#556b8f"
                               anchors.horizontalCenter: parent.horizontalCenter }
                    }
                    MouseArea {
                        id: mma; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.mode === "busy") return
                            root.selMode = modelData.k
                            statusTxt.setMsg(
                                modelData.k === "crisp_fit" ? "清晰适配:原生清晰;下方调字号让字回到框里"
                              : modelData.k === "pmv2" ? "PMv2:最清晰;若个别面板异常再切其他模式"
                              : modelData.k === "enhanced" ? "系统增强:不溢出但偏软(GDI 矢量缩放)"
                              : "位图:最稳、最糊(整窗位图拉伸)", root.cAccent)
                        }
                    }
                }
            }
        }

        // ---- 清晰适配: 字体档位(仅该模式且 DPI 开启时显示)----
        Row {
            id: fontRow
            visible: root.dpiEnabled && root.selMode === "crisp_fit"
            anchors.horizontalCenter: parent.horizontalCenter; y: 410; spacing: 6
            Text { text: "字体"; font.pixelSize: 12; color: "#8ea3c8"
                   anchors.verticalCenter: parent.verticalCenter }
            Repeater {
                model: [75, 80, 85, 90, 100]
                delegate: Rectangle {
                    width: 46; height: 28; radius: 8
                    property bool sel: root.fontPct === modelData
                    color: sel ? Qt.rgba(0.13,0.83,0.93,0.15)
                                : (fma.containsMouse ? "#12233b" : "transparent")
                    border.width: sel ? 1.5 : 1
                    border.color: sel ? "#22d3ee" : "#22314a"
                    Behavior on color { ColorAnimation { duration: 150 } }
                    Text { anchors.centerIn: parent; text: modelData + "%"
                           font.pixelSize: 11; font.bold: parent.sel
                           color: parent.sel ? "#a8f6ff" : "#8ea3c8" }
                    MouseArea {
                        id: fma; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.mode === "busy") return
                            root.fontPct = modelData
                            statusTxt.setMsg("字体 " + modelData + "% · 越小越紧,调到字不出框", root.cAccent)
                        }
                    }
                }
            }
        }

        // ---- 汉化管理按钮(暂时卸载/恢复)----
        Rectangle {
            id: l10nManageBtn
            anchors.horizontalCenter: parent.horizontalCenter
            y: root.dpiEnabled && root.selMode === "crisp_fit" ? 444 : 416
            width: 112; height: 30; radius: 6
            color: l10nManageMa.containsMouse
                   ? (root.l10nStashed ? "#123c36" : "#3a2230")
                   : "#101a2b"
            border.width: 1
            border.color: root.l10nStashed ? "#34d399" : "#a8556d"
            Text {
                anchors.centerIn: parent
                text: root.l10nStashed ? "恢复汉化" : "暂时卸载"
                font.pixelSize: 11; font.bold: true
                color: root.l10nStashed ? "#8ff0c8" : "#f4a6b8"
            }
            MouseArea {
                id: l10nManageMa; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.mode === "busy") return
                    root.mode = "busy"; coreTxt.text = "···"
                    statusTxt.setMsg(
                        root.l10nStashed ? "正在校验并恢复汉化…" : "正在暂存汉化外置文件…",
                        root.cAccent)
                    backend.toggle_localization()
                }
            }
        }

        // ================= 按钮 =================
        Item {
            id: btn; width: 300; height: 54
            anchors.horizontalCenter: parent.horizontalCenter
            y: root.dpiEnabled && root.selMode === "crisp_fit" ? 484 : 456
            scale: btnMa.pressed ? 0.98 : (btnMa.containsMouse && root.mode!=="busy" ? 1.03 : 1.0)
            Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }

            // 悬停辉光(MultiEffect drop-shadow 作外发光)
            Rectangle {
                id: btnFace
                anchors.fill: parent; radius: 15; border.width: 1; clip: true
                border.color: root.mode==="busy" ? "#2b3f63" : "#a8f6ff"
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: root.mode==="busy" ? "#274a66" : "#22d3ee" }
                    GradientStop { position: 0.55; color: root.mode==="busy" ? "#254264" : "#4f7dff" }
                    GradientStop { position: 1.0; color: root.mode==="busy" ? "#233a63" : "#8b5cf6" }
                }
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: root.mode==="busy" ? "transparent" : root.cAccent
                    shadowBlur: 1.0; shadowScale: 1.0
                    shadowVerticalOffset: 3; shadowHorizontalOffset: 0
                    brightness: btnMa.containsMouse && root.mode!=="busy" ? 0.10 : 0.0
                    Behavior on brightness { NumberAnimation { duration: 200 } }
                }

                // 顶部玻璃高光(静态、柔和,替代廉价扫光条)
                Rectangle {
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.margins: 1
                    height: parent.height * 0.5; radius: parent.radius - 1
                    visible: root.mode!=="busy"
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: Qt.rgba(1,1,1,0.28) }
                        GradientStop { position: 1.0; color: "transparent" }
                    }
                }

                Row {
                    anchors.centerIn: parent; spacing: 9
                    Shape {
                        visible: root.mode==="busy"; width: 16; height: 16; antialiasing: true
                        anchors.verticalCenter: parent.verticalCenter
                        ShapePath {
                            fillColor: "transparent"; strokeColor: "#bfefff"; strokeWidth: 2
                            capStyle: ShapePath.RoundCap
                            PathAngleArc { centerX: 8; centerY: 8; radiusX: 6; radiusY: 6; startAngle: 0; sweepAngle: 280 }
                        }
                        RotationAnimator on rotation { from:0; to:360; duration:800
                            loops: Animation.Infinite; running: root.mode==="busy" }
                    }
                    Text { text: root.mode==="busy" ? "PATCHING…"
                                 : root.dpiEnabled ? "▶  启动修复版编辑器"
                                 : root.l10nEnabled ? "▶  启动汉化版编辑器"
                                 : "▶  启动编辑器"
                           font.pixelSize: 15; font.bold: true
                           color: root.mode==="busy" ? "#9fc0e0" : "#04121e" }
                }
            }
            MouseArea {
                id: btnMa; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (root.mode==="busy") return
                    if (!root.dpiEnabled && !root.l10nEnabled) {
                        statusTxt.setMsg("清晰度修复和汉化都已关闭，没有需要修补的功能", "#fbbf24")
                        return
                    }
                    root.mode = "busy"; coreTxt.text = "···"
                    statusTxt.setMsg("初始化补丁引擎…", root.cAccent)
                    backend.launch(root.dpiEnabled ? root.selMode : "none",
                                   root.fontPct, root.l10nEnabled)
                }
            }
        }

        // ================= 状态 =================
        Text {
            id: statusTxt; anchors.horizontalCenter: parent.horizontalCenter
            y: root.dpiEnabled && root.selMode === "crisp_fit" ? 552 : 524
            font.pixelSize: 13; color: root.cMuted; text: "初始化…"
            Behavior on opacity { NumberAnimation { duration: 300 } }
            function setMsg(m, c) { opacity = 0; _m = m; _c = c; fadeTimer.restart() }
            property string _m: ""; property color _c: "#63769a"
            Timer { id: fadeTimer; interval: 160
                    onTriggered: { statusTxt.text = statusTxt._m; statusTxt.color = statusTxt._c
                                   statusTxt.opacity = 1 } }
        }

        // ================= 路径 =================
        Rectangle {
            id: pathBox; height: 30; radius: 10
            width: Math.min(pathTxt.implicitWidth + 26, 460)
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom; anchors.bottomMargin: 38
            color: pathMa.containsMouse ? "#0d1c2e" : "transparent"
            border.width: 1
            border.color: pathMa.containsMouse ? Qt.rgba(0.13,0.83,0.93,0.4) : "#22314a"
            Behavior on color { ColorAnimation { duration: 150 } }
            Text {
                id: pathTxt; anchors.centerIn: parent; text: "» 定位编辑器中…"
                font.pixelSize: 11; font.family: "Consolas"
                color: pathMa.containsMouse ? "#a8f6ff" : "#5a6d90"
                elide: Text.ElideMiddle; width: Math.min(implicitWidth, 434)
            }
            MouseArea { id: pathMa; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: { if (root.mode!=="busy") backend.pick() } }
        }

        // ================= 署名 =================
        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom; anchors.bottomMargin: 10
            spacing: 3
            Text {
                text: "原汉化：头目 · hgzerg · OB"
                font.pixelSize: 11; font.bold: true; color: "#7b93b8"
                anchors.horizontalCenter: parent.horizontalCenter
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true; shadowColor: "#22d3ee"
                    shadowBlur: 0.6; shadowVerticalOffset: 0; shadowHorizontalOffset: 0
                }
            }
            Text {
                text: "DPI 修复 · 依赖汉化 · 工具开发：BoomFirst"
                font.pixelSize: 10; color: "#5e7899"
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
    }

    Connections {
        target: backend
        function onStatus(kind, msg) {
            if (kind === "status") statusTxt.setMsg(msg, root.cAccent)
            else if (kind === "done") { root.mode = "ok"; coreTxt.text = "✓"; statusTxt.setMsg(msg, root.cAccent) }
            else if (kind === "fail") { root.mode = "err"; coreTxt.text = "!"; statusTxt.setMsg(msg, root.cAccent) }
            else if (kind === "path") root.setPath(msg)
            else if (kind === "l10n_state") {
                root.l10nStashed = msg === "1"
                if (root.l10nStashed) root.l10nEnabled = false
            }
        }
    }
    Component.onCompleted: {
        var p = backend.get_editor()
        setPath(p)
        root.l10nStashed = backend.localization_stashed()
        if (root.l10nStashed) root.l10nEnabled = false
        statusTxt.setMsg(p ? "已定位编辑器 · 准备就绪" : "未自动找到,请点下方选择",
                         p ? root.cAccent : "#fb7185")
    }
}
"""


class Backend(QObject):
    status = Signal(str, str)   # kind, msg

    def __init__(self):
        super().__init__()
        self.editor = core.find_editor()

    @Slot(result=str)
    def get_editor(self):
        return self.editor or ""

    @Slot(result=str)
    def get_version(self):
        return core.app_version()

    @Slot(result=bool)
    def localization_stashed(self):
        return core.localization_is_uninstalled(self.editor)

    @Slot()
    def pick(self):
        p, _ = QFileDialog.getOpenFileName(
            None, "选择 SC2Editor_x64.exe", "",
            "SC2Editor (SC2Editor_x64.exe);;可执行文件 (*.exe)")
        if p:
            self.editor = p
            self.status.emit("path", p)
            self.status.emit(
                "l10n_state", "1" if core.localization_is_uninstalled(p) else "0"
            )

    @Slot()
    def toggle_localization(self):
        threading.Thread(target=self._toggle_localization, daemon=True).start()

    def _toggle_localization(self):
        try:
            if core.localization_is_uninstalled(self.editor):
                count, conflicts = core.restore_localization(
                    self.editor, lambda m: self.status.emit("status", m)
                )
                detail = f"已恢复 {count} 个汉化文件"
                if conflicts:
                    detail += f" · 备份 {conflicts} 个冲突文件"
                self.status.emit("done", detail + " ✓")
            else:
                count = core.temporarily_uninstall_localization(
                    self.editor, lambda m: self.status.emit("status", m)
                )
                self.status.emit("done", f"已暂时卸载 {count} 个汉化文件 · 可恢复 ✓")
        except core.PatchError as exc:
            self.status.emit("fail", str(exc))
        except Exception as exc:  # noqa
            self.status.emit("fail", f"错误: {exc}")
        finally:
            self.status.emit(
                "l10n_state",
                "1" if core.localization_is_uninstalled(self.editor) else "0",
            )

    @Slot(str, int, bool)
    def launch(self, mode="crisp_fit", font_pct=85, localization=True):
        threading.Thread(
            target=self._work,
            args=(mode, font_pct, localization),
            daemon=True,
        ).start()

    def _work(self, mode="crisp_fit", font_pct=85, localization=True):
        l10n_status = "官方依赖汉化已加载" if localization else "未启用汉化"
        done = {
            "none": f"已启动 · {l10n_status} · 不修复 DPI ✓",
            "crisp_fit": f"已启动 · {l10n_status} · 清晰适配 字体{font_pct}% ✓",
            "pmv2": f"已启动 · {l10n_status} · PMv2 物理像素渲染 ✓",
            "enhanced": f"已启动 · {l10n_status} · 系统增强矢量缩放 ✓",
            "bitmap": f"已启动 · {l10n_status} · 位图缩放 ✓",
        }.get(mode, f"已启动 · {l10n_status} ✓")
        try:
            core.launch_patched(self.editor, lambda m: self.status.emit("status", m),
                                mode=mode, font_pct=font_pct,
                                localization=localization)
            self.status.emit("done", done)
        except core.PatchError as e:
            self.status.emit("fail", str(e))
        except Exception as e:  # noqa
            self.status.emit("fail", f"错误: {e}")

    @Slot()
    def close(self):
        QApplication.quit()


def main():
    app = QApplication([])
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    ico = os.path.join(base, "app.ico")
    if os.path.exists(ico):
        app.setWindowIcon(QIcon(ico))
    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)
    engine.loadData(QML.encode("utf-8"))
    if not engine.rootObjects():
        raise SystemExit("QML 加载失败")
    win = engine.rootObjects()[0]
    scr = app.primaryScreen().geometry()
    win.setX((scr.width() - 520) // 2)
    win.setY(scr.height() // 3 - 40)
    app.exec()


if __name__ == "__main__":
    main()
