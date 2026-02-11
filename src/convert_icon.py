from PIL import Image
import os

# 转换gif为ico
gif_path = "assets/gifs/ameath.gif"
ico_path = "assets/gifs/ameath.ico"

img = Image.open(gif_path)
img.save(
    ico_path,
    format="ICO",
    sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
)
print(f"图标已保存到: {ico_path}")
