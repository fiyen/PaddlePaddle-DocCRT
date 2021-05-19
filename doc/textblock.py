from .block import Block
from time import time
from PySide2.QtGui import QFontMetrics, QPalette, QPainter, QColor, QFont
from PySide2.QtCore import QRect, Qt, QPoint, QTimer
from PySide2.QtWidgets import QApplication, QLabel
from .test import test
from . import globalvars

GlobalVars = globalvars.GlobalVars
SelStatus = globalvars.SelStatus
global CurrentTextItem
CurrentTextItem = None
global CurrentTextItemIndex  # currentTextItem的索引位置
CurrentTextItemIndex = None
global CurrentTextFragment
CurrentTextFragment = None


class readWord():
    """
    按单词读取，保证单词的连续性
    比如 "_ab1"返回"_","ab","1"
    """

    def __init__(self, text):
        self.text = str(text)
        self.textLength = len(self.text)

    def __iter__(self):
        self.index = 0
        return self

    def __next__(self):
        if self.index == self.textLength:  # 到达最后一个字符
            raise StopIteration
        else:
            text = ""
            while self.index != self.textLength:
                if self.text[self.index].encode("UTF-8").isalpha():  # 转变成utf-8判断
                    text += self.text[self.index]
                    self.index += 1
                else:
                    if not text:  # 直接读到非字母字符
                        text = self.text[self.index]
                        self.index += 1
                    break
            return text


class UpdateView():
    """
    决定是否立马更新视图等
    当需要界面更新时候,会更新坐标、大小、光标 等,反之,只更新基本属性即可，以节约性能
    """
    updateNone = 0  # 不更新
    updateAll = 1  # 更新所有，会影响后面的部分


class TextFragment():
    # 分别表示片段的起始x,y值，宽度，所占行高，文字内容，文字的起始纵坐标，文字的高度，在文本条中所占的索引范围
    def __init__(self, posX, posY, width, lineHeight, text, contentPosY, fontHeight, startIndex, endIndex):
        self.posX = posX
        self.posY = posY
        self.width = width
        self.lineHeight = self.preLineHeight = lineHeight  # prelinheight指的是由于前面的文字较大，导致本fragment行高较大，lineheight综合考虑前面和后面的文字大小
        self.text = text
        self.contentPosY = self.preContentPosY = contentPosY
        self.fontHeight = self.preFontHeight = fontHeight
        self.startIndex = startIndex
        self.endIndex = endIndex


class TextItem():
    @test("创建文本条")
    def __init__(self, textBlock=None, text="", preTextItem=False, font=None, textColor=None, backgroundColor=False,
                 updateView=UpdateView.updateAll):
        # 对初始值进行处理，可以单独分离，以节约性能，没必要
        if not textBlock:  # 可优化，不会对block的类型进行判断
            textBlock = GlobalVars.CurrentBlock
        if preTextItem is False:
            preTextItem = CurrentTextItem
        if not font:
            font = GlobalVars.CurrentFont
        if not textColor:
            textColor = GlobalVars.CurrentTextColor
        if backgroundColor is False:
            backgroundColor = GlobalVars.CurrentBackgroundColor

        self.textBlock = textBlock
        self.textFragments = []  # 默认为空

        self.preTextItem = preTextItem  # preTextItem为None，表示第一段
        if preTextItem:  # 不是第一个文字条
            self.nextTextItem = preTextItem.nextTextItem
            preTextItem.nextTextItem = self
            if self.nextTextItem:  # 后面有文本条
                self.nextTextItem.preTextItem = self
            else:  # 新建的是最后一个文本条
                self.textBlock.LastTextItem = self
        else:  # 段首插入文本条
            self.nextTextItem = self.textBlock.RootTextItem
            self.textBlock.RootTextItem = self
            if self.nextTextItem:  # 本段不是空段，有其他文本条
                self.nextTextItem.preTextItem = self
            else:  # 本段是空段
                self.textBlock.LastTextItem = self
        self.isSelected = False  # 用于判断是否处于选中状态
        self.font = None  # 不可少，否则setfont出错
        self.setFont(font, updateView=UpdateView.updateNone)  # 此时没有self.text，所以不能更新视图
        self.setTextColor(textColor)
        self.setBackgroundColor(backgroundColor)  # backgroundColor 为None,表示没有填充
        self.text = None  # 不可少，否则setText出错
        self.setText(text, updateView=updateView)
        self.setAsCurrentTextItem()

        if updateView:  # 跟新段落、光标等
            self.textBlock.updateSize()
            global CurrentTextItemIndex
            CurrentTextItemIndex = len(self.text)  # index更新到到item尾
            self.textBlock.updateCursor()  # 光标更新

    def setAsCurrentTextItem(self):
        global CurrentTextItem
        CurrentTextItem = self

    def setText(self, text, updateView=UpdateView.updateAll):
        if self.text != text:
            self.text = text
            if updateView:
                self.updateAllTextFragments()  # 生成textFragment
                self.setAsCurrentTextItem()
                global CurrentTextItemIndex
                CurrentTextItemIndex = len(text)
                self.textBlock.updateCursor()  # 更新光标

    def setFont(self, font, updateView=UpdateView.updateAll):  # 可优化，类变量调用改成局部变量调用
        if self.font != font:  # 刚开始没
            self.font = font
            self.fontMetrics = QFontMetrics(font)
            self.fontHeight = self.fontMetrics.height()
            self.lineHeight = self.textBlock.getLineHeight(
                self.fontHeight)  # 根据textBlock策略返回行高。默认根据字体越大，上下获得的间距也越大，产生更好的视觉效果
            self.contentPosY = (self.lineHeight - self.fontHeight) / 2  # 如果有填充，填充开始的纵坐标

            if updateView:
                self.updateAllTextFragments()

    def setTextColor(self, color):
        self.textColor = color

    def setBackgroundColor(self, color):  # color为None,表示没有填充
        self.backgroundColor = color

    @test("插入文字")
    def insertText(self, text, index=None, updateView=UpdateView.updateAll):
        global CurrentTextItemIndex
        if not index:
            index = CurrentTextItemIndex
        t = self.text  # 当前的text
        self.text = t[:index] + text + t[index:]
        if updateView:  # 更新视图
            self.updateAllTextFragments()  # 之所以和updatesize分开，是因为更新textfragment会导致nextTextItem相继更新，没有必要每一次都跟新段落大小
            CurrentTextItemIndex = index + len(text)
            self.textBlock.updateCursor()  # 更新光标

    @test("删除文字")
    def delText(self, startIndex=None, endIndex=None, updateView=UpdateView.updateAll):
        global CurrentTextItemIndex
        if startIndex is None:  # startindex可能为0
            startIndex = endIndex = CurrentTextItemIndex
        self.text = self.text[0:startIndex] + self.text[endIndex + 1:]
        if updateView:  # 立刻更新视图，比如回车删除，当进行多行或段文字删除等操作的时候，只需要最后统一更新
            self.updateAllTextFragments()
            self.setAsCurrentTextItem()
            CurrentTextItemIndex = startIndex
            self.textBlock.updateCursor()

    # 当字体改变或者从别处粘贴不同格式的文字的时候，会插入textItem,这个函数可在TextItem的文字中间插入新的textItem
    @test("插入textItem")
    def insertTextItem(self, index=None, updateView=UpdateView.updateAll):
        """
        插入新的textItem
        """
        global CurrentTextItem
        global CurrentTextItemIndex

        if not index:
            index = CurrentTextItemIndex  # index为None,根据当前光标位置插入

        if index == len(self.text):  # 在textIem结尾插入
            newTextItem = TextItem(self.textBlock, preTextItem=self, updateView=updateView)

        elif index == 0:  # 在文本条开头插入
            newTextItem = TextItem(self.textBlock, preTextItem=self.preTextItem,
                                   updateView=updateView)  # 定位到前一个文本条,item为None也可以

        else:  # 在textItem中间插入
            nnextText = self.text[index:]  # 这些文字会放到下下个文本条
            self.setText(self.text[0:index],
                         updateView=UpdateView.updateNone)  # 之所以不更新视图，是因为此时更新视图会引起文档滚动，原因应该是文档大小的调整引起的

            nnextItem = TextItem(self.textBlock, text=nnextText, preTextItem=self, font=self.font,
                                 textColor=self.textColor,
                                 backgroundColor=self.backgroundColor,
                                 updateView=UpdateView.updateNone)  # 先插入下下个文本条，之所以这么做，避免最后要重新定位
            newTextItem = TextItem(self.textBlock, preTextItem=self,
                                   updateView=UpdateView.updateNone)  # 插入的文字自动成为当前文本条，也不需要再计算索引
            self.updateAllTextFragments()

        return newTextItem

    @test("删除textitem")
    def delTextItem(self, updateView=UpdateView.updateAll):
        global CurrentTextItemIndex

        preTextItem = self.preTextItem
        nextTextItem = self.nextTextItem
        if preTextItem:  # 删除的非首句
            preTextItem.nextTextItem = nextTextItem
            if nextTextItem:  # 删除的是中间的item
                nextTextItem.preTextItem = preTextItem
            else:  # 删除的是最后一个item
                self.textBlock.LastTextItem = preTextItem
            if updateView:  # 是当前的textItem，因此要更新currentTextItem
                preTextItem.setAsCurrentTextItem()
                preTextItem.updateAllTextFragments()
                CurrentTextItemIndex = len(preTextItem.text)
                self.textBlock.updateCursor()
        else:  # 本段第一个item
            if nextTextItem:  # 不是本段最后一个item
                nextTextItem.preTextItem = None
                self.textBlock.RootTextItem = nextTextItem
                if updateView:
                    nextTextItem.setAsCurrentTextItem()
                    nextTextItem.updateAllTextFragments()
                    CurrentTextItemIndex = 0
                    self.textBlock.updateCursor()
            else:  # 本段只有一个item,本段文字全部删除
                self.textBlock.delBlock()
        del self

    def copyFrom(self, textItem, copyText=False,
                 updateView=UpdateView.updateAll):  # 继承textItem的属性,方便复制，默认不会复制文字，只会复制颜色、字体等属性
        if copyText:
            self.setText(textItem.text, updateView=updateView)
        self.setTextColor(textItem.textColor)
        self.setBackgroundColor(textItem.backgroundColor)
        self.setFont(textItem.font, updateView=updateView)
        if updateView:
            self.updateAllTextFragments()  # 可优化，对于颜色这些属性，不需要更新fragment 待完善，可以自由选择那些属性复制

    def italicWidth(self, text):  # 待优化，有些字符没有斜体
        """
        如果是斜体，要增加一定空间保证字符显示正确
        """
        if self.font.italic():
            return self.fontMetrics.width(text) / 2
        else:
            return 0

    @test("更新textFragment")
    def updateAllTextFragments(self):  # 自动区分单词 待优化，极端情况比旧算法慢二十倍,考虑只对dangqianitem更新的情况
        sta = time()  # 测试
        preTextItem = self.preTextItem
        fontMetricsWidth = self.fontMetrics.width
        italicWidth = self.italicWidth
        blockWidth = self.textBlock.BlockWidth
        lineHeight = self.lineHeight
        fontHeight = self.fontHeight
        contentPosY = self.contentPosY  # 填充的纵坐标便宜
        self.textFragments = []

        if preTextItem:  # 不是第一个item
            preFragment = preTextItem.textFragments[-1]
            fragmentStartPosX = preFragment.posX + preFragment.width
            fragmentStartPosY = preFragment.posY
        else:  # 第一个item
            fragmentStartPosX = 0
            fragmentStartPosY = 0
        if self.text:  # 有文字
            text = iter(readWord(self.text))  # 按照单词读取

            fragmentText = ""  # 当前fragment里的文字
            fragmentWidth = 0  # 当前摄入fragment的文字宽度
            fragmentStartIndex = 0
            fragmentEndIndex = -1
            # fragment 包括posX, posY, width, lineHeight, text, contentPosY, fontHeight, startIndex, endIndex这些属性，其中lineHeight fontHeight固定，只需要更新其他属性
            while True:
                try:
                    w = next(text)  # 读取单词
                    width = fontMetricsWidth(w)  # 当前摄入的单词宽度
                    italicwidth = italicWidth(w[-1])  # 耗费大量性能
                    while fragmentStartPosX + fragmentWidth + width + italicwidth > blockWidth:  # 超出单行限制 +fontMetricsWidth(])/2
                        if fragmentText:  # 前面有单词，因此先记录前面的单词，并生成新行
                            newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY,
                                                           fragmentWidth + italicWidth(
                                                               self.text[fragmentStartIndex - 1]),
                                                           lineHeight, fragmentText,
                                                           contentPosY + fragmentStartPosY,
                                                           fontHeight, fragmentStartIndex, fragmentEndIndex)
                            self.textFragments.append(newTextFragment)
                            self.updateLine()  # 更新行高 可优化，只有与不同大小的文字在同一行时，才需要考虑
                            preFragment = newTextFragment
                            fragmentStartPosX = 0
                            fragmentStartPosY = preFragment.posY + preFragment.lineHeight
                            fragmentText = ""  # 准备计算下一个textfragment
                            fragmentWidth = 0
                            fragmentStartIndex = fragmentEndIndex + 1  # fragmentendindex不变w没进行处理，因此继续循环
                        elif fragmentStartPosX != 0:  # 没有压入新的单词，但是前面有别的文字，因此直接新起一行，同时不会更新高度，同时会继续上述的循环，这也是while存在的意义
                            fragmentStartPosX = 0
                            fragmentStartPosY = preFragment.posY + preFragment.lineHeight
                            fragmentWidth = 0
                        else:  # 文字位于行头，证明必须要进行拆解才行，注意单个文字的存在
                            totalText = w  # 记录w，因为下面w会变化
                            totalwidth = width  # 记录w的总长度，因为下面width会变化
                            for c in w[1::-1]:  # 因为至少要留一个字符，所以不取第一位字符，这种方式从后向前调用，对于中文可大量节省时间
                                cwidth = fontMetricsWidth(c)  # 字符的宽度
                                width -= cwidth
                                w = w[:-1]
                                citalicwidth = italicWidth(c)
                                if fragmentWidth + citalicwidth <= blockWidth:  # 可以放下
                                    fragmentWidth = width  # 等同于framentWidth+=width
                                    fragmentText = w  # 等同于ftamentText+=w
                                    newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY,
                                                                   fragmentWidth + citalicwidth,
                                                                   lineHeight, fragmentText,
                                                                   contentPosY + fragmentStartPosY,
                                                                   fontHeight, fragmentStartIndex, fragmentEndIndex)
                                    self.textFragments.append(newTextFragment)
                                    preFragment = newTextFragment
                                    fragmentStartPosX = 0
                                    fragmentStartPosY = preFragment.posY + preFragment.lineHeight
                                    fragmentText = ""  # 准备计算下一个textfragment
                                    fragmentStartIndex = fragmentEndIndex + 1  # fragmentendindex不变
                                    w = totalText[len(w):]  # 更新 剩下的字符
                                    width = totalwidth - width  # 更新width
                                    continue  # 处理接下来的文字，也就是w
                            # 循环完了，依然大于宽度，证明第一个字符就很大，但是至少要压入一个字符
                            fragmentText = w
                            fragmentWidth = width
                            newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, fragmentWidth,
                                                           lineHeight, fragmentText,
                                                           contentPosY + fragmentStartPosY,
                                                           fontHeight, fragmentStartIndex, fragmentEndIndex)
                            self.textFragments.append(newTextFragment)
                            preFragment = newTextFragment
                            fragmentStartPosX = 0
                            fragmentStartPosY = preFragment.posY + preFragment.lineHeight
                            fragmentText = ""  # 准备计算下一个textfragment
                            fragmentStartIndex = fragmentEndIndex + 1  # fragmentendindex不变
                            w = totalText[1:]  # 更新 剩下的字符
                            width = totalwidth - width  # 更新width

                    fragmentText += w
                    fragmentWidth += width
                    fragmentEndIndex += len(w)  # 更新索引
                except StopIteration:
                    break
            newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY,
                                           fragmentWidth + italicWidth(fragmentText[-1]),
                                           lineHeight, fragmentText,
                                           contentPosY + fragmentStartPosY,
                                           fontHeight, fragmentStartIndex, fragmentEndIndex)  # 添加最后一个textfragment
            self.textFragments.append(newTextFragment)
            self.updateLine()  # 可优化，只有与不同大小的文字同处一行才需要判断
        else:  # 空的item
            newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, 0, lineHeight, "",
                                           contentPosY + fragmentStartPosY, fontHeight, 0, 0)
            self.textFragments.append(newTextFragment)
            self.updateLine()  # 可优化，只有与不同大小的文字同处一行才需要判断

        t = time() - sta  # 测试
        print(t, "稳定更新textFragment的时间")  # 测试
        self.updateHeightBoundary()  # 更新边界，为了鼠标定位使用

        if self.nextTextItem:
            self.nextTextItem.updateAllTextFragments()
        else:
            self.textBlock.updateSize()

    # 旧算法
    def updateAllTextFragment(self):  # 较为快速的更新方式
        sta = time()  # 测试

        self.textFragments = []  # 恢复默认
        text = self.text
        blockWidth = self.textBlock.BlockWidth
        fontMetricsWidth = self.fontMetrics.width
        fontHeight = self.fontHeight
        lineHeight = self.lineHeight
        contentPosY = self.contentPosY
        textLength = len(text)
        maxIndex = textLength - 1

        # 确定起始x坐标值
        if self.preTextItem:  # 前边有其他文本条
            preFragment = self.preTextItem.textFragments[-1]
            fragmentStartPosX = preFragment.posX + preFragment.width  # 可优化，可以将其存储起来，避免每次计算
            fragmentStartPosY = preFragment.posY
        else:  # 第一行文字
            fragmentStartPosX = 0
            fragmentStartPosY = 0
        fragmentStartIndex = fragmentEndIndex = 0
        # self, posX, posY, width, lineHeight, text, contentPosY, fontHeight, startIndex, endIndex textfragment的参数
        if text:  # 不是空的
            textWidth = fontMetricsWidth(text)  # 剩余文字需要的空间 总长度
            if fragmentStartPosX != 0:  # 先计算第一行
                line1Remainder = blockWidth - fragmentStartPosX
                if fontMetricsWidth(text[0]) > line1Remainder:  # 字体较大 第一个文字就超过了,另起新行
                    fragmentStartPosX = 0
                    fragmentStartPosY += preFragment.lineHeight
                else:
                    line1charnum = int(
                        line1Remainder / textWidth * textLength)  # 预估第一行的字数，lineremainder可能比textwidthremiande大，所以会越界,需要先将整个宽度计算一遍 ，可优化，取一个平均数计算
                    line1charnum = min(line1charnum, maxIndex)  # 确保不会越界
                    fragmentEndIndex = line1charnum
                    text1 = text[:fragmentEndIndex + 1]
                    text1Width = fontMetricsWidth(text1)
                    status = None
                    while True:
                        if text1Width == line1Remainder:  # 恰好占满一行
                            newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, text1Width,
                                                           lineHeight, text1, contentPosY + fragmentStartPosY,
                                                           fontHeight, fragmentStartIndex, fragmentEndIndex)
                            self.textFragments.append(newTextFragment)

                            # 下一行，不一定存在
                            fragmentStartIndex = fragmentEndIndex + 1
                            fragmentStartPosX = 0  # 第二行的开始横坐标
                            fragmentStartPosY = newTextFragment.posY + newTextFragment.lineHeight
                            break
                        elif text1Width < line1Remainder:
                            if status == 1:  # 上一个字符超出了文档宽度
                                newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, text1Width,
                                                               lineHeight, text1, contentPosY + fragmentStartPosY,
                                                               fontHeight, fragmentStartIndex, fragmentEndIndex)
                                self.textFragments.append(newTextFragment)

                                fragmentStartIndex = fragmentEndIndex + 1
                                fragmentStartPosX = 0
                                fragmentStartPosY = newTextFragment.posY + newTextFragment.lineHeight
                                break
                            else:
                                status = 0
                                fragmentEndIndex += 1
                                if fragmentEndIndex == textLength:  # 全部文字都在一行以内
                                    newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, text1Width,
                                                                   lineHeight, text1, contentPosY + fragmentStartPosY,
                                                                   fontHeight, fragmentStartIndex, fragmentEndIndex - 1)
                                    self.textFragments.append(newTextFragment)
                                    fragmentStartIndex = fragmentEndIndex  # 方便之后判断
                                    break
                                t = text[fragmentEndIndex]
                                text1 += t
                                text1Width += fontMetricsWidth(t)
                        else:
                            if status == 0:  # 上一个文字宽度小于文档宽度
                                text1Width -= fontMetricsWidth(text[fragmentEndIndex])
                                newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, text1Width,
                                                               lineHeight, text1[:-1],
                                                               contentPosY + fragmentStartPosY, fontHeight,
                                                               fragmentStartIndex, fragmentEndIndex - 1)
                                self.textFragments.append(newTextFragment)

                                fragmentStartIndex = fragmentEndIndex
                                fragmentStartPosX = 0
                                fragmentStartPosY = newTextFragment.posY + newTextFragment.lineHeight
                                break
                            else:
                                status = 1
                                text1 = text1[:-1]  # 如果文字较大，会自动到第二行 不需要单独考虑
                                text1Width -= fontMetricsWidth(text[fragmentEndIndex])
                                fragmentEndIndex -= 1
                    self.updateLine()
            if fragmentStartIndex != textLength:  # textitem 从0坐标开始 或者有第二行存在
                line2charnum = int(blockWidth / textWidth * textLength)  # 一行大概能容纳的字数
                while True:  # 计算不同的行
                    if fragmentStartIndex > maxIndex:  # 全部解析完毕
                        break
                    fragmentEndIndex = fragmentStartIndex + line2charnum  # 不需要考虑减一的问题，本来就是估计
                    fragmentEndIndex = min(fragmentEndIndex, maxIndex)  # 保证不越界
                    text2 = text[fragmentStartIndex:fragmentEndIndex + 1]
                    text2Width = fontMetricsWidth(text2)
                    status = None  # 恢复状态，用于判断
                    while True:
                        if text2Width == blockWidth:  # 恰好占满一行
                            newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, text2Width,
                                                           lineHeight, text2, contentPosY + fragmentStartPosY,
                                                           fontHeight, fragmentStartIndex, fragmentEndIndex)
                            self.textFragments.append(newTextFragment)

                            # 下一行
                            fragmentStartIndex = fragmentEndIndex + 1
                            fragmentStartPosY = newTextFragment.posY + newTextFragment.lineHeight
                            break
                        elif text2Width < blockWidth:
                            if status == 1:  # 上一个字符超出了文档宽度
                                newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, text2Width,
                                                               lineHeight, text2, contentPosY + fragmentStartPosY,
                                                               fontHeight, fragmentStartIndex, fragmentEndIndex)
                                self.textFragments.append(newTextFragment)

                                fragmentStartIndex = fragmentEndIndex + 1
                                fragmentStartPosY = newTextFragment.posY + newTextFragment.lineHeight
                                break
                            else:
                                status = 0
                                if fragmentEndIndex == maxIndex:  # 已经是最后一个字符
                                    newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, text2Width,
                                                                   lineHeight, text2, contentPosY + fragmentStartPosY,
                                                                   fontHeight, fragmentStartIndex, fragmentEndIndex)
                                    self.textFragments.append(newTextFragment)

                                    fragmentStartIndex = fragmentEndIndex + 1  # 之后判断需要
                                    break
                                fragmentEndIndex += 1
                                t = text[fragmentEndIndex]
                                text2 += t
                                text2Width += fontMetricsWidth(t)
                        else:
                            if status == 0:  # 上一个文字宽度小于文档宽度
                                text2Width -= fontMetricsWidth(text[fragmentEndIndex])
                                newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, text2Width,
                                                               lineHeight, text2[:-1],
                                                               contentPosY + fragmentStartPosY, fontHeight,
                                                               fragmentStartIndex, fragmentEndIndex - 1)
                                self.textFragments.append(newTextFragment)

                                fragmentStartIndex = fragmentEndIndex
                                fragmentStartPosY = newTextFragment.posY + newTextFragment.lineHeight
                                break
                            else:
                                status = 1
                                t = text2[:-1]
                                if not t:  # 字体较大，字符本身已经超出了行范围,但是每行至少应该有一个字符，否则会无休止循环下去
                                    newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, text2Width,
                                                                   lineHeight, text2, contentPosY + fragmentStartPosY,
                                                                   fontHeight, fragmentStartIndex, fragmentEndIndex)
                                    self.textFragments.append(newTextFragment)

                                    fragmentStartIndex = fragmentEndIndex + 1
                                    break
                                text2 = t
                                text2Width -= fontMetricsWidth(text[fragmentEndIndex])
                                fragmentEndIndex -= 1
        else:
            newTextFragment = TextFragment(fragmentStartPosX, fragmentStartPosY, 0,
                                           lineHeight, "", contentPosY + fragmentStartPosY,
                                           fontHeight, fragmentStartIndex,
                                           fragmentEndIndex)  # fragmentStartIndex, fragmentEndIndex均为0
            self.textFragments.append(newTextFragment)
            self.updateLine()

        self.updateHeightBoundary()  # 更新边界，为了鼠标定位使用

        t = time() - sta  # 测试
        print(t, "更新textFragment的时间")  # 测试

        if self.nextTextItem:
            self.nextTextItem.updateAllTextFragments()
        else:
            self.textBlock.updateSize()

    def updateLine(self):  # 在产生新行也就是产生新的textFragment的时候使用
        lastFragment = self.textFragments[-1]
        if lastFragment.posX != 0:  # 同一行中，前面有fragment
            preTextItem = self.preTextItem
            preFragment = preTextItem.textFragments[-1]
            if preFragment.preLineHeight <= lastFragment.preLineHeight:  # 当前的字符大小大于之前的
                preFragment.lineHeight = lastFragment.lineHeight
                preFragment.fontHeight = lastFragment.fontHeight
                preFragment.contentPosY = lastFragment.contentPosY
                preTextItem.updateLine()  # 前面的textitem更新 因为处于同行的一定是最后一个textFragment，不必担心出错

            else:  # 之前的大于当前的
                lastFragment.lineHeight = preFragment.lineHeight
                lastFragment.preLineHeight = preFragment.preLineHeight

                lastFragment.fontHeight = preFragment.fontHeight
                lastFragment.preFontHeight = preFragment.preFontHeight

                lastFragment.contentPosY = preFragment.contentPosY
                lastFragment.preContentPosY = preFragment.preContentPosY

    @test("更新textItem纵坐标范围")
    def updateHeightBoundary(self):  # 更新item高度范围，方便文字定位
        self.StartY = self.textFragments[0].posY
        self.EndY = self.textFragments[-1].posY + self.textFragments[-1].lineHeight

    def paint(self, painter):
        if self.textFragments:
            painter.setFont(self.font)
            painter.setPen(self.textColor)
            if self.backgroundColor:  # 有背景色
                for f in self.textFragments:
                    if self.isSelected:
                        painter.fillRect(QRect(f.posX, f.contentPosY, f.width, f.fontHeight),
                                         self.backgroundColor)  # 同行的填充色高度相同
                        painter.drawText(QRect(f.posX, f.contentPosY, f.width, f.fontHeight),
                                         int(Qt.AlignLeft | Qt.AlignBottom),
                                         f.text)  # 字体
                        painter.fillRect(QRect(f.posX, f.posY, f.width, f.lineHeight),
                                         GlobalVars.SelColor)
                    else:
                        painter.fillRect(QRect(f.posX, f.contentPosY, f.width, f.fontHeight),
                                         self.backgroundColor)  # 同行的填充色高度相同
                        painter.drawText(QRect(f.posX, f.contentPosY, f.width, f.fontHeight),
                                         int(Qt.AlignLeft | Qt.AlignBottom),
                                         f.text)  # 字体
            else:
                for f in self.textFragments:
                    if self.isSelected:
                        painter.drawText(QRect(f.posX, f.contentPosY, f.width + 4, f.fontHeight),  # 待优化 +4是为了应对斜体字的存在
                                         int(Qt.AlignLeft | Qt.AlignBottom),
                                         f.text)  # 字体
                        painter.fillRect(QRect(f.posX, f.posY, f.width, f.lineHeight),
                                         GlobalVars.SelColor)
                    else:
                        painter.drawText(QRect(f.posX, f.contentPosY, f.width + 4, f.fontHeight),  # 待优化 +4是为了应对斜体字的存在
                                         int(Qt.AlignLeft | Qt.AlignBottom),
                                         f.text)  # 字体


class Cursor(QLabel):
    """
    textblock的光标
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.isOpacity = False  # 用于光标的闪烁
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.cursorBlink)

        self.setFocusPolicy(Qt.NoFocus)
        self.resize(2, 20)
        self.show()

    def move(self, *args, **argv):
        super().move(*args, **argv)
        self.resize(3, CurrentTextFragment.fontHeight)

    def show(self):
        super().show()
        self.timer.start(500)  # 500毫秒闪烁一次

    def hide(self):
        super().hide()
        self.timer.stop()

    def cursorBlink(self):
        if self.isOpacity:
            self.setStyleSheet("background-color:rgba(0,0,0)")
        else:
            self.setStyleSheet("background-color:rgba(0,0,0,0)")
        self.isOpacity = not self.isOpacity


class TextBlock(Block):

    # 默认lineSpacing为fontHeight的1/8,相对行间距
    @test("创建textblock")
    def __init__(self, document, preBlock=None, float=False, lineSpacing=None,
                 lineSpacingPolicy=None, titleLevel=None):
        super().__init__(document, preBlock, float)
        self.RootTextItem = None
        self.LastTextItem = None
        self.SelItems = []  # 当拖动选择或搜索时候，存储选中的item

        global CurrentTextItem
        CurrentTextItem = None  # 不可少

        self.setAttribute(Qt.WA_InputMethodEnabled)  # 接受输入法事件
        self.lastInputMethodLength = 0  # 记录输入法predding的字符数，为了之后后删除输入的临时性的文字，以实现输入法更新
        self.disableInputMethod = False  # 用于输入法，避免调用输入法的同时，用户点击其他地方造成错误

        pal = QPalette()
        pal.setColor(QPalette.Background, Qt.red)
        self.setPalette(pal)

        if not lineSpacing:
            lineSpacing = GlobalVars.CurrentLineSpacing
        self.lineSpacing = lineSpacing  # 行高
        if not lineSpacingPolicy:  # 设置行间距的方法
            lineSpacingPolicy = GlobalVars.CurrentLineSpacingPolicy
        self.lineSpacingPolicy = lineSpacingPolicy

        self.Selector = []  # 选中的item和对应的index，支持多选，但现在不支持，格式为[firsritem startindex,lastitem,endindex]
        self.selDrawRects = []  # 拖动选择绘制的选区，是显示效果

        globalv = GlobalVars
        if not titleLevel:
            titleLevel = GlobalVars.T0
        self.TitleLevel = titleLevel

        self.cursor_ = Cursor(self)
        self.setFocus()

    # 根据textblock的spacingpolicy和textitem的字体大小，返回该textItem应有的行高
    def getLineHeight(self, fontHeight):
        if self.lineSpacingPolicy is GlobalVars.absLineSpacingPolicy:  # 绝对行间距
            return fontHeight + self.lineSpacing * 2
        else:
            return fontHeight + fontHeight * self.lineSpacing * 2  # 相对行间距

    # 设置行间距 待完善
    def setLineSpacing(self, spacing):
        if self.lineSpacing != spacing:
            self.lineSpacing = spacing
            textItem = self.RootTextItem
            while textItem:
                textItem.lineHeight = self.getLineHeight(
                    textItem.fontHeight)  # 根据textBlock策略返回行高。默认根据字体越大，上下获得的间距也越大，产生更好的视觉效果
                textItem.contentPosY = (textItem.lineHeight - textItem.fontHeight) / 2  # 如果有填充，填充开始的纵坐标
                textItem = textItem.nextTextItem
            self.RootTextItem.updateAllTextFragments()  # 统一更新

    # 设置行间距策略 待完善
    def setLineSpacingPolicy(self, policy):
        if self.lineSpacingPolicy is not policy:
            self.lineSpacingPolicy = policy
            textItem = self.RootTextItem
            while textItem:
                textItem.lineHeight = self.getLineHeight(
                    textItem.fontHeight)  # 根据textBlock策略返回行高。默认根据字体越大，上下获得的间距也越大，产生更好的视觉效果
                textItem.contentPosY = (textItem.lineHeight - textItem.fontHeight) / 2  # 如果有填充，填充开始的纵坐标
                textItem = textItem.nextTextItem
            self.RootTextItem.updateAllTextFragments()  # 统一更新

    # 设置标题等级
    def setTitleLevel_(self, titleLevel):
        """
        设置标题等级，直接设置不考虑有选中的文字的情况
        """
        if titleLevel is not GlobalVars.T0:  # 转变为其他格式的标题
            i = self.RootTextItem.nextTextItem
            text = ""
            while i:
                text += i.text
                nextItem = i.nextTextItem
                i.delTextItem(updateView=UpdateView.updateNone)
                i = nextItem
            self.RootTextItem.setText(self.RootTextItem.text + text, updateView=UpdateView.updateNone)
            self.RootTextItem.setFont(titleLevel.font, updateView=UpdateView.updateNone)
            self.RootTextItem.setTextColor(titleLevel.textColor)
            self.RootTextItem.setBackgroundColor(titleLevel.backgroundColor)
            self.RootTextItem.updateAllTextFragments()
            self.update()
        self.TitleLevel = titleLevel

    # 根据选择设置标题
    def setTitleLevel(self, titleLevel=None):
        if self.SelStatus is SelStatus.SelPart:  # 只在部分选中的状态下才考虑
            selContext = self.Selector[0]  # 待优化 不支持多选
            startItem, startIndex, endItem, endIndex = selContext
            if not all([startItem is self.RootTextItem, startIndex == 0, endItem is self.LastTextItem,
                        endIndex == len(self.LastTextItem.text) - 1]):  # 部分选中
                selItems = self.splitSeleted()
                nextBlock = TextBlock(self.document, preBlock=self)
                nextBlock.copyFrom(self, startTextItem=selItems[0], endTextItem=selItems[-1])
                nextBlock.setTitleLevel_(titleLevel)
                if selItems[-1].nextTextItem:  # 有后面的部分
                    nnextBlock = TextBlock(self.document, preBlock=nextBlock)
                    nnextBlock.copyFrom(self, startTextItem=selItems[-1].nextTextItem)
                item = selItems[0]

                while item:  # 可优化，判断是否已经是空段
                    nextItem = item.nextTextItem
                    item.delTextItem(updateView=UpdateView.updateNone)
                    item = nextItem

                self.RootTextItem.updateAllTextFragments()
                self.optimize()  # 优化

            else:
                self.setTitleLevel_(titleLevel)
                self.updateCursor()
        else:
            self.setTitleLevel_(titleLevel)
            self.updateCursor()
        self.deSelEvent()

    @test("新增textItem")
    def addTextItem(self, text="", preTextItem=False, font=None, textColor=None, backgroundColor=False,
                    updateView=UpdateView.updateAll):
        """
        对外接口，方便调用，同时保证公用textItem
        """
        newTextItem = TextItem(self, text, preTextItem, font, textColor, backgroundColor, updateView)
        return newTextItem

    # 字体变动
    def setFont_(self, font):
        if self.SelStatus is SelStatus.SelAll:  # 段落全部选中
            item = self.RootTextItem
            while item:
                item.setFont(font, updateView=UpdateView.updateNone)
                item = item.nextTextItem
            self.RootTextItem.updateAllTextFragments()
        elif self.SelStatus is SelStatus.SelPart:
            selItems = self.splitSeleted()  # 分裂所选内容
            for i in selItems:
                i.setFont(GlobalVars.CurrentFont, updateView=UpdateView.updateNone)
            selItems[0].updateAllTextFragments()
            self.optimize()  # 优化
        else:  # 没有选中
            currentTextItem = CurrentTextItem
            if currentTextItem.text:  # 当前item有文字，需要新建item
                item = currentTextItem.insertTextItem()  # 可优化 使用的不是font 而是Globals.CurrentFont
                item.setFont(font)  # 必须有
            else:
                CurrentTextItem.setFont(font)  # 空的item ，只需要更改属性

    def setFontFamily(self, family):
        if self.SelStatus is SelStatus.SelAll:  # 段落全部选中
            item = self.RootTextItem
            while item:
                font = QFont(self.font)
                font.setFamily(family)
                item.setFont(font, updateView=UpdateView.updateNone)
                item = item.nextTextItem
            self.RootTextItem.updateAllTextFragments()
        elif self.SelStatus is SelStatus.SelPart:
            if not self.SelItems:  # 处于选中状态第一次操作，先分离所选内容
                self.SelItems = self.splitSeleted()  # 分裂所选内容
                for i in self.SelItems:  # 待优化，可与下边合并
                    i.isSelected = True
                self.selDrawRects = []  # 取消选择框，由item自身完成绘制
            for i in self.SelItems:
                font = QFont(i.font)
                font.setFamily(family)
                i.setFont(GlobalVars.CurrentFont, updateView=UpdateView.updateNone)
            self.SelItems[0].updateAllTextFragments()
        else:  # 没有选中
            currentTextItem = CurrentTextItem
            if self is GlobalVars.CurrentBlock:  # 保证是当前blcok，避免误操作
                if currentTextItem.text:  # 当前item有文字，需要新建item
                    item = currentTextItem.insertTextItem()  # 注意 使用的是Globals.CurrentFont
                else:
                    font = QFont(currentTextItem.font)
                    font.setFamily(family)
                    CurrentTextItem.setFont(font)  # 空的item ，只需要更改属性

    def setFontItalic(self, italic):
        if self.SelStatus is SelStatus.SelAll:  # 段落全部选中
            item = self.RootTextItem
            while item:
                font = QFont(self.font)
                font.setItalic(italic)
                item.setFont(font, updateView=UpdateView.updateNone)
                item = item.nextTextItem
            self.RootTextItem.updateAllTextFragments()
        elif self.SelStatus is SelStatus.SelPart:
            if not self.SelItems:  # 处于选中状态第一次操作，先分离所选内容
                self.SelItems = self.splitSeleted()  # 分裂所选内容
                for i in self.SelItems:  # 待优化，可与下边合并
                    i.isSelected = True
                self.selDrawRects = []  # 取消选择框，由item自身完成绘制
            for i in self.SelItems:
                font = QFont(i.font)
                font.setItalic(italic)
                i.setFont(font, updateView=UpdateView.updateNone)
            self.SelItems[0].updateAllTextFragments()
        else:  # 没有选中
            currentTextItem = CurrentTextItem
            if self is GlobalVars.CurrentBlock:  # 保证是当前blcok，避免误操作
                if currentTextItem.text:  # 当前item有文字，需要新建item
                    item = currentTextItem.insertTextItem()  # 注意 使用的是Globals.CurrentFont
                else:
                    font = QFont(currentTextItem.font)
                    font.setItalic(italic)
                    CurrentTextItem.setFont(font)  # 空的item ，只需要更改属性

    def setFontWeight(self, weight):
        if self.SelStatus is SelStatus.SelAll:  # 段落全部选中
            item = self.RootTextItem
            while item:
                font = QFont(item.font)
                font.setWeight(weight)
                item.setFont(font, updateView=UpdateView.updateNone)
                item = item.nextTextItem
            self.RootTextItem.updateAllTextFragments()
        elif self.SelStatus is SelStatus.SelPart:
            if not self.SelItems:  # 处于选中状态第一次操作，先分离所选内容
                self.SelItems = self.splitSeleted()  # 分裂所选内容
                for i in self.SelItems:  # 待优化，可与下边合并
                    i.isSelected = True
                self.selDrawRects = []  # 取消选择框，由item自身完成绘制
            for i in self.SelItems:
                font = QFont(i.font)
                font.setWeight(weight)
                i.setFont(font, updateView=UpdateView.updateNone)
            self.SelItems[0].updateAllTextFragments()
        else:  # 没有选中
            currentTextItem = CurrentTextItem
            if self is GlobalVars.CurrentBlock:  # 保证是当前blcok，避免误操作
                if currentTextItem.text:  # 当前item有文字，需要新建item
                    item = currentTextItem.insertTextItem()  # 注意 使用的是Globals.CurrentFont
                else:
                    font = QFont(currentTextItem.font)
                    font.setWeight(weight)
                    CurrentTextItem.setFont(font)  # 空的item ，只需要更改属性

    def setFontSize(self, size):
        if self.SelStatus is SelStatus.SelAll:  # 段落全部选中
            item = self.RootTextItem
            while item:
                font = QFont(self.font)
                font.setPointSize(size)
                item.setFont(font, updateView=UpdateView.updateNone)
                item = item.nextTextItem
            self.RootTextItem.updateAllTextFragments()
        elif self.SelStatus is SelStatus.SelPart:
            if not self.SelItems:  # 处于选中状态第一次操作，先分离所选内容
                self.SelItems = self.splitSeleted()  # 分裂所选内容
                for i in self.SelItems:  # 待优化，可与下边合并
                    i.isSelected = True
                self.selDrawRects = []  # 取消选择框，由item自身完成绘制
            for i in self.SelItems:
                font = QFont(i.font)
                font.setPointSize(size)
                i.setFont(font, updateView=UpdateView.updateNone)
            self.SelItems[0].updateAllTextFragments()
        else:  # 没有选中
            currentTextItem = CurrentTextItem
            if self is GlobalVars.CurrentBlock:  # 保证是当前blcok，避免误操作
                if currentTextItem.text:  # 当前item有文字，需要新建item
                    item = currentTextItem.insertTextItem()  # 注意 使用的是Globals.CurrentFont
                else:
                    font = QFont(currentTextItem.font)
                    font.setPointSize(size)
                    CurrentTextItem.setFont(font)  # 空的item ，只需要更改属性

    def setTextColor(self, color):
        if self.SelStatus is SelStatus.SelAll:  # 全部选中
            item = self.RootTextItem
            while item:
                item.setTextColor(color)
                item = item.nextTextItem
        elif self.SelStatus is SelStatus.SelPart:  # 部分选中
            if not self.SelItems:  # 处于选中状态第一次操作，先分离所选内容
                self.SelItems = self.splitSeleted()  # 分裂所选内容
                for i in self.SelItems:  # 待优化，可与下边合并
                    i.isSelected = True
                self.selDrawRects = []  # 取消选择框，由item自身完成绘制
            for i in self.SelItems:
                i.setTextColor(color)
            self.SelItems[0].updateAllTextFragments()  # 待优化，颜色变动不需要全部更新文字
        else:  # 不选中
            currentTextItem = CurrentTextItem
            if currentTextItem.text:  # 当前item有文字，需要新建item
                item = currentTextItem.insertTextItem()
            else:
                CurrentTextItem.setTextColor(color)  # 空的item ，只需要更改属性

    def setBackgroundColor(self, color):
        if self.SelStatus is SelStatus.SelAll:  # 全部选中
            item = self.RootTextItem
            while item:
                item.setBackgroundColor(color)
                item = item.nextTextItem
        elif self.SelStatus is SelStatus.SelPart:  # 部分选中
            if not self.SelItems:  # 处于选中状态第一次操作，先分离所选内容
                self.SelItems = self.splitSeleted()  # 分裂所选内容
                for i in self.SelItems:  # 待优化，可与下边合并
                    i.isSelected = True
                self.selDrawRects = []  # 取消选择框，由item自身完成绘制
            for i in self.SelItems:
                i.setBackgroundColor(color)
            self.SelItems[0].updateAllTextFragments()  # 待优化，颜色变动不需要全部更新文字
        else:  # 不选中
            currentTextItem = CurrentTextItem
            if currentTextItem.text:  # 当前item有文字，需要新建item
                item = currentTextItem.insertTextItem()
            else:
                CurrentTextItem.setBackgroundColor(color)  # 空的item ，只需要更改属性

    def copyFrom(self, block, startTextItem=None, endTextItem=None,
                 updateView=UpdateView.updateAll):  # 继承block的属性,firstitem指的是开始复制的item
        if not startTextItem:
            startTextItem = block.RootTextItem
        if endTextItem:
            endTextItem = endTextItem.nextTextItem  # 不进行处理的话，下面的计算不包括lastitem
        item = startTextItem
        nextTextItem = None
        while item is not endTextItem:
            nextTextItem = TextItem(self, preTextItem=nextTextItem, updateView=UpdateView.updateNone)
            nextTextItem.copyFrom(textItem=item, copyText=True, updateView=UpdateView.updateNone)
            item = item.nextTextItem
        if updateView is UpdateView.updateAll:
            self.RootTextItem.updateAllTextFragments()  # 最后统一更新

    def showCursor(self):
        try:
            self.cursor_.show()
        except:
            pass

    def hideCursor(self):
        self.cursor_.hide()

    @test("根据点击位置更新索引和光标")
    def findTextIndexWithCursorUpdate(self, pos):  # 鼠标点击,更新curtextItem index和光标
        global CurrentTextItem
        global CurrentTextItemIndex
        global CurrentTextFragment
        pos, CurrentTextItem, CurrentTextItemIndex, CurrentTextFragment = self.findTextIndex(pos)

        GlobalVars.CurrentTextColor = CurrentTextItem.textColor  # 待完善，应该同步更新按钮颜色
        GlobalVars.CurrentBackgroundColor = CurrentTextItem.backgroundColor
        GlobalVars.CurrentFont = CurrentTextItem.font
        self.cursor_.move(pos)

    def findTextIndex(self, cursorPos):  # 根据坐标,返回准确的光标位置,currentTextItem和currentIndex
        textItem = self.RootTextItem
        cursorPosY = cursorPos.y()
        cursorPosX = cursorPos.x()
        while textItem:
            if textItem.StartY <= cursorPosY <= textItem.EndY:  # 点击点可能在此textitem里面，不确定
                for fragment in textItem.textFragments:
                    if (fragment.posY < cursorPosY < fragment.posY + fragment.lineHeight) and (
                            fragment.posX <= cursorPosX <= fragment.posX + fragment.width):  # 在此fragment里面,待优化，避免每次计算fragment.PosX+fragment.LineHeight，之所以只用大于，是为了排除空的textItem，因为具有行间距，一般人也不会在两行汇交的中间点击
                        currentTextItem = textItem
                        currentTextFragment = fragment
                        t = fragment.text
                        localCursorPosX = cursorPosX - fragment.posX  # 鼠标在fragment中的相对位置
                        x = 0
                        preX = 0  # 第一个字符所占的水平位置上界限是fragment的起始坐标
                        textLength = len(t)
                        for i in range(textLength):
                            tt = t[i]
                            xx = textItem.fontMetrics.width(tt)  # 字符ss的长度
                            x += xx  # i字符的位置
                            nextX = x - xx / 2  # i字符的水平方向的下界
                            if preX <= localCursorPosX <= nextX:  # 证明定位到i字符
                                currentTextItemIndex = i + fragment.startIndex

                                return QPoint(x - xx + fragment.posX,
                                              fragment.contentPosY), currentTextItem, currentTextItemIndex, currentTextFragment
                            else:
                                preX = nextX  # 上一个字符的下界是下一个字符的上界
                        currentTextItemIndex = textLength + fragment.startIndex  # 没有找到位置，证明在fragment的最后一个字符的后半部分点击
                        return QPoint(fragment.posX + fragment.width,
                                      fragment.contentPosY), currentTextItem, currentTextItemIndex, currentTextFragment
            textItem = textItem.nextTextItem

        currentTextItem = self.LastTextItem  # 点击空白位置，定位到段尾
        currentTextItemIndex = len(currentTextItem.text)
        lastFragment = currentTextItem.textFragments[-1]
        currentTextFragment = lastFragment
        return QPoint(lastFragment.posX + lastFragment.width,
                      lastFragment.contentPosY), currentTextItem, currentTextItemIndex, currentTextFragment

    # 根据当前的textItem和index更新光标
    @test("根据索引更新光标")
    def updateCursor(self):
        global CurrentTextFragment
        index = CurrentTextItemIndex
        currentTextItem = CurrentTextItem
        for fragment in currentTextItem.textFragments:  # 需要保证currenttextitem，currenttextfragment 和index正确性
            if fragment.startIndex <= index <= fragment.endIndex:  # 在其此fragment中
                CurrentTextFragment = fragment
                posX = currentTextItem.fontMetrics.width(fragment.text[:index - fragment.startIndex]) + fragment.posX
                self.cursor_.move(posX, fragment.contentPosY)
                return
        CurrentTextFragment = fragment
        self.cursor_.move(fragment.posX + currentTextItem.fontMetrics.width(fragment.text),
                          fragment.contentPosY)  # 位于textItem末尾

    def paste(self):  # 待完善，需要处理不同的格式
        cliboard = QApplication.clipboard()
        text=cliboard.text().split("\n")#以换行符分割
        CurrentTextItem.insertText(text[0], CurrentTextItemIndex)
        b=self
        for t in text[1:]:
            self.document.addTextBlockWithTextItem(b,t)
            b=b.nextBlock

    # 将所选内容分裂
    def splitSeleted(self):
        selTextItem = []  # 最后返回选中的item
        for selContext in self.Selector:  # selector放置了多个选择的内容
            startItem, startIndex, endItem, endIndex = selContext
            if startItem is endItem:  # 选中同一个item
                if startIndex == 0 and endIndex == len(startItem.text) - 1:  # 全部选中
                    selTextItem.append(startItem)
                else:
                    text = startItem.text[startIndex:endIndex + 1]
                    newItem = startItem.insertTextItem(endIndex + 1, updateView=UpdateView.updateNone)
                    newItem.copyFrom(startItem)  # 刷新格式
                    newItem.setText(text, updateView=UpdateView.updateNone)
                    startItem.setText(startItem.text[0:startIndex], updateView=UpdateView.updateAll)  # 待优化，只需要更新自身就行
                    selTextItem.append(newItem)
            else:  # 选中不同的item
                newItem = TextItem(self, text=startItem.text[startIndex:], preTextItem=startItem, updateView=False)
                startItem.setText(startItem.text[:startIndex], updateView=UpdateView.updateNone)

                newItem.copyFrom(startItem)
                item = newItem
                while item is not endItem:
                    selTextItem.append(item)
                    item = item.nextTextItem
                newItem = TextItem(self, text=endItem.text[:endIndex + 1], preTextItem=endItem.preTextItem,
                                   updateView=UpdateView.updateNone)
                newItem.copyFrom(endItem)
                selTextItem.append(newItem)
                endItem.setText(endItem.text[endIndex + 1:], updateView=UpdateView.updateNone)
                startItem.updateAllTextFragments()
        return selTextItem  # selTextItem是按textitem的顺序存放的

    def downSelEvent(self):
        super().downSelEvent()
        if self.SelStatus is SelStatus.SelPart:
            area = self.document.SelArea
            drawRects = self.selDrawRects  # 绘制选区的widget
            startPos = self.mapFromParent(self.page.mapFromParent(QPoint(area[0], area[1])))
            startX = startPos.x()
            startY = startPos.y()
            endPos = self.mapFromParent(self.page.mapFromParent(QPoint(area[2], area[3])))
            endX = endPos.x()
            endY = endPos.y()

            if startY < 0:  # 本段开头全部选中
                selStartTextItem = self.RootTextItem
                selStartTextFragment = selStartTextItem.textFragments[0]
                selStartTextItemIndex = 0
                selAreaStartPos = QPoint(0, selStartTextFragment.contentPosY)  # 绘制选择区域的最左上点
            else:  # 开头部分选中
                selAreaStartPos, selStartTextItem, selStartTextItemIndex, selStartTextFragment = self.findTextIndex(
                    QPoint(startX, startY))  # 找出最终坐标
            if endY > self.height():  # 选中到尾
                selEndTextItem = self.LastTextItem
                selEndTextFragment = selEndTextItem.textFragments[-1]
                selEndTextItemIndex = len(selEndTextItem.text) - 1
                selAreaEndPos = QPoint(self.width(), selEndTextFragment.contentPosY)  # 绘制选择区域的最右下点
                self.Selector.append(
                    [selStartTextItem, selStartTextItemIndex, selEndTextItem,
                     selEndTextItemIndex])  # textItem要减去1 待优化当选择空白区域时出错
            else:  # 段末没有全部选中
                selAreaEndPos, selEndTextItem, selEndTextItemIndex, selEndTextFragment = self.findTextIndex(
                    QPoint(endX, endY))  # 找出最终坐标
                self.Selector.append(
                    [selStartTextItem, selStartTextItemIndex, selEndTextItem,
                     selEndTextItemIndex - 1])  # textItem要减去1 待优化当选择空白区域时出错

            # 绘制选择区域
            if selAreaStartPos.y() == selAreaEndPos.y():  # 同一行
                drawRects.append(
                    QRect(selAreaStartPos.x(), selEndTextFragment.posY, selAreaEndPos.x() - selAreaStartPos.x(),
                          selStartTextFragment.lineHeight))
            else:  # 不是同一行选中
                drawRects.append(
                    QRect(selAreaStartPos.x(), selStartTextFragment.posY, self.width() - selAreaStartPos.x(),
                          selStartTextFragment.lineHeight))
                drawRects.append(QRect(0, selEndTextFragment.posY, selAreaEndPos.x(), selEndTextFragment.lineHeight))
                if selStartTextFragment.posY + selStartTextFragment.lineHeight != selEndTextFragment.posY:  # 中间有其他行选中
                    drawRects.append(QRect(0, selStartTextFragment.posY + selStartTextFragment.lineHeight, self.width(),
                                           selEndTextFragment.posY - selStartTextFragment.posY - selStartTextFragment.lineHeight))
        elif self.SelStatus is SelStatus.SelAll:  # 全部选中
            self.selDrawRects.append(QRect(0,0,self.width(),self.height()))
        self.update()

    def deSelEvent(self):
        super().deSelEvent()
        self.Selector = []
        self.selDrawRects = []
        if self.SelItems:
            self.optimize()  # 有选中，证明进行了更改
        for i in self.SelItems:
            i.isSelected = False
        self.SelItems = []
        self.update()

    @test("转换为html")
    def toHtml(self):
        self.optimize()  # 先进行优化
        if self.TitleLevel is GlobalVars.T0:  # 正文格式
            text = '<p style="width:{}px; lineSpacingPolicy:{}; lineSpacing:{}">\n'.format(self.BlockWidth,
                                                                                           self.lineSpacingPolicy,
                                                                                           self.lineSpacing)  # 一些属性，在html中没有意义
            textItem = self.RootTextItem
            while textItem:
                font = textItem.font
                fontFamily = font.family()
                fontSize = font.pointSize()
                italic = "italic" if font.italic() else "normal"
                weight = "bold" if font.bold() else "normal"  # 待完善，不止这两种
                lineHeight = self.getLineHeight(fontSize)  # 行高
                textColor = list(textItem.textColor.getRgb())
                textColor[3] /= 255  # 透明度转化为浮点数
                textColor = "rgba" + str(tuple(textColor))  # 转化为html格式
                backgroundColor = textItem.backgroundColor
                if backgroundColor:
                    backgroundColor = list(backgroundColor.getRgb())
                    backgroundColor[3] /= 255  # 透明度转化为小数
                    backgroundColor = "rgba" + str(tuple(backgroundColor))
                else:
                    backgroundColor = "none"
                text += '<span style="font-family:{};font-style:{};font-weight:{};font-size:{}pt;color:{};background-color:{};line-height:{}px">{}</span>\n'.format(
                    fontFamily, italic, weight, fontSize, textColor, backgroundColor, lineHeight,
                    textItem.text)  # 待完善使用pt作为单位，应该全部都使用pt
                textItem = textItem.nextTextItem
            text += "</p>\n"
        else:
            text = '<{} style="width:{}px; lineSpacingPolicy:{}; lineSpacing:{}">{}</{}>\n'.format(
                self.TitleLevel.toHtmlFormat,
                self.BlockWidth,
                self.lineSpacingPolicy,
                self.lineSpacing,
                self.RootTextItem.text,
                self.TitleLevel.toHtmlFormat)  # 一些属性，在html中没有意义
        return text

    def updateSize(self):  # textItem变动，进行更新
        lastItem_LastFragment = self.LastTextItem.textFragments[-1]
        self.resize(self.BlockWidth, lastItem_LastFragment.posY + lastItem_LastFragment.lineHeight)
        self.updateBlock()  # 之所以不用nextBlock.updayeBlock是因为nextblock可能为None，减少判断
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        textItem = self.RootTextItem
        while textItem:
            textItem.paint(p)
            textItem = textItem.nextTextItem
        if self.selDrawRects:  # 选中状态
            for r in self.selDrawRects:
                p.fillRect(r, GlobalVars.SelColor)  # 可优化，访问外部变量的时间较长

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        if self.lastInputMethodLength:  # 输入法启动的时候点击，删除输入法的残留文字
            self.disableInputMethod = True
            self.document.setFocus()  # 目的是为了清空输入法的内容
            self.setFocus()
        self.findTextIndexWithCursorUpdate(
            event.pos())  # 更新currentTextItem,currentTextItemIndexmCurrentTextFragment,self.cursor坐标
        event.ignore()  # 向document传递信息

    def focusInEvent(self, event):
        self.showCursor()
        GlobalVars#标题格式修改
        super().focusInEvent(event)

    @test("段落删除，获得焦点，与鼠标点击事件相对")
    def setFocus_(self, sign):  # sign为True是定位到段首，比如删除第一段,或使用向下键，False表示定位到段尾，比如删除后一段或使用向上键,默认定位到段首
        super().setFocus_(sign)
        global CurrentTextItem
        global CurrentTextItemIndex
        global CurrentTextFragment
        if sign:  # 后一段删除获得焦点
            CurrentTextItem = self.RootTextItem
            CurrentTextFragment = self.RootTextItem.textFragments[0]
            CurrentTextItemIndex = 0
            self.updateCursor()
        else:
            CurrentTextItem = self.LastTextItem
            CurrentTextFragment = self.LastTextItem.textFragments[-1]
            CurrentTextItemIndex = len(self.LastTextItem.text)
            self.updateCursor()

    @test("失去焦点")
    def focusOutEvent(self, event):
        # 待完善，拾取焦点的时候输入法会有残留
        self.delNullTextItem()
        self.hideCursor()
        super().focusOutEvent(event)

    # 删除空的textItem
    @test("删除空的文本条")
    def delNullTextItem(self):
        textItem = self.RootTextItem
        while textItem:
            nextItem = textItem.nextTextItem
            if not textItem.text:  # 空的文本条
                textItem.delTextItem(updateView=False)
            textItem = nextItem

    def optimize(self):  # 待优化，下面过程有重复
        self.delNullTextItem()
        item = self.RootTextItem
        while item:
            nextItem = item.nextTextItem
            if nextItem and item.font == nextItem.font and item.textColor == nextItem.textColor and item.backgroundColor == nextItem.backgroundColor:
                item.setText(item.text + nextItem.text)
                nextItem.delTextItem()
            else:
                item = nextItem
        self.RootTextItem.updateAllTextFragments()

    def delSelected(self):  # 删除选择内容
        selContext = self.Selector[0]  # 选中的内容 待完善，只是对一次选中的内容进行处理
        startItem, startIndex, endItem, endIndex = selContext
        if startItem is endItem:  # 选中同一个item
            startItem.delText(startIndex, endIndex)
        else:  # 选中不同的item
            startItem.delText(startIndex, len(startItem.text) - 1, updateView=False)
            item = startItem.nextTextItem
            while item is not endItem:
                nextItem = item.nextTextItem
                item.delTextItem(updateView=False)
                item = nextItem
            endItem.delText(0, endIndex, updateView=False)
            startItem.updateAllTextFragments()  # 更新视图

    @test("输入文字")
    def keyPressEvent(self, event):
        if self.SelStatus:  # 鼠标拖动选中状态
            event.ignore()  # 事件交由document处理
            return

        global CurrentTextItem
        global CurrentTextItemIndex
        key = event.key()
        if key == Qt.Key_Backspace:  # 空格删除
            index = CurrentTextItemIndex
            if index == 0:  # 位于句首
                preTextItem = CurrentTextItem.preTextItem
                if preTextItem:  # 前面有文字
                    CurrentTextItem = preTextItem
                    index = len(preTextItem.text) - 1
                    preTextItem.delText(index, index)
                elif len(CurrentTextItem.text) == 0:  # 删除
                    CurrentTextItem.delTextItem()
            else:
                index = CurrentTextItemIndex - 1
                CurrentTextItem.delText(index, index)
        elif key == Qt.Key_Return:
            currentTextItem = CurrentTextItem
            currentTextItemIndex = CurrentTextItemIndex
            if currentTextItem is self.LastTextItem and currentTextItemIndex == len(currentTextItem.text):  # 在段尾回车
                self.document.addTextBlockWithTextItem()
            elif currentTextItem is self.RootTextItem and currentTextItemIndex == 0:
                self.document.addTextBlockWithTextItem(self.preBlock)
            else:
                textItem = CurrentTextItem
                newTextItem = textItem.insertTextItem()

                newBlock = TextBlock(self.document, preBlock=self)  # 增加一个新段
                newBlock.copyFrom(self, startTextItem=newTextItem.nextTextItem)
                item = newTextItem
                while item:
                    nextItem = item.nextTextItem
                    item.delTextItem()
                    item = nextItem
        elif event.modifiers()==Qt.ControlModifier and key==Qt.Key_S:#待完善，为什么按钮的快捷键不能被识别
            pass

        else:
            CurrentTextItem.insertText(event.text(), CurrentTextItemIndex)
        event.accept()
        super().keyPressEvent(event)


    # 调用输入法事件
    def inputMethodEvent(self, event):
        if self.lastInputMethodLength:  # 证明已经在调用输入法
            self.setUpdatesEnabled(False)  # 暂停视图更新避免闪烁
            CurrentTextItem.delText(CurrentTextItemIndex - self.lastInputMethodLength,
                                    CurrentTextItemIndex - 1)  # 删除上一次文字
        CurrentTextItem.insertText(event.preeditString(), CurrentTextItemIndex)
        self.setUpdatesEnabled(True)
        self.lastInputMethodLength = len(event.preeditString())  # 值为0，代表一次输入事件结束

        if event.commitString():
            if self.disableInputMethod:  # 输入法禁用,在输入法输入时，点击了其他地方，目的是为了防止输入不必要的文字
                self.disableInputMethod = False  # 重新启用,
            else:
                CurrentTextItem.insertText(event.commitString(), CurrentTextItemIndex)

        super().inputMethodEvent(event)

    # 自动输入文字
    def inputText(self, text):
      CurrentTextItem.insertText(text, CurrentTextItemIndex)
