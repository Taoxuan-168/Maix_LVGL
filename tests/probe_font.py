import os

path = "/maixapp/share/font/SourceHanSansCN-Regular.otf"
print("exists:", os.path.exists(path))
if os.path.exists(path):
    print("size:", os.path.getsize(path))
    with open(path, "rb") as f:
        head = f.read(8)
    print("header:", head.hex(), head)

try:
    from maix import font
    print("maix.font:", [n for n in dir(font) if not n.startswith("_")])
    try:
        f = font.Font(path)
        print("Font ok:", f)
        print("Font attrs:", [n for n in dir(f) if not n.startswith("_")][:40])
    except Exception as e:
        print("Font load failed:", type(e).__name__, e)
except Exception as e:
    print("maix.font import failed:", type(e).__name__, e)
