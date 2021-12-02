from PIL import ImageGrab
from paddleocr import PaddleOCR
import numpy as np

# RGBA to RGB
img = ImageGrab.grabclipboard().convert('RGB')
img_ndarray = np.array(img)
ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False)
result = ocr.ocr(img_ndarray, cls=True)
text = result[0][1][0]
print(text)
# for line in result:
#     print(line)
