from functools import wraps
global prefix  # 前缀，方便阅读
prefix = ""


# 本装饰器针对类函数,特别注意
def test(name=""):
    def dec(func):
        @wraps(func)
        def w1(*args, **argv):
            global prefix
            try:
                prefix += ("    ")
                print(prefix,name,end=" ")#打印函数的提示语
                # print(args[0],end=" ")#打印当前类的名称
                # print(func.__name__,end=" ")#打印当前函数名称
                print("")
                return func(*args, **argv)
            except Exception as e:
                raise e
            finally:
                prefix = prefix[:-4]
        return w1
    return dec
