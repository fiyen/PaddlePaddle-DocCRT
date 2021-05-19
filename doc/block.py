from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Qt, QEvent, QRect
from PySide2.QtGui import QKeySequence, QPainter, QPalette
from . import globalvars

GlobalVars = globalvars.GlobalVars
SelStatus = globalvars.SelStatus
from .test import test  # 测试


# 块，或者叫段落，是文档构成和扩展的基本要素
class Block(QWidget):
    @test("新建block")
    def __init__(self, document, preBlock, float=False):  # float表示是否是浮动段落
        super().__init__()
        self.setFocusPolicy(Qt.ClickFocus)  # 点击获得焦点
        self.setAttribute(Qt.WA_DeleteOnClose)  # 窗口关闭时候，自动删除,避免占用内存

        # 默认段落可以接受复制粘贴事件，具体方法可重写copy 和paste类函数
        self.grabShortcut(QKeySequence("ctrl+c"), Qt.ApplicationShortcut)
        self.grabShortcut(QKeySequence("ctrl+v"), Qt.ApplicationShortcut)

        self.document = document
        self.SelStatus = SelStatus.SelNone  # 拖动选择的时候，变成SelAll
        self.BlockWidth = document.RootPage.PageContentWidth  # 预设块宽度等于页面内容的宽度，updateBlock会重新更新
        self.posY = [0, 0]  # 初始化widget左侧两点的纵坐标，updateBlock会重新更新
        self.resize(self.BlockWidth, 100)  # 默认高度为20

        if float:  # 浮动段落
            pass  # 待完善
        else:  # 不是浮动段落，根据上一段位置，自上而下排列
            # 主要属性self.preblock self.nextblock self.documeny.Rootblock self.document.lastblock
            self.preBlock = preBlock
            if preBlock:  # 不是文档首段
                self.nextBlock = preBlock.nextBlock  # 复制preblock 的nextBlock属性
                preBlock.nextBlock = self  # 更新preblock
                if self.nextBlock:  # 有后段，本段为插入段
                    self.nextBlock.preBlock = self
                else:  # 本段为末段
                    self.document.LastBlock = self

            else:  # preBlock为None,本段为文档首段
                self.nextBlock = self.document.RootBlock
                self.document.RootBlock = self
                if self.nextBlock:  # 文档不是空的，在文档首处插入新段
                    self.nextBlock.preBlock = self
                else:  # 文档新建后的第一段
                    self.document.LastBlock = self
            self.updateBlock()  # 更新段落在页面上所处的位置
        self.setAsCurrentBlock()
        self.setFocus()  # 获取焦点
        self.show()

    # 更新段坐标
    @test("段落位置更新")
    def updateBlock(self):
        """
        # 更新段落在页面上所处的位置
        """
        # 待完善，每次全部更新浪费性能，应在换页符或恰好占满一页停止
        preBlock = self.preBlock
        if preBlock:  # 不是首段
            page = preBlock.page
            if self.height() + preBlock.posY[1] > page.PageContentHeight:  # 超过当前页的高度，需要新增页或移到下一页
                if page.nextPage:  # 移到下一页
                    page = page.nextPage
                    if self.height() > page.PageContentHeight:  # 段落高度超过了页面高度
                        page.PageHeight = self.height() + page.PageVerticalMargin * 2  # 设置页面高度，保证每页至少能容纳一段
                        page.resize(page.PageWidth, page.PageHeight)
                    self.setPage(page)
                    self.move(page.PageHorizontalMargin, page.PageVerticalMargin)
                    page.updatePage()
                else:  # 新建页
                    newPage = self.document.addPage(page)  # 新增页
                    if self.height() > newPage.PageContentHeight:  # 段落高度超过了页面高度
                        newPage.PageHeight = self.height() + newPage.PageVerticalMargin * 2  # 设置页面高度，保证每页至少能容纳一段
                        newPage.resize(newPage.PageWidth, newPage.PageHeight)
                    self.setPage(newPage)
                    self.move(newPage.PageHorizontalMargin, newPage.PageVerticalMargin)  # 会自动更新posY
                    page.updatePage()
            else:
                self.setPage(page)
                self.move(page.PageHorizontalMargin, preBlock.posY[1])  # 会自动更新posY
        else:
            page = self.document.RootPage
            self.setPage(page)
            if self.height() > page.PageContentHeight:  # 第一段超过第一页的高度，调整页大小
                page.PageHeight = self.height() + page.PageVerticalMargin * 2  # 设置页面高度，保证每页至少能容纳一段
                page.resize(page.PageWidth, page.PageHeight)
                page.updatePage()
            self.move(page.PageHorizontalMargin, page.PageVerticalMargin)

        if self.nextBlock:  # 不是尾段，调整后一段
            self.nextBlock.updateBlock()
        else:  # 已经是最后一段，查看是否删除无用的页面
            while self.page is not self.document.LastPage:  # 不是最后一页
                self.document.LastPage.delPage()  # 删除空页 待完善，没有考虑浮动段落的存在

    def setPage(self, page):
        self.page = page
        self.setParent(page)
        self.show()  # 不可少，当移动到别的页时，可能不会正常更新

    def setAsCurrentBlock(self):
        GlobalVars.CurrentBlock = self

    @test("删除块")
    def delBlock(self):
        preBlock = self.preBlock
        nextBlock = self.nextBlock
        if preBlock:  # 删除的不是首段
            preBlock.nextBlock = nextBlock
            if nextBlock:  # 删除的不是最后一段
                nextBlock.preBlock = preBlock
                nextBlock.updateBlock()
            else:  # 删除的是最后一段
                self.document.LastBlock = preBlock
                preBlock.updateBlock()
            preBlock.setFocus_(False)  # false表示定位到段尾部 最后一段删除，因此获得焦点
        else:  # 删除的是首段
            if nextBlock:  # 不是最后一段
                nextBlock.preBlock = None
                self.document.RootBlock = nextBlock
                nextBlock.updateBlock()
                nextBlock.setFocus_(True)  # 首段删除获得焦点，定位到头部
            else:  # 唯一一段
                self.document.initialization()  # 初始化document参数设置
        self.close()  # 关闭窗口，也是删除窗口

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        return
        # 测试代码，调试时候使用
        if self is GlobalVars.CurrentBlock:
            p.setPen(Qt.red)
            p.drawRect(2, 2, self.size().width() - 4, self.size().height() - 4)
        elif GlobalVars.CurrentBlock.preBlock and GlobalVars.CurrentBlock.preBlock is self:
            p.setPen(Qt.green)
            p.drawRect(2, 2, self.size().width() - 4, self.size().height() - 4)
        elif GlobalVars.CurrentBlock.nextBlock and GlobalVars.CurrentBlock.nextBlock is self:
            p.setPen(Qt.blue)
            p.drawRect(2, 2, self.size().width() - 4, self.size().height() - 4)
        if self is self.document.RootBlock:
            p.setPen(Qt.darkYellow)
            p.drawRect(8, 8, self.size().width() - 16, self.size().height() - 16)
        if self is self.document.LastBlock:
            p.setPen(Qt.darkCyan)
            p.drawRect(8, 8, self.size().width() - 16, self.size().height() - 16)

    def move(self, x, y):
        super().move(x, y)
        self.posY[0] = y  # 更新posY值，减少重复计算
        self.posY[1] = y + self.height()

    def resize(self, w, h):
        super().resize(w, h)
        self.posY[1] = self.posY[0] + h  # 更新posY值，减少重复计算

    @test("获取焦点")
    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.setAsCurrentBlock()
        self.document.update()  # 测试，对文档进行重绘以显示当前取得焦点的块

    @test("获取焦点")
    def setFocus_(self, sign=True):  # sign为True是定位到段首，比如删除第一段,或使用向下键，False表示定位到段尾，比如删除后一段或使用向上键,默认定位到段首
        self.setFocus()

    def event(self, event):
        if event.type() == QEvent.Shortcut:
            # 复制粘贴的快捷键设置
            if event.key() == QKeySequence("ctrl+c"):
                self.copy()
            if event.key() == QKeySequence("ctrl+v"):
                self.paste()
        return super().event(event)  # 必须用return

    # 复制
    def copy(self):
        pass

    # 粘贴
    def paste(self):
        pass

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.document.FirstSelBlock = self  # 第一个选中的块

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:  # 删除段落
            self.delBlock()

    # 默认向下拖动选中的事件，可以重写
    def downSelEvent(self):
        pass

    # 鼠标释放的时候的事件，目的是将一些消耗性能的操作放到最后完成
    def downSelConfirmEvent(self):
        self.downSelEvent()

    # 默认向上拖动选择的事件
    def upSelEvent(self):
        pass

    # 鼠标释放的时候的事件，目的是将一些消耗性能的操作放到最后完成
    def upSelConfirmEvent(self):
        self.upSelEvent()

    # 取消选择
    def deSelEvent(self):
        self.SelStatus = SelStatus.SelNone
