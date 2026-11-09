import maix_lvgl as lv

print("ANIM_ENABLE:", int(lv.ANIM_ENABLE.OFF), int(lv.ANIM_ENABLE.ON))
print("SCREEN_LOAD_ANIM.FADE_ON:", int(lv.SCREEN_LOAD_ANIM.FADE_ON))
print("SYMBOL.OK:", lv.SYMBOL.OK.encode("utf-8").hex())
print("SYMBOL.CLOSE:", lv.SYMBOL.CLOSE.encode("utf-8").hex())
print("image_src_get_type:", lv.image_src_get_type(lv.SYMBOL.OK))
print("canvas_buf_size:", lv.canvas_buf_size(100, 100, 32, 400))
