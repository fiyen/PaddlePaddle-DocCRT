# PaddlePaddle-DocCRT: 可视化文档纠错工具


本项目推出一个可视化的文档纠错工具，该工具可以实现简单的文档编辑和查错纠错功能。该项目github链接为[https://github.com/fiyen/PaddlePaddle-DocCRT](https://github.com/fiyen/PaddlePaddle-DocCRT) 欢迎多多fork。

注：此项目文档编辑部分参考了项目[Doc](https://github.com/yimuchens/doc)，文档纠错部分使用了超过fork数超过2k的[PyCorrector](https://github.com/shibing624/pycorrector)。

# 使用教程
## 下载安装
通过git命令下载该项目，并解压。


```python
!git clone https://github.com/fiyen/PaddlePaddle-DocCRT.git
```

## 运行
由于该项目需要调用PySide2实现界面操作，无法在线运行，感兴趣的话可以下载下来运行。


```python
#使用以下命令运行
!cd PaddlePaddle-DocCRT
!python main.py
```

运行成功后，将进入以下界面：

<img src="https://ai-studio-static-online.cdn.bcebos.com/9b792891f5744064869f8934f0ea4c30b6129ff633574bd4979fbe70579c1640" width="600"/>


可以直接点击/双击空白处进行文档编辑，效果如下：

<img src="https://ai-studio-static-online.cdn.bcebos.com/c148f662211e4afe8ef3bd879ee99c5b7283e85a12b64a1fb3a912ba57db2a17" width="600"/>

也可以直接复制粘贴(ctrl+v)相关内容。在编辑结束后，点击左上角功能栏“批”按键进行文本自动修改，第一次点击可能时间较长。

<img src="https://ai-studio-static-online.cdn.bcebos.com/3d027e6002154eb588bb8b3e1b91d4fd0e0d966556ea42059b950dfb2d19cf3e" width="600"/>

批改结束后，软件判断错误的地方会被标红：

<img src="https://ai-studio-static-online.cdn.bcebos.com/16cab2c38ad24e09bd416460f16e9dbb8f2af3174f654df1859f8a3e8b77cb78" width="600"/>

在标红的地方鼠标右击，会弹出功能窗口，除了“忽略此错误”和“撤销此更改”外，剩余部分为待选更正项，点击即可进行更正。

<img src="https://ai-studio-static-online.cdn.bcebos.com/5aeccf01541a474aad890056464e901fe7fd5fbf885a47faa080420c5baba7b1" width="600"/>

更正完成后，点击右上角功能栏的“定”按钮，即可接受已经进行的更改，将被标错误的文字恢复正常格式。

<img src="https://ai-studio-static-online.cdn.bcebos.com/62fd14adc8bf4481b514c9301cb15394a1577a4fd480478089437a4c31a83403" width="600"/>

处理纠错功能之外，工具还具备常见的一些文字编辑功能，如设置字体，大小，斜体，粗体，字体颜色以及背景颜色等。

<img src="https://ai-studio-static-online.cdn.bcebos.com/bba80bf67fba471cb74a0900a4abe3ca7cf4bd6370664a5c851c4e1ff740c4e1" width="600"/>

# 总结和展望
本项目是一个简单的工具实例demo，具体功能欢迎fork项目进行了解。以后将增加的内容包括：
1. 增加txt文档导入，导出
2. 增加word文档导入，导出
3. 增加批改模型选择（目前固定为ErnieModel）

**欢迎感兴趣的开发者更改和完善并提交pr，谢谢谢谢！**
