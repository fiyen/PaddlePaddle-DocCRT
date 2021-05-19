from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Qt, QPoint, QRect
from PySide2.QtGui import QPainter, QFont, QPalette
from . import globalvars

GlobalVars = globalvars.GlobalVars
from .test import test  # 测试


class A():
    pass


# 页面
class Page(QWidget, A):  # 直接用widget 的__setattr__会出问题
    @test("新建页面")
    def __init__(self, document, prePage):
        super().__init__(document)
        self.setAutoFillBackground(True)
        # pal = QPalette()#不能始终有效，不知道原因，在paintevent里绘制背景
        # pal.setColor(QPalette.Background, Qt.blue)
        # self.setPalette(pal)
        # 基本属性
        self.document = document
        self.setFocusPolicy(Qt.NoFocus)  # 不获得焦点
        self.setAttribute(Qt.WA_DeleteOnClose)  # 页面关闭时，自动删除,避免占用内存

        # 大小位置
        self.PosY = [0, 0]  # 初始化纵坐标的范围
        self.PageWidth = GlobalVars.PageWidth  # 页宽度
        self.PageHeight = GlobalVars.PageHeight  # 页高度
        self.PageVerticalMargin = GlobalVars.PageVerticalMargin  # 垂直边距
        self.PageHorizontalMargin = GlobalVars.PageHorizontalMargin  # 水平边距，自动更新ContentSize

        # 主要包括self.prePage self.nextPage self.document.RootPage self.document.lastPage这些属性
        self.prePage = prePage
        if prePage:  # 不是第一页
            self.nextPage = prePage.nextPage  # 继承上一页的属性
            prePage.nextPage = self  # 更新上一页属性
            if self.nextPage:  # 更新下一页属性
                self.nextPage.prePage = self
            else:  # 本段为末段
                self.document.LastPage = self

        else:  # prePage为None,第一页
            self.nextPage = self.document.RootPage
            self.document.RootPage = self
            if self.nextPage:  # 文档不是空的，插入第一页
                self.nextPage.prePage = self
            else:  # 文档新建后的第一段
                self.document.LastPage = self
        self.updatePageNumber()
        self.updatePage()  # 更新坐标
        self.show()
        # 更新坐标

    def updatePage(self):
        """
        更新页面位置和大小
        """
        prePage = self.prePage
        nextPage = self.nextPage
        if prePage:
            self.move(0, prePage.PosY[1])
        else:
            self.move(0, 0)
        if nextPage:
            nextPage.updatePage()
        else:  # 最后一页，调整document大小
            self.document.resize(GlobalVars.PageWidth, self.PosY[1])

    # 更新页码
    def updatePageNumber(self):
        if self.prePage:
            self.PageNumber = self.prePage.PageNumber + 1
        else:
            self.PageNumber = 1
        if self.nextPage:
            self.nextPage.updatePageNumber()

    # 删除页，不能删除第一页
    def delPage(self):
        """
        删除页面,同时更新文档大小
        """
        prePage = self.prePage
        nextPage = self.nextPage
        if prePage:  # 删除的不是首叶
            if nextPage:  # 删除的不是最后一段
                prePage.nextPage = nextPage
                nextPage.prePage = prePage
                nextPage.updatePage()  # 更新页面和大小
            else:  # 删除的是最后一页
                prePage.nextPage = None
                self.document.LastPage = prePage
                prePage.updatePage()  # 更新页面和大小
            prePage.updatePageNumber()
        else:  # 删除第一页
            if nextPage:  # 不是最后一页
                nextPage.prePage = None
                self.document.RootPage = nextPage
                nextPage.updatePageNumber()
                nextPage.updatePage()  # 更新页面和大小
            else:  # 删除唯一页
                return  # 不进行操作，文档至少要有一页
        self.close()  # 关闭窗口，也是删除窗口

    # 同时更新self.PosYRange属性
    def move(self, x, y):
        super().move(x, y)
        self.PosY[0] = y
        self.PosY[1] = y + self.height()

    def resize(self, w, h):
        super().resize(w, h)
        self.PosY[1] = self.PosY[0] + h

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.fillRect(QRect(0, 0, self.PageWidth, self.PageHeight), Qt.white)
        p.setFont(QFont("微软雅黑", pointSize=10))
        p.setPen(Qt.black)
        p.drawRect(self.PageHorizontalMargin, self.PageVerticalMargin, self.PageContentWidth, self.PageContentHeight)
        p.drawText(QPoint(0, self.PageVerticalMargin), str(self.PageNumber))

    def updatePageContentSize(self):  # 除去四周边距后的文档内容的宽度和高度
        """
        更新除去四周边距后的文档内容的宽度和高度
        """
        self.PageContentWidth = self.PageWidth - 2 * self.PageHorizontalMargin
        self.PageContentHeight = self.PageHeight - 2 * self.PageVerticalMargin

    def __setattr__(self, key, value):
        # 设置页面内容
        super(A, self).__setattr__(key, value)
        if any([
            key == "PageVerticalMargin", key == "PageHorizontalMargin", key == "PageWidth",
            key == "PageHeight"]):  # 设置页面大小时候，自动更新一些内容
            try:
                self.updatePageContentSize()  # 除去四周边距后的文档内容的宽度和高度
                self.resize(self.PageWidth, self.PageHeight)  # 调整页面大小
            except Exception as e:
                pass
