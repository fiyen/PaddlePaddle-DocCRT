from PySide2.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, \
    QFontDialog, QFileDialog, QColorDialog, QMenu
from PySide2.QtCore import QPoint, Signal, QEvent
from PySide2.QtGui import QFont, QColor, QIcon, QFontDatabase, QPalette
from .box_widget import *
from .document import Document
import os
import re
from . import globalvars
import sys
from .textblock import TextItem, UpdateView
from PIL import ImageGrab
from paddleocr import PaddleOCR
import numpy as np
import pyperclip
from pycorrector.ernie.ernie_corrector import ErnieCorrector
corrector = ErnieCorrector()

GlobalVars = globalvars.GlobalVars
SelStatus = globalvars.SelStatus()


class TextItemReload(TextItem, QPushButton):
    right_click = Signal(QPoint)

    def __init__(self, textBlock=None, text="", preTextItem=False, font=None, textColor=None, backgroundColor=False,
                 updateView=UpdateView.updateAll, corrected_text=[], parent=None):
        TextItem.__init__(self, textBlock, text, preTextItem,
                          font, textColor, backgroundColor, updateView)
        QPushButton.__init__(self, parent)
        self.oldText = text
        self.oldTextColor = textColor
        self.setTextColor(QColor(255, 0, 0, 150))
        self.right_click.connect(self.popUpMenu)
        self.setStyleSheet('border:0px; background-color: rgba(255,255,255,0)')
        self.updateAllTextFragments = self.updateAllTextFragmentsReload(
            self.updateAllTextFragments)
        self.updateAllTextFragments()
        self.corrected_text = corrected_text
        self.correct_menu = QMenu()
        ignore = self.correct_menu.addAction("忽略此错误")
        ignore.triggered.connect(self.ignore_action)
        self.correct_menu.addSeparator()
        undo = self.correct_menu.addAction("撤销此更改")
        undo.triggered.connect(self.undo_action)
        self.correct_menu.addSeparator()
        self.sub_actions = []
        self._set_sub_actions()

    def ignore_action(self):
        self.setTextColor(self.oldTextColor)

    def undo_action(self):
        self.setText(self.oldText)

    def updateAllTextFragmentsReload(self, func):
        def __wrap__():
            func()
            self.resize(self.textFragments[-1].width,
                        self.textFragments[-1].lineHeight)
            self.move(self.getPos())
            self.hide()
            self.show()
        return __wrap__

    def getPos(self):
        pos = QPoint(self.textFragments[-1].posX, self.textFragments[-1].posY)
        return pos

    def enterEvent(self, event):
        print("Enter")
        self.oldBackgroundColor = self.backgroundColor
        new_color = QColor(0, 0, 255, 125)
        self.setBackgroundColor(new_color)
        self.updateView()

    def updateView(self):
        self.textBlock.updateSize()
        global CurrentTextItemIndex
        CurrentTextItemIndex = len(self.text)  # index更新到到item尾
        self.textBlock.updateCursor()  # 光标更新

    def leaveEvent(self, event):
        print("Leave")
        self.setBackgroundColor(self.oldBackgroundColor)
        self.updateView()

    def mousePressEvent(self, event):
        pos = event.pos()
        gp = self.mapToGlobal(pos)
        if event.buttons() == Qt.RightButton:
            self.right_click.emit(gp)

    def popUpMenu(self, pos):
        print("popUpMenu")
        self.correct_menu.popup(pos)

    def _set_sub_actions(self):
        if self.corrected_text:
            for text in self.corrected_text:
                sub_action = self.correct_menu.addAction(text)
                sub_action.triggered.connect(self.modify(text))

    def modify(self, text):
        def __later__():
            self.setText(text)
        return __later__


class DocumentScrollArea(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumSize(GlobalVars.PageWidth + 30, 10000)
        self.setMinimumSize(GlobalVars.PageWidth + 30, 10)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setStyleSheet("background-color:rgba(255,255,255)")

    def setDocument(self, document):
        self.document = document
        self.setWidget(document)


class FontFamiliesPanel(ListWidget):
    """
    字体选项栏
    """

    def __init__(self, parent=None, func=None):  # 最后选择的字体通过font返回,func表示字体选择的时候，执行的函数
        super().__init__(parent)
        self.func = func  # func表示选中字体后要进行的操作
        fontDataBase = QFontDatabase().families()
        fontDataBase.reverse()  # 反转列表，使得中文位于前面
        for f in fontDataBase:
            button = PushButton(f)
            # 不能直接用 lambda f=f:self.func(f) 不知道为什么
            button.clicked.connect(self.itemClicked(f))
            font = QFont(f, pointSize=10)
            button.setFont(font)  # 设置字体
            button.resize(button.sizeHint())
            self.addItem(button)
        self.hide()

    def itemClicked(self, f):
        return lambda: self.func(f)


class FontSizePanel(ListWidget):
    """
    字体大小选择栏
    """

    def __init__(self, parent=None, func=None):
        super().__init__(parent)
        self.func = func
        pointSize = [10, 12, 14, 16, 20, 24, 30]  # 预先定义的不同的字体大小

        for s in pointSize:
            button = PushButton(str(s))
            button.clicked.connect(self.itemClicked(s))
            button.setFont(QFont(button.font().family(), pointSize=s))
            button.resize(button.sizeHint())
            self.addItem(button)
        self.hide()  # 默认不显示

    def itemClicked(self, s):
        return lambda: self.func(s)


# 行距选择栏
class LineSpacingPanel(ListWidget):
    """
    行距选择栏
    """

    def __init__(self, parent=None, func=None):
        super().__init__(parent)
        self.func = func
        pointSize = [0.25, 0.5, 1, 5, 10, 20]  # 预先定义的不同的行距大小,小数主要服务相对行距

        for s in pointSize:
            button = PushButton(str(s))
            button.clicked.connect(self.itemClicked(s))
            button.resize(button.sizeHint())
            self.addItem(button)
        self.hide()  # 默认不显示

    def itemClicked(self, s):
        return lambda: self.func(s)


class TitleLevelsPanel(ScrollArea):
    """
    标题选项栏
    """

    def __init__(self, parent=None, func=None):  # func 字体选择执行的程序
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.func = func
        self.titleButtons = {}  # 显示当前标题等级时候使用
        self.ActivatedTitleButton = None  # 当前激活的标题等级

        layout = QGridLayout()
        row = column = 0  # 起始的行和列的位置
        for t in GlobalVars.TitleLevels:
            button = PushButton(t.name, self)
            # button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.titleButtons[t.name] = button
            button.setFont(t.font)
            button.clicked.connect(self.itemClicked(t))
            layout.addWidget(button, row, column)
            if column == 4:  # 换行，每行最多容纳四个标题
                row += 1
                column = 0
            else:
                column += 1
        self.setLayout(layout)

    def itemClicked(self, titleLevel):  # 选择字体
        def clicked():
            if self.func:
                self.func(titleLevel)  # 选择字体的时候执行的额操作
            GlobalVars.CurrentTitleLevel = titleLevel

        return clicked

    def setTitle(self, t):  # 更新当前的标题等级
        if self.ActivatedTitleButton:  # 恢复之前的标题格式，待优化，太冗长
            self.ActivatedTitleButton.setStyleSheet(
                "QPushButton{{background-color:rgba{};border:0px}} QPushButton:hover{{background-color:rgba{}}} ".format(
                    str(GlobalVars.Panel_BackgroundColor.getRgb()), str(GlobalVars.Panel_ActivateColor.getRgb())))
        self.ActivatedTitleButton = self.titleButtons[t.name]  # 设置新的当前标题
        self.ActivatedTitleButton.setStyleSheet(
            "QPushButton{{background-color:rgba{};border:0px}} ".format(str(GlobalVars.Panel_ActivateColor.getRgb())))


class ToolWidget(QWidget):
    """
    # 文字工具栏
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.DocWidget = parent
        self.setFocusPolicy(Qt.NoFocus)
        self.ui()

    def ui(self):
        self.setMaximumSize(10000, 100)  # 限制高度
        self.setMinimumSize(10, 100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.mainLayout = QHBoxLayout()  # 总体布局

        # 文件管理布局
        saveButton = ToolButton(QIcon(
            "images/save.png"), "", toolTip="保存", clicked=self.saveDocument, shortcut="ctrl+s")
        saveAsButton = ToolButton(QIcon("images/saveas.png"), "", toolTip="另存为",
                                  clicked=self.saveDocumentAs, shortcut="ctr+shift+s")
        openButton = ToolButton(QIcon(
            "images/open.png"), "", toolTip="打开", clicked=self.openDocument, shortcut="ctrl+o")
        newButton = ToolButton(QIcon("images/new.png"), "", toolTip="新建")

        fileLayout = QGridLayout()
        fileLayout.addWidget(newButton, 0, 0)
        fileLayout.addWidget(openButton, 0, 1)
        fileLayout.addWidget(saveButton, 1, 0)
        fileLayout.addWidget(saveAsButton, 1, 1)

        # 字体布局
        GlobalVars.titleLevelsPanel = TitleLevelsPanel(
            func=self.setTitleLevel)  # func绑定到函数，修改标题等级时候调用
        GlobalVars.CurrentTitleLevel = GlobalVars.CurrentTitleLevel  # 重新赋值，刷新界面

        GlobalVars.currentFontFamilyPanel = LineEditWithSubButton(
            self, toolTip="选择字体", subButton="itemButton")
        GlobalVars.currentFontFamilyPanel.listWidget = FontFamiliesPanel(
            self.parent(), func=self.setFontFamily)

        GlobalVars.currentFontSizePanel = LineEditWithSubButton(
            self, toolTip="字体大小", subButton="itemButton")
        GlobalVars.currentFontSizePanel.listWidget = FontSizePanel(
            self.parent(), func=self.setFontSize)

        # 斜体设置
        GlobalVars.currentFontItalicPanel = ToolButton(
            clicked=self.setFontItalic, subButton="itemButton")  # 斜体面板
        GlobalVars.currentFontItalicPanel.listWidget.addItem(
            ToolButton(icon=QIcon("images/italic.png"), toolTip="斜体", clicked=lambda: self.setFontItalic(True)))
        GlobalVars.currentFontItalicPanel.listWidget.addItem(
            ToolButton(icon=QIcon("images/notitalic.png"), toolTip="取消斜体",
                       clicked=lambda: self.setFontItalic(False)))

        GlobalVars.currentFontItalicPanel.listWidget.setParent(
            self.parent())  # 设置父对象
        # 粗体设置 待完善，不同的粗度
        GlobalVars.currentFontWeightPanel = ToolButton(
            self, clicked=self.setFontWeight, subButton="itemButton")  # 加粗面板
        GlobalVars.currentFontWeightPanel.listWidget.addItem(
            ToolButton(icon=QIcon("images/bold.png"), toolTip="加粗",
                       clicked=lambda: self.setFontWeight(QFont.Bold)))
        GlobalVars.currentFontWeightPanel.listWidget.addItem(
            ToolButton(icon=QIcon("images/unbold.png"), toolTip="取消加粗",
                       clicked=lambda: self.setFontWeight(False)))
        GlobalVars.currentFontWeightPanel.listWidget.setParent(
            self.parent())  # doc是listwidget的父级
        GlobalVars.CurrentFont = GlobalVars.CurrentFont  # 更新与文字相关属性面板

        GlobalVars.currentTextColorPanel = ToolButton(
            "A", toolTip="设置文字颜色", clicked=self.setTextColor)
        GlobalVars.CurrentTextColor = GlobalVars.CurrentTextColor  # 重新赋值，刷新界面

        GlobalVars.currentBackgroundColorPanel = ToolButton(
            toolTip="设置背景色", clicked=self.setBackgroundColor)
        GlobalVars.CurrentBackgroundColor = GlobalVars.CurrentBackgroundColor  # 重新赋值，刷新界面

        GlobalVars.correctorPushPanel = ToolButton(
            "批", toolTip="批改所有内容", clicked=self.correctOP)  # 待完善

        GlobalVars.certifyCorrector = ToolButton(
            "定", toolTip="确定所有更改", clicked=self.certifyOP)

        GlobalVars.currentFontSuperScriptPanel = ToolButton(icon=QIcon("images/superscript.png"),
                                                            toolTip="上标")  # 上标待完善
        GlobalVars.currentFontSuperScriptPanel.setEnabled(False)
        GlobalVars.currentFontSubScriptPanel = ToolButton(icon=QIcon("images/subscript.png"),
                                                          toolTip="下标")  # 下标待完善
        GlobalVars.currentFontSubScriptPanel.setEnabled(False)
        GlobalVars.screenShotCapture = ToolButton(icon=QIcon('images/capture.png'),
                                                  toolTip='截屏识别',
                                                  clicked=self.screenShotCapture)

        font1Layout = QHBoxLayout()
        font1Layout.addWidget(GlobalVars.currentFontFamilyPanel)
        font1Layout.addWidget(GlobalVars.currentFontSizePanel)
        font2Layout = QHBoxLayout()
        font2Layout.addWidget(GlobalVars.correctorPushPanel)
        font2Layout.addWidget(GlobalVars.certifyCorrector)
        font2Layout.addWidget(GlobalVars.currentFontSuperScriptPanel)
        font2Layout.addWidget(GlobalVars.currentFontSubScriptPanel)
        font2Layout.addWidget(GlobalVars.screenShotCapture)
        font2Layout.addWidget(GlobalVars.currentFontItalicPanel)
        font2Layout.addWidget(GlobalVars.currentFontWeightPanel)
        font2Layout.addWidget(GlobalVars.currentTextColorPanel)
        font2Layout.addWidget(GlobalVars.currentBackgroundColorPanel)
        fontLayout = QVBoxLayout()
        fontLayout.addLayout(font1Layout)
        fontLayout.addLayout(font2Layout)

        # 段落相关设置
        GlobalVars.alignLeftPanel = ToolButton(
            QIcon("images/alignleft.png"), "", toolTip="左对齐")  # 待完善
        GlobalVars.alignLeftPanel.setEnabled(False)
        GlobalVars.alignCenterPanel = ToolButton(
            QIcon("images/aligncenter.png"), "", toolTip="中对齐")  # 待完善
        GlobalVars.alignCenterPanel.setEnabled(False)
        GlobalVars.alignRightPanel = ToolButton(
            QIcon("images/alignright.png"), "", toolTip="右对齐")  # 待完善
        GlobalVars.alignRightPanel.setEnabled(False)

        GlobalVars.currentLineSpacingPanel = LineEditWithSubButton(
            toolTip="设置行距大小", subButton="itemButton")
        GlobalVars.currentLineSpacingPanel.listWidget = LineSpacingPanel(
            self.parent(), func=self.setLineSpacing)
        GlobalVars.CurrentLineSpacing = GlobalVars.CurrentLineSpacing

        GlobalVars.currentLineSpacingPolicyPanel = ToolButton(clicked=self.setLineSpacingPolicy,
                                                              subButton="itemButton")
        GlobalVars.currentLineSpacingPolicyPanel.listWidget.addItem(
            ToolButton(icon=QIcon("images/absolute_linespacing.png"), toolTip="绝对行距",
                       clicked=lambda: self.setLineSpacingPolicy(GlobalVars.absLineSpacingPolicy)))
        GlobalVars.currentLineSpacingPolicyPanel.listWidget.addItem(
            ToolButton(icon=QIcon("images/relative_linespacing.png"), toolTip="相对行距",
                       clicked=lambda: self.setLineSpacingPolicy(GlobalVars.relLineSpacingPolicy)))
        GlobalVars.currentLineSpacingPolicyPanel.listWidget.setParent(
            self.parent())
        GlobalVars.CurrentLineSpacingPolicy = GlobalVars.CurrentLineSpacingPolicy  # 更新界面

        paragraph1Layout = QHBoxLayout()
        paragraph1Layout.addWidget(GlobalVars.currentLineSpacingPanel)
        paragraph2Layout = QHBoxLayout()
        paragraph2Layout.addWidget(GlobalVars.alignLeftPanel)
        paragraph2Layout.addWidget(GlobalVars.alignCenterPanel)
        paragraph2Layout.addWidget(GlobalVars.alignRightPanel)
        paragraph2Layout.addWidget(GlobalVars.currentLineSpacingPolicyPanel)
        paragraphLayout = QVBoxLayout()
        paragraphLayout.addLayout(paragraph1Layout)
        paragraphLayout.addLayout(paragraph2Layout)

        self.mainLayout.addLayout(fileLayout)
        self.mainLayout.addWidget(GlobalVars.titleLevelsPanel)
        self.mainLayout.addLayout(fontLayout)
        self.mainLayout.addLayout(paragraphLayout)

        self.setLayout(self.mainLayout)

        self.setAutoFillBackground(True)
        pal = QPalette()
        pal.setColor(QPalette.Background, GlobalVars.Panel_BackgroundColor)
        self.setPalette(pal)

    def saveDocument(self):
        document = GlobalVars.CurrentDocument
        if not document.path:
            if document.title:
                file, format = QFileDialog.getSaveFileName(self, "保存文件", "files/" + document.title,
                                                           "网页格式(*.html);;所有(*)")
            else:
                file, format = QFileDialog.getSaveFileName(
                    self, "保存文件", "files/document", "网页格式(*.html);;所有(*)")

            if file:
                if not document.title:  # 标题没有命名,自动定义文档标题
                    document.title = os.path.basename(file).split(".")[0]
                document.path = file
            else:
                return  # 不可少
        with open(document.path, "w", encoding="UTF-8") as f:
            f.write(document.toHtml())

    def saveDocumentAs(self):
        document = GlobalVars.CurrentDocument
        path = document.path
        if path:
            name, suffix = os.path.basename(path).split(".")  # 名字和后缀
            newPath = os.path.dirname(path) + name + "1." + suffix

            file, format = QFileDialog.getSaveFileName(
                self, "保存文件", newPath, "网页格式(*.html);;所有(*)")

            if file:
                with open(file, "w", encoding="UTF-8") as f:
                    f.write(document.toHtml())
                # 待完善 ，关闭旧文档，打开新文档
        else:
            self.saveDocument()

    def openDocument(self):
        # 待完善，判断是否保存现有文档或者新建文档选项卡
        file, suffix = QFileDialog.getOpenFileName(
            self, "打开文件", "files", "网页格式(*.html)")
        if file:
            with open(file, "r", encoding="UTF-8") as f:
                document = self.analysisHtml(f)  # 解析html文档
                document.path = file
                self.DocWidget.documentScrollArea.setWidget(document)
                self.update()
                print(True)

    def correctOP(self):
        block = self.DocWidget.documentScrollArea.document.RootBlock
        while block:
            text = ''
            index = 0
            itemSiteList = []
            textItem = block.RootTextItem
            while textItem:
                text += textItem.text
                itemSiteList.append(
                    (textItem, index, index + len(textItem.text)))
                index = index + len(textItem.text)
                textItem = textItem.nextTextItem
            results = corrector.correct(text)
            if results[1]:
                self.prepareCorrectGui(text, block, itemSiteList, results[1])
            block = block.nextBlock

    def certifyOP(self):
        block = self.DocWidget.documentScrollArea.document.RootBlock
        while block:
            textItem = block.RootTextItem
            while textItem:
                if isinstance(textItem, TextItemReload):
                    font, textColor, backgroundColor = self.getItemAttrs(
                        textItem)
                    textColor = textItem.oldTextColor
                    newTextItem = TextItem(
                        block, textItem.text, textItem, font, textColor, backgroundColor)
                    oldTextItem = textItem
                    textItem = textItem.nextTextItem
                    oldTextItem.deleteLater()
                    oldTextItem.delTextItem()
                else:
                    textItem = textItem.nextTextItem
            block = block.nextBlock

    def prepareCorrectGui(self, sourceText, block, itemSiteList, correctedText):
        for textItem, startSite, endSite in itemSiteList:
            font, textColor, backgroundColor = self.getItemAttrs(textItem)
            for _, text, startIndex, endIndex in correctedText:
                preText = sourceText[startSite:startIndex]
                wrongText = sourceText[max(
                    startSite, startIndex):min(endSite, endIndex)]
                afterText = sourceText[endIndex:endSite]
                # 无错误存在，直接跳过
                if not wrongText:
                    continue

                if preText:
                    preTextItem = TextItem(
                        block, preText, textItem.preTextItem, font, textColor, backgroundColor)
                    wrongTextItem = TextItemReload(block, wrongText, preTextItem, font, textColor, backgroundColor,
                                                   corrected_text=[text], parent=block)
                else:
                    wrongTextItem = TextItemReload(block, wrongText, textItem.preTextItem, font, textColor, backgroundColor,
                                                   corrected_text=[text], parent=block)
                if afterText:
                    textItem.setText(afterText)
                else:
                    textItem.delTextItem()
                startSite = endIndex

    def getItemAttrs(self, textItem):
        font = textItem.font
        textColor = textItem.textColor
        backgroundColor = textItem.backgroundColor
        return font, textColor, backgroundColor

    def setTextColor(self):
        color = QColorDialog.getColor(title="选择文字颜色")
        GlobalVars.CurrentTextColor = color
        if GlobalVars.CurrentDocument.SelBlocks:  # 处于选中状态 待优化，多个段落反复更新坐标降低性能
            for block in GlobalVars.CurrentDocument.SelBlocks:
                if hasattr(block, "setTextColor"):
                    block.setTextColor(color)
        else:
            if hasattr(GlobalVars.CurrentBlock, "setTextColor"):
                GlobalVars.CurrentBlock.setTextColor(color)

    def setBackgroundColor(self):
        color = QColorDialog.getColor(title="选择背景颜色")
        GlobalVars.CurrentBackgroundColor = color
        if GlobalVars.CurrentDocument.SelBlocks:  # 处于选中状态
            for block in GlobalVars.CurrentDocument.SelBlocks:
                if hasattr(block, "setBackgroundColor"):
                    block.setBackgroundColor(color)
        else:
            if hasattr(GlobalVars.CurrentBlock, "setBackgroundColor"):
                GlobalVars.CurrentBlock.setBackgroundColor(color)

    def setFont_(self):
        font, ok = QFontDialog.getFont()
        if ok:
            GlobalVars.CurrentFont = font
            if GlobalVars.CurrentDocument.SelBlocks:  # 处于选中状态
                for block in GlobalVars.CurrentDocument.SelBlocks:
                    if hasattr(block, "setFont_"):
                        block.setFont_(font)
            else:
                if hasattr(GlobalVars.CurrentBlock, "setFont_"):
                    GlobalVars.CurrentBlock.setFont_(font)

    def setFontFamily(self, family):
        font = QFont(GlobalVars.CurrentFont)
        font.setFamily(family)
        GlobalVars.CurrentFont = font  # 更新当前字体
        if GlobalVars.CurrentDocument.SelBlocks:  # 处于选中状态
            for block in GlobalVars.CurrentDocument.SelBlocks:
                if hasattr(block, "setFontFamily"):
                    block.setFontFamily(family)
        else:
            if hasattr(GlobalVars.CurrentBlock, "setFontFamily"):
                GlobalVars.CurrentBlock.setFontFamily(family)
        GlobalVars.currentFontFamilyPanel.listWidget.hide()

    def setFontItalic(self, italic=None):
        if italic is None:
            italic = not GlobalVars.CurrentFont.italic()
        font = QFont(GlobalVars.CurrentFont)
        font.setItalic(italic)
        GlobalVars.CurrentFont = font  # 刷新界面
        if GlobalVars.CurrentDocument.SelBlocks:  # 处于选中状态
            for block in GlobalVars.CurrentDocument.SelBlocks:
                if hasattr(block, "setFontItalic"):
                    block.setFontItalic(italic)
        else:
            if hasattr(GlobalVars.CurrentBlock, "setFontItalic"):
                GlobalVars.CurrentBlock.setFontItalic(italic)
        GlobalVars.currentFontItalicPanel.listWidget.hide()

    def setFontWeight(self, weight=None):
        if weight is None:
            weight = False if GlobalVars.CurrentFont.bold() else QFont.Bold
        font = QFont(GlobalVars.CurrentFont)
        font.setWeight(weight)
        GlobalVars.CurrentFont = font  # 刷新界面
        if GlobalVars.CurrentDocument.SelBlocks:  # 处于选中状态
            for block in GlobalVars.CurrentDocument.SelBlocks:
                if hasattr(block, "setFontWeight"):
                    block.setFontWeight(weight)
        else:
            if hasattr(GlobalVars.CurrentBlock, "setFontWeight"):
                GlobalVars.CurrentBlock.setFontWeight(weight)
        GlobalVars.currentFontWeightPanel.listWidget.hide()  # 隐藏字体粗度选项栏

    def setFontSize(self, size):
        font = QFont(GlobalVars.CurrentFont)
        font.setPointSize(size)
        GlobalVars.CurrentFont = font  # 刷新界面
        if GlobalVars.CurrentDocument.SelBlocks:  # 处于选中状态
            for block in GlobalVars.CurrentDocument.SelBlocks:
                if hasattr(block, "setFontSize"):
                    block.setFontSize(size)
        else:
            if hasattr(GlobalVars.CurrentBlock, "setFontSize"):
                GlobalVars.CurrentBlock.setFontSize(size)
        GlobalVars.currentFontSizePanel.listWidget.hide()  # 隐藏字体粗度选项栏

    # 设置标题
    def setTitleLevel(self, titleLevel):
        GlobalVars.CurrentTitleLevel = titleLevel
        if GlobalVars.CurrentDocument.SelBlocks:  # 选中状态
            for block in GlobalVars.CurrentDocument.SelBlocks:
                if hasattr(block, "setTitleLevel"):
                    block.setTitleLevel(titleLevel)
        else:
            if hasattr(GlobalVars.CurrentBlock, "setTitleLevel"):
                GlobalVars.CurrentBlock.setTitleLevel(titleLevel)

    def setLineSpacing(self, spacing):
        GlobalVars.CurrentLineSpacing = spacing
        if GlobalVars.CurrentDocument.SelBlocks:  # 处于选中状态
            for block in GlobalVars.CurrentDocument.SelBlocks:
                if hasattr(block, "setLineSpacing"):
                    block.setLineSpacing(spacing)
        else:
            if hasattr(GlobalVars.CurrentBlock, "setLineSpacing"):
                GlobalVars.CurrentBlock.setLineSpacing(spacing)
        GlobalVars.currentLineSpacingPanel.listWidget.hide()

    def setLineSpacingPolicy(self, policy=None):
        if not policy:
            if GlobalVars.CurrentLineSpacingPolicy is GlobalVars.relLineSpacingPolicy:
                policy = GlobalVars.absLineSpacingPolicy
            else:
                policy = GlobalVars.relLineSpacingPolicy
        GlobalVars.CurrentLineSpacingPolicy = policy
        if GlobalVars.CurrentDocument.SelBlocks:  # 处于选中状态
            for block in GlobalVars.CurrentDocument.SelBlocks:
                if hasattr(block, "setLineSpacingPolicy"):
                    block.setLineSpacingPolicy(policy)
        else:
            if hasattr(GlobalVars.CurrentBlock, "setLineSpacingPolicy"):
                GlobalVars.CurrentBlock.setLineSpacingPolicy(policy)
        GlobalVars.currentLineSpacingPolicyPanel.listWidget.hide()

    # 解析html格式 待优化,用beautifulsoap
    def analysisHtml(self, f):
        document = Document()
        text = f.readline()
        while text:
            if text.startswith("<body"):
                document.documentWidth = int(self.analysisStyle(text)[
                                             "width"][:-2])  # 去掉px字符
            if text.startswith("<title"):
                document.title = self.analysisText(text)
            if text.startswith("<h1") or text.startswith("<h2") or text.startswith("<h3") or text.startswith("<h4"):
                block = document.addTextBlock()
                text_ = self.analysisText(text)  # 文本内容

                block.addTextItem(text_, preTextItem=None)
                exec("block.setTitleLevel_(GlobalVars.T{})".format(text[2]))
            if text.startswith("<p"):
                block = document.addTextBlock()
            if text.startswith("<span"):
                attr = self.analysisStyle(text)  # 属性
                text = self.analysisText(text)  # 文本内容

                font = QFont()
                font.setFamily(attr["font-family"])
                font.setPointSize(int(attr["font-size"][0:-2]))
                font.setItalic(
                    True if attr['font-style'] == 'italic' else False)
                font.setBold(True if attr['font-weight'] == 'bold' else False)

                textColor = attr["color"]
                textColor = textColor[5:-1].split(",")
                textColor = [int(textColor[i]) for i in range(
                    3)] + [int(float(textColor[3]) * 255)]
                textColor = QColor(*textColor)

                backgroundColor = attr["background-color"]
                if backgroundColor == "none":
                    backgroundColor = None
                else:
                    backgroundColor = backgroundColor[5:-1].split(",")
                    backgroundColor = [int(backgroundColor[i]) for i in range(3)] + [
                        int(float(backgroundColor[3]) * 255)]
                    backgroundColor = QColor(*backgroundColor)

                block.addTextItem(
                    text, font=font, textColor=textColor, backgroundColor=backgroundColor)
            text = f.readline()
        return document

    # 分析html的style属性，返回字典
    def analysisStyle(self, text):
        text = re.search('style=".*"', text).group()  # style字段
        attr = text[text.find('"') + 1:text.rfind('"')]  # 属性字段
        attr = dict((i.split(":") for i in attr.split(";")))  # 属性转化为字典
        return attr

    # 分析html的字段，返回文字内容，限制在同一行
    def analysisText(self, text):
        text = re.search(">.*<", text).group()
        text = text[1:-1]
        return text

    def screenShotCapture(self):
        # RGBA to RGB
        img = ImageGrab.grabclipboard()
        if (img is None):
          print('Unable to read image from clipboard, please check with win + V')
          return
        img_ndarray = np.array(img.convert('RGB'))
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False)
        result = ocr.ocr(img_ndarray, cls=True)
        text = ''
        for line in result:
          text += line[1][0]
        # Copy the content to the clipboard
        pyperclip.copy(text)
        print('Recognize succeed, press CTRL + V to paste it into the text box')


class DocWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        initialize()  # 初始化一些参数
        self.ui()
        '''self.document = Document(self)
        block = self.document.addTextBlock()
        text1 = TextItem(block, "吃了一口凡，然后就火急火聊地炮走了")
        self.documentScrollArea.setDocument(self.document)
        text2 = TextItem(block, "对，就是一个测试！", preTextItem=text1)
        
        font = QFont(text1.font)
        self.text3 = TextItemReload(block, text='插入段落', preTextItem=text1, font=font,
                                    corrected_text=["测试1", "测试2"], parent=block)'''

    def ui(self):
        self.setWindowIcon(QIcon("images/icon.png"))
        self.setWindowTitle("文本批改编辑器")

        self.toolWidget = ToolWidget(self)
        self.toolWidget.move(0, 0)

        self.documentScrollArea = DocumentScrollArea(self)
        self.document = Document(self)
        self.documentScrollArea.setDocument(self.document)
        self.document.addTextBlockWithTextItem()  # 初始化

        layout = QVBoxLayout()
        layout.addWidget(self.toolWidget)
        documentLayout = QHBoxLayout()
        documentLayout.addStretch()
        documentLayout.addWidget(self.documentScrollArea)
        documentLayout.addStretch()
        layout.addLayout(documentLayout)
        self.setLayout(layout)

        self.setGeometry(200, 200, 1500, 800)  # 默认尺寸


def initialize():
    # 之所以将有关文字的内容放到这里，在其他地方定义后，计算pointsize会出错
    GlobalVars.CurrentFont = QFont("微软雅黑", pointSize=12)

    # 标题格式待完善，从设置提取
    GlobalVars.T0 = globalvars.TitleLevel(
        "正文", QFont("微软雅黑", pointSize=12, ), toHtmlFormat="p")
    GlobalVars.T1 = globalvars.TitleLevel("一级标题", QFont(
        "微软雅黑", pointSize=20, weight=QFont.Bold), toHtmlFormat="h1")
    GlobalVars.T2 = globalvars.TitleLevel("二级标题", QFont(
        "微软雅黑", pointSize=16, weight=QFont.Bold), toHtmlFormat="h2")
    GlobalVars.T3 = globalvars.TitleLevel("三级标题", QFont(
        "微软雅黑", pointSize=14, weight=QFont.Bold), toHtmlFormat="h3")
    GlobalVars.T4 = globalvars.TitleLevel("四级标题", QFont(
        "微软雅黑", pointSize=12, weight=QFont.Bold), toHtmlFormat="h4")
    GlobalVars.CurrentTitleLevel = GlobalVars.T0  # 默认为正文格式


def main():
    app = QApplication(sys.argv)
    doc = DocWidget()
    doc.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
