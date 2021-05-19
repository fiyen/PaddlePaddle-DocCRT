from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Qt
from PySide2.QtGui import QFont, QColor
from .page import Page
from .test import test  # 测试
from . import globalvars
from .textblock import TextBlock
from .block import Block

GlobalVars = globalvars.GlobalVars
SelStatus = globalvars.SelStatus


class Document(QWidget):
    @test("新建文档")
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)  # 文档捕获的焦点

        self.initialization()  # 初始化，文档不包含任何block
        self.DocumentWidth = GlobalVars.PageWidth  # 文档宽度
        self.path = ""  # 文档保存路径
        self.title = ""  # 文档标题

        self.SelArea = [0, 0, 0, 0]  # 鼠标拖选的起始点的横纵坐标和结束点的横纵坐标
        self.FirstSelBlock = None  # 当前获得焦点的块，也是上一次选中的块
        self.SelBlocks = []  # 所有选中的块

        # 新建页面
        self.RootPage = self.LastPage = None
        self.page = self.addPage(None)  # 新建第一页

        # 键盘按键
        self.isShiftPressed = False  # shift键是否按下
        self.isAltPressed = False  # alt键是否按下

        self.setAsCurrentDocument()
        self.show()

    def initialization(self):  # 初始状态，当没有block时候的状态
        GlobalVars.CurrentBlock = None
        self.RootBlock = None
        self.LastBlock = None

    def setAsCurrentDocument(self):
        GlobalVars.CurrentDocument = self
        GlobalVars.CurrentBlock = None  # 不可少，否则会出现当前document与当前block不对应的情况

    @test("添加空白文字段落")
    def addTextBlock(self, preBlock=False):
        """
        添加文本块，文本块没有文字，打开文件时使用
        """
        if preBlock is False:  # block可以为None,所以用false判断
            preBlock = GlobalVars.CurrentBlock
        newTextBlock = TextBlock(self, preBlock)
        return newTextBlock

    @test("新增段落")
    def addTextBlockWithTextItem(self, block=False, text=""):  # block为False表示在当前段落后添加abc_我的世界1
        """
        添加文本块，默认开头输入四个空格
        """

        newTextBlock = self.addTextBlock(block)
        newTextBlock.addTextItem(text)
        return newTextBlock

    def addBlankBlock(self, preBlock=False):
        """
        添加空白块，用于调试或增加段间距
        """
        if preBlock is False:
            preBlock = GlobalVars.CurrentBlock
        block = Block(self, preBlock)
        return block

    def addPage(self, page):
        """
        新增页面
        """
        newPage = Page(self, page)
        return newPage

    @test("导出html")
    def toHtml(self):
        """
        导出html格式
        """
        # text表示输出的html文字
        text = "<html>\n<style>\n"
        # css格式，定义标题关键字的格式
        for t in GlobalVars.TitleLevels:  # 将标题格式记录到css,包括默认正文格式
            font = t.font
            fontFamily = font.family()
            italic = "italic" if font.italic() else "normal"
            weight = "bold" if font.bold() else "normal"  # 待完善，不止这两种
            fontSize = font.pointSize()
            textColor = list(t.textColor.getRgb())
            textColor[3] /= 255  # 透明度转化为浮点数
            textColor = "rgba" + str(tuple(textColor))  # 转化为html格式
            backgroundColor = t.backgroundColor
            if backgroundColor:  # 待完善使用pt作为单位，应该全部都使用pt
                backgroundColor = list(backgroundColor.getRgb())
                backgroundColor[3] /= 255  # 透明度转化为小数
                backgroundColor = "rgba" + str(tuple(backgroundColor))
            else:
                backgroundColor = "none"

            text += "{}{{font-family:{};font-style:{};font-weight:{};font-size:{}pt;color:{};background-color:{}}}\n".format(
                t.toHtmlFormat,
                fontFamily,
                italic,
                weight,
                fontSize,
                textColor,
                backgroundColor)
        text += '</style>\n<head>\n'
        text += '<title>{}</title>\n'.format(self.title)
        text += '<docversion style="docVersion:{}"></docversion>\n'.format(GlobalVars.DocVersion)
        text += '</head>\n<body style="width:{}px">\n'.format(self.DocumentWidth)
        # 待完善 只处理段落，没有处理页面
        block = self.RootBlock
        while block:
            text += block.toHtml() + "\n"
            block = block.nextBlock
        text += '</body>\n</html>'
        print(text)
        return text

    def update(self, now_pos=None):
        #super().update()
        #return  # 测试，对所有块进行重绘，显示当前选中的块，rootBlock lastBlock
        block = self.RootBlock
        while block:
            if now_pos is not None:
                pass
            block.update()
            block = block.nextBlock

    # 取消选择
    def deSelEvent(self):
        """
        取消选择
        """
        if self.SelBlocks:
            for block in self.SelBlocks:
                block.deSelEvent()  # 对每个block进行操作
            self.SelBlocks = []  # 没有选中的块

    def delSelected(self):
        """
        删除选择的内容
        """
        for b in self.SelBlocks:
            b.delSelected()  # 对每个block进行操作
        self.deSelEvent()  # 清空选择

    def keyPressEvent(self, event):  # 选中状态有document处理空格
        super().keyPressEvent(event)
        event.accept()  # 事件不再向上传递
        key = event.key()
        if key == Qt.Key_Backspace:  # 选择状态下的退格删除命令
            self.delSelected()  # 此函数会判断是否有选中的内容

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        event.accept()
        self.addTextBlockWithTextItem()  # 双击增加新的文本段落

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        event.accept()

        if self.SelBlocks:  # 之前选中了块# 取消之前的选择
            self.deSelEvent()
        self.SelArea[0], self.SelArea[1] = event.x(), event.y()  # 鼠标单击开始坐标
        self.update()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        event.accept()
        self.mouseMoveAndReleaseEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        event.accept()
        self.mouseMoveAndReleaseEvent(event)

    def mouseMoveAndReleaseEvent(self, event):  # 拖动选择事件，供mouseMoveEvent 和mouseReleaseEvent使用
        x, y = event.x(), event.y()
        #print(event.pos())
        self.SelArea[2], self.SelArea[3] = x, y
        x1 = x - self.SelArea[0]
        y1 = y - self.SelArea[1]  # 坐标y的差值
        if self.SelBlocks:  # 每一次移动，先取消之前选中的块
            for block in self.SelBlocks:
                block.deSelEvent()
                self.SelBlocks = []

        block = self.FirstSelBlock
        #print(block.document)
        if y1 > 1 or x1 > 1:  # 向下选择
            while block:
                if block.page.mapToParent(block.pos()).y() < y:  # 待优化，记录block的全局坐标
                    block.SelStatus = SelStatus.SelAll  # 第一个和最后一个是部分选中
                    self.SelBlocks.append(block)
                    block = block.nextBlock
                else:
                    break
            if self.SelBlocks:
                self.SelBlocks[0].SelStatus = SelStatus.SelPart  # 有缺陷，认为不可能恰好完整的选取选中的第一段和最后一段
                self.SelBlocks[len(self.SelBlocks) - 1].SelStatus = SelStatus.SelPart
                for b in self.SelBlocks:  # 可优化，与上面合并，但会另增判断
                    b.downSelEvent()  # 块向下选中时的事件
            else:
                print('未选中任何块')

        elif y1 < -1:  # 向上选择
            while block:
                if block.page.mapToParent(block.pos()).y() < y:  # 待优化，记录block的全局坐标
                    block.SelStatus = SelStatus.SelAll  # 第一个和最后一个是部分选中
                    self.SelBlocks.append(block)
                    block = block.nextBlock
                else:
                    break
            if self.SelBlocks:
                self.SelBlocks[0].SelStatus = SelStatus.SelPart  # 有缺陷，认为不可能恰好完整的选取选中的第一段和最后一段
                self.SelBlocks[len(self.SelBlocks) - 1].SelStatus = SelStatus.SelPart
                self.SelBlocks = self.SelBlocks[::-1]
                for b in self.SelBlocks:  # 可优化，与上面合并，但会另增判断
                    b.upSelEvent()  # 块向上选中时的事件
            else:
                print('未选中任何块')

        self.update()
