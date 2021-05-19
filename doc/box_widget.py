from PySide2.QtWidgets import QWidget, QScrollArea, QPushButton, QLineEdit, QSizePolicy, QHBoxLayout
from PySide2.QtGui import QPalette, QPainter, QBrush, QPainterPath, QFont, QIcon, QCursor
from PySide2.QtCore import Qt, QPoint, QTimer
from . import globalvars
from .test import test

GlobalVars = globalvars.GlobalVars


# 自定义的一些组件，方便后期修改
class ScrollArea(QScrollArea):
    def __init__(self, *args, **argv):
        super().__init__(*args, **argv)
        self.setFocusPolicy(Qt.ClickFocus)
        self.ScrollBarWidth = 12  # 滑动条宽度
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        s = ""
        s += "QScrollBar:vertical{{width:{}px;background:rgba{};margin:0px,0px,0px,0px;padding-top:10px;padding-bottom:10px}}".format(
            self.ScrollBarWidth, str(GlobalVars.Panel_DarkerBackgroundColor.getRgb()))
        s += "QScrollBar::handle:vertical{{width:{}px;background:rgba{}; border-radius:4px;min-height:30px}}".format(
            self.ScrollBarWidth, str(GlobalVars.Panel_DarkerBackgroundColor.getRgb()))
        s += "QScrollBar::handle:vertical:hover{{width:{}px;background:rgba{};border-radius:4px;min-height:30}}".format(
            self.ScrollBarWidth, str(GlobalVars.Panel_ActivateColor.getRgb()))
        s += "QScrollBar::add-line:vertical{{height:{}px;width:{}px;border-image:url(images/toparrow.png);subcontrol-position:top}}".format(
            self.ScrollBarWidth, self.ScrollBarWidth)
        s += "QScrollBar::sub-line:vertical{{height:{}px;width:{}px;border-image:url(images/bottomarrow.png);subcontrol-position:bottom}}".format(
            self.ScrollBarWidth, self.ScrollBarWidth)
        s += "QScrollBar:horizontal{{height:{}px;background:rgba{};margin:0px,0px,0px,0px;padding-left:10px;padding-right:10px}}".format(
            self.ScrollBarWidth, str(GlobalVars.Panel_DarkerBackgroundColor.getRgb()))
        s += "QScrollBar::handle:horizontal{{width:{}px;background:rgba{}; border-radius:4px;min-height:30px}}".format(
            self.ScrollBarWidth, str(GlobalVars.Panel_DarkerBackgroundColor.getRgb()))
        s += "QScrollBar::handle:horizontal:hover{{width:{}px;background:rgba{};border-radius:4px;min-height:30}}".format(
            self.ScrollBarWidth, str(GlobalVars.Panel_ActivateColor.getRgb()))
        s += "QScrollBar::add-line:horizontal{{height:{}px;width:{}px;border-image:url(images/rightarrow.png);subcontrol-position:right}}".format(
            self.ScrollBarWidth, self.ScrollBarWidth)
        s += "QScrollBar::sub-line:horizontal{{height:{}px;width:{}px;border-image:url(images/leftarrow.png);subcontrol-position:left}}".format(
            self.ScrollBarWidth, self.ScrollBarWidth)
        s += "QScrollArea{{background-color:rgba{}}} ".format(str(GlobalVars.Panel_BackgroundColor.getRgb()))
        self.setStyleSheet(s)

    def resize(self, w, h):
        w += self.ScrollBarWidth
        h += self.ScrollBarWidth
        super().resize(w, h)


class PushButton(QPushButton):
    """
    各种按钮的基类，方便统一控制样式
    """

    def __init__(self, *args, **argv):
        super().__init__(*args, **argv)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet(
            "QPushButton{{background-color:rgba{};border:0px}} QPushButton:hover{{background-color:rgba{}}} ".format(
                str(GlobalVars.Panel_BackgroundColor.getRgb()), str(GlobalVars.Panel_ActivateColor.getRgb())))


class LineEdit(QLineEdit):
    """
    lineEdit的基类，方便统一控制样式
    """

    def __init__(self, *args, **argv):
        super().__init__(*args, **argv)
        self.setStyleSheet("background-color:rgba{}".format(str(GlobalVars.Panel_BackgroundColor.getRgb())))


# 三角形下拉按键
class ItemButton(PushButton):
    def __init__(self, *args, **argv):
        super().__init__(*args, **argv)
        self.setFocusPolicy(Qt.NoFocus)
        self.resize(5, 5)  # 为了调用resizeevent
        self.setIcon(QIcon("images/itembutton.png"))

    def resize(self, w, h):
        w = h / 2  # 以h为基准调整
        super().resize(w, h)


# 列表widget
class ListWidget(ScrollArea):
    """
    在一个widget里添加不同的项。类似widgetlist但是每个项大小不一定一样
    """

    def __init__(self, *args, **argv):
        super().__init__(*args, **argv)
        self.setFocusPolicy(Qt.ClickFocus)
        self.widget_ = QWidget()  # 容纳widget的部件
        self.widget_.setFocusPolicy(Qt.NoFocus)
        self.widget_.setStyleSheet(
            "background-color:rgba{} ".format(str(GlobalVars.Panel_BackgroundColor.getRgb())))  # 统一颜色
        self.spacing = 5  # 边距，产生较好的视觉效果
        self.maxItemHeight = 0  # item总共的高度，也是下一个item的纵坐标
        self.maxItemWidth = 0
        self.maxHeight = 500  # 允许的最大的高度
        self.maxWidth = 200  # 允许的最大宽度

        self.setWidget(self.widget_)

    @test("失去焦点")
    def focusOutEvent(self, event):
        print("ListWidget is out focus")
        self.hide()

    @test("获得焦点")
    def focusInEvent(self, event):
        print('ListWidget is in focus')
        super().setFocus()
        pass

    def addItem(self, item):
        item.setParent(self.widget_)
        item.move(0, self.maxItemHeight)
        self.maxItemHeight += item.height() + self.spacing  # 下一个item的位置
        self.maxItemWidth = max(self.maxItemWidth, item.width())
        self.widget_.resize(self.maxItemWidth, self.maxItemHeight)
        self.resize(min(self.maxItemWidth, self.maxWidth), min(self.maxItemHeight, self.maxHeight))

    def clearWidget_(self):
        self.widget_ = QWidget()
        self.maxItemHeight = 0
        self.maxItemWidth = 0
        self.setWidget(self.widget_)

    def leaveEvent(self, event):
        self.hide()


# 带有次级按钮的widget
class WidgetWithSubButton(QWidget):
    """
    带有次级按钮的widget
    """

    def __init__(self, mainWidgetCls, *args, **argv):
        if argv.__contains__("subButton"):  # 需要添加subButton
            subButton = argv["subButton"]
            if not isinstance(subButton, tuple):  # 转换为列表，方便判断
                subButton = [subButton]
            del argv["subButton"]
        else:
            subButton = None
        self.mainWidget = mainWidgetCls(*args, **argv)
        if self.mainWidget.parent():
            super().__init__(self.mainWidget.parent())
        else:
            super().__init__()
        self.mainWidget.setParent(self)

        if subButton:
            for b in subButton:
                if b == "itemButton":
                    self.itemButton = ItemButton(self, clicked=self.click)
                    self.listWidget = ListWidget(self.parent())  # 默认使用self的父对象
                    self.listWidget.hide()
        self.resize(100, 25)  # 避免用户忽略更新

    def resize(self, w, h):
        self.mainWidget.resize(w, h)  # 默认的pushbutton是正方形的
        if hasattr(self, "itemButton"):
            self.itemButton.resize(w, h)  # 自动调整大小
            self.itemButton.move(w, 0)
            w += self.itemButton.width()
        super().resize(w, h)
        self.setMinimumSize(w, h)

    def click(self):
        pos = QPoint(self.x(), self.y() + self.height())
        self.listWidget.move(self.listWidget.parent().mapFromGlobal(self.parent().mapToGlobal(pos)))
        self.listWidget.raise_()
        self.listWidget.show()
        self.listWidget.focusInEvent(None)

    def enterEvent(self, event):
      self.click()


# 按钮，可以添加刺激按钮如下拉栏等
class ToolButton(WidgetWithSubButton):
    """
    按钮，可以添加刺激按钮如下拉栏等
    """

    def __init__(self, *args, **argv):  # 类型不是QPushButton，尽量模拟QPushButton的行为，易于使用
        super().__init__(PushButton, *args, **argv)
        self.resize(25, 25)

    def enterEvent(self, event):
      pass


# 带有次级按钮的lineEdit
class LineEditWithSubButton(WidgetWithSubButton):
    """
    带有次级按钮的lineEdit
    """

    def __init__(self, *args, **argv):
        super().__init__(LineEdit, *args, **argv)
        self.mainWidget.setFocusPolicy(Qt.NoFocus)  # 待完善，不能输入
        self.resize(100, 30)  # 这个大小等于self.mainWidget的大小，只需要调整这个大小，mainWidget和itemButton会自动调整大小
