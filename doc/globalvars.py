from PySide2.QtGui import QColor, QFont, QIcon, QPalette


# 定义标题等级，正文、一级标题等
class TitleLevel():
    def __init__(self, name, font, textColor=QColor(0, 0, 0), backgroundColor=None,
                 toHtmlFormat=None):  # 默认文字颜色为黑色,没有背景色 htmlFormat指存储为html格式时的标签，如h1 h2等
        self.name = name  # 标题等级名称，如正文、一级标题
        self.font = font  # 标题的字体
        self.textColor = textColor  # 标题的颜色
        self.backgroundColor = backgroundColor  # 标题的背景色
        self.toHtmlFormat = toHtmlFormat  # 存储为html格式时的标签，如h1 h2等
        GlobalVars.TitleLevels.append(self)


class SelStatus():
    """
    段落选中的状态
    """
    SelNone = 0  # 没有选中
    SelAll = 1  # 段落整个选中
    SelPart = 2  # 部分选中


# 全局变量设置
class GlobalVars_Class():
    def __init__(self):
        # 全局变量 待完善，可以自定义设置
        # 暂时用像素定义尺寸
        self.DocVersion = 1.01  # 文档版本
        self.CurrentDocument = None
        self.CurrentBlock = None
        # 页面设置
        self.PageVerticalMargin = 20  # 页面上下所留的边距，默认上下对称
        self.PageHorizontalMargin = 20  # 页面左右所留的边距，默认左右对称
        self.PageWidth = 1000  # 页面宽度
        self.PageHeight = 1500  # 页面高度
        # 文字格式设置
        self.CurrentFont = QFont()  # 默认字体，，不在这里定义，因为会出现pointsize计算不准确的问题
        self.CurrentTextColor = QColor(0, 0, 0)  # 默认文字颜色
        self.CurrentBackgroundColor = None  # None代表没有背景色
        # 段落行距设置
        self.absLineSpacingPolicy = 1  # 绝对行间距
        self.relLineSpacingPolicy = 0  # 相对行间距，意味着文字字体越大，间距越大
        self.CurrentLineSpacingPolicy = self.relLineSpacingPolicy
        self.CurrentLineSpacing = 0.25
        # 界面颜色
        self.SelColor = QColor(0, 100, 255, 150)  # 选中状态时候呈现的颜色
        # 面板相关设置
        self.Panel_BackgroundColor = QColor(255, 255, 255)  # 默认面板、工具栏、按钮等的背景色
        self.Panel_DarkerBackgroundColor = QColor(200, 200, 200)  # 第二种背景色，用于需要区分的地方
        self.Panel_ActivateColor = QColor(160, 200, 250)  # 面板、工具栏、按钮等激活后的的背景色
        self.Panel_FontFamily = "微软雅黑"  # 面板、工具栏、按钮等的字体
        self.TitleLevels = []  # 不同的标题等级的集合，如正文、一级标题等，标题格式在doc中定义，否则会出现pointsize计算不准确的问题
        # 读取html
        self.htmlFormat = {}  # 不同的html标签对应的类，决定了html格式如何打开

    def __setattr__(self, key, value):
        # 设置前景色或文字颜色
        if all([key == "CurrentTextColor", hasattr(self, key), hasattr(self, "currentTextColorPanel")]):
            p = QPalette()
            p.setColor(QPalette.ButtonText, value)
            self.currentTextColorPanel.mainWidget.setPalette(p)
            self.currentTextColorPanel.mainWidget.setFont(QFont(self.Panel_FontFamily, 15))
        # 设置背景色
        if all([key == "CurrentBackgroundColor", hasattr(self, "currentBackgroundColorPanel")]):
            if value:
                self.currentBackgroundColorPanel.mainWidget.setIcon(QIcon(""))  # 取消背景图标的显示
                self.currentBackgroundColorPanel.mainWidget.setStyleSheet(
                    "QPushButton{{background-color:rgba{};border:0px}} QPushButton:hover{{background-color:rgba{}}} ".format(
                        str(value.getRgb()), str(self.Panel_ActivateColor.getRgb())))  # 待优化 不利于修改
            else:
                self.currentBackgroundColorPanel.mainWidget.setIcon(QIcon("images/null.png"))  # 设置空的图标，表示没有背景色
                self.currentBackgroundColorPanel.mainWidget.setStyleSheet(
                    "QPushButton{{background-color:rgba{};border:0px}} QPushButton:hover{{background-color:rgba{}}} ".format(
                        str(self.Panel_BackgroundColor.getRgb()), str(self.Panel_ActivateColor.getRgb())))  # 待优化 不利于修改
        # 设置标题等级
        if all([key == "CurrentTitleLevel", hasattr(self, "titleLevelsPanel")]):
            self.titleLevelsPanel.setTitle(value)  # value为TitleLevel实例
        # 设置字体
        if all([key == "CurrentFont"]):
            # 字体设置
            if hasattr(self, "currentFontFamilyPanel"):
                self.currentFontFamilyPanel.mainWidget.setText(value.family())
                # 改变字体选择器的字体，方便查看
                font = self.currentFontFamilyPanel.font()
                font.setFamily(value.family())
                self.currentFontFamilyPanel.mainWidget.setFont(font)
            # 字体倾斜设置
            if hasattr(self, "currentFontItalicPanel"):
                isItalic = value.italic()
                if isItalic:
                    self.currentFontItalicPanel.mainWidget.setIcon(QIcon("images/italic.png"))  # 斜体
                    self.currentFontItalicPanel.setToolTip("斜体")
                else:
                    self.currentFontItalicPanel.mainWidget.setIcon(QIcon("images/notItalic.png"))  # 非斜体
                    self.currentFontItalicPanel.setToolTip("取消斜体")
            # 字体粗度设置
            if hasattr(self, "currentFontWeightPanel"):  # 待完善，不止有粗体和非粗体之分
                isBold = value.bold()
                if isBold:
                    self.currentFontWeightPanel.mainWidget.setIcon(QIcon("images/bold.png"))
                    self.currentFontWeightPanel.setToolTip("加粗")
                else:
                    self.currentFontWeightPanel.mainWidget.setIcon(QIcon("images/unbold.png"))
                    self.currentFontWeightPanel.setToolTip("取消加粗")
            # 字体大小设置
            if hasattr(self, "currentFontSizePanel"):
                self.currentFontSizePanel.mainWidget.setText(str(value.pointSize()))
        if all([key == "CurrentLineSpacingPolicy", hasattr(self, "currentLineSpacingPolicyPanel")]):
            if value is self.relLineSpacingPolicy:
                self.currentLineSpacingPolicyPanel.mainWidget.setIcon(QIcon("images/relative_linespacing.png"))
                self.currentLineSpacingPolicyPanel.setToolTip("相对行距")
            else:
                self.currentLineSpacingPolicyPanel.mainWidget.setIcon(QIcon("images/absolute_linespacing.png"))
                self.currentLineSpacingPolicyPanel.setToolTip("绝对行距")
        if all([key == "CurrentLineSpacing", hasattr(self, "currentLineSpacingPanel")]):
            self.currentLineSpacingPanel.mainWidget.setText(str(value))
        return super().__setattr__(key, value)


GlobalVars = GlobalVars_Class()
