"""Idempotent patches for LVGL 9.1.0 defects hit by the maix_lvgl binding.

Applied from ``regenerate_binding.ensure_binding`` before every build, so a
fresh LVGL download (or a clean MaixCDK tree) gets the same fixes.

1. ``lv_observer_remove`` freed an observer but left the object's
   ``LV_EVENT_DELETE`` hook pointing at it.  Deleting the object (or
   ``lv_deinit``) then dereferenced freed memory and crashed.
2. ``lv_canvas_copy_buf`` asserted ``cf != dest_cf`` with the condition
   inverted; same-format copies hit ``LV_ASSERT_HANDLER`` (``while(1)``).
"""
from __future__ import annotations

from pathlib import Path

OBSERVER_MARKER = "maix_lvgl: drop the object"
OBSERVER_OLD = """void lv_observer_remove(lv_observer_t * observer)
{
    LV_ASSERT_NULL(observer);

    observer->subject->notify_restart_query = 1;
"""
OBSERVER_NEW = """void lv_observer_remove(lv_observer_t * observer)
{
    LV_ASSERT_NULL(observer);

    /* maix_lvgl: drop the object's LV_EVENT_DELETE hook as well.  Without
     * this the hook keeps a dangling observer pointer and deleting the
     * object (or lv_deinit()) crashes. */
    if(observer->target != NULL) {
        lv_obj_remove_event_cb_with_user_data(observer->target, unsubscribe_on_delete_cb, observer);
    }

    observer->subject->notify_restart_query = 1;
"""

UNSUBSCRIBE_OLD = """static void unsubscribe_on_delete_cb(lv_event_t * e)
{
    lv_observer_t * observer = lv_event_get_user_data(e);
    lv_observer_remove(observer);
}"""
UNSUBSCRIBE_NEW = """static void unsubscribe_on_delete_cb(lv_event_t * e)
{
    lv_observer_t * observer = lv_event_get_user_data(e);
    /* maix_lvgl: the object is being deleted; do not try to remove the
     * delete hook that is currently running. */
    observer->target = NULL;
    lv_observer_remove(observer);
}"""

CANVAS_OLD = (
    'LV_ASSERT_MSG(canvas->draw_buf->header.cf != dest_buf->header.cf, '
    '"Color formats must be the same");'
)
CANVAS_NEW = (
    'LV_ASSERT_MSG(canvas->draw_buf->header.cf == dest_buf->header.cf, '
    '"Color formats must be the same");'
)


def _patch(path: Path, old: str, new: str, marker: str, label: str, log) -> bool:
    if not path.is_file():
        raise RuntimeError(f"LVGL patch target missing: {path}")
    text = path.read_text(encoding="utf-8")
    if new in text or (marker and marker in text):
        return False
    if old not in text:
        raise RuntimeError(f"LVGL patch pattern not found in {path}: {label}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    log(f"patched LVGL: {label}")
    return True


def _apply_freetype_face_lock(root: Path, log) -> int:
    """Serialize FreeType FT_Face access (backport from LVGL 9.2.0).

    LVGL 9.1.0's FreeType cache callbacks call FT_Load_Glyph / FT_Render_Glyph
    from the render thread while another thread can access the same FT_Face.
    FreeType faces are not thread-safe; the resulting race can leave the glyph
    cache stuck.  9.2.0 adds a per-cache-node face_lock; backport it here.
    """
    changed = 0
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_private.h",
        "    FT_Face face;\n\n    /*glyph cache*/",
        "    FT_Face face;\n    lv_mutex_t face_lock;\n\n    /*glyph cache*/",
        "",
        "FreeType cache node face_lock field",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype.c",
        "    node->face = face;\n\n    return true;\n}\nstatic void cache_node_cache_free_cb",
        "    node->face = face;\n    lv_mutex_init(&node->face_lock);\n\n    return true;\n}\nstatic void cache_node_cache_free_cb",
        "",
        "init FreeType face_lock",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype.c",
        "    FT_Done_Face(node->face);\n\n    if(node->glyph_cache) {",
        "    FT_Done_Face(node->face);\n    lv_mutex_delete(&node->face_lock);\n\n    if(node->glyph_cache) {",
        "",
        "delete FreeType face_lock",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_glyph.c",
        "    lv_font_glyph_dsc_t * dsc_out = &data->glyph_dsc;\n\n    FT_Face face = dsc->cache_node->face;",
        "    lv_font_glyph_dsc_t * dsc_out = &data->glyph_dsc;\n\n    lv_mutex_lock(&dsc->cache_node->face_lock);\n\n    FT_Face face = dsc->cache_node->face;",
        "",
        "lock glyph cache create",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_glyph.c",
        '        FT_ERROR_MSG("FT_Load_Glyph", error);\n        return false;',
        '        FT_ERROR_MSG("FT_Load_Glyph", error);\n        lv_mutex_unlock(&dsc->cache_node->face_lock);\n        return false;',
        "",
        "unlock glyph cache error",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_glyph.c",
        "    dsc_out->is_placeholder = glyph_index == 0;\n    dsc_out->glyph_index = glyph_index;\n\n    return true;",
        "    dsc_out->is_placeholder = glyph_index == 0;\n    dsc_out->glyph_index = glyph_index;\n\n    lv_mutex_unlock(&dsc->cache_node->face_lock);\n\n    return true;",
        "",
        "unlock glyph cache create",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_image.c",
        "    FT_Error error;\n\n    FT_Face face = dsc->cache_node->face;\n    FT_Set_Pixel_Sizes(face, 0, dsc->size);\n    error = FT_Load_Glyph(face, data->glyph_index,  FT_LOAD_RENDER | FT_LOAD_TARGET_NORMAL);",
        "    FT_Error error;\n\n    lv_mutex_lock(&dsc->cache_node->face_lock);\n\n    FT_Face face = dsc->cache_node->face;\n    FT_Set_Pixel_Sizes(face, 0, dsc->size);\n    error = FT_Load_Glyph(face, data->glyph_index,  FT_LOAD_RENDER | FT_LOAD_TARGET_NORMAL);",
        "",
        "lock image cache create",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_image.c",
        '        FT_ERROR_MSG("FT_Load_Glyph", error);\n        return false;',
        '        FT_ERROR_MSG("FT_Load_Glyph", error);\n        lv_mutex_unlock(&dsc->cache_node->face_lock);\n        return false;',
        "",
        "unlock image load error",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_image.c",
        '        FT_ERROR_MSG("FT_Render_Glyph", error);\n        return false;',
        '        FT_ERROR_MSG("FT_Render_Glyph", error);\n        lv_mutex_unlock(&dsc->cache_node->face_lock);\n        return false;',
        "",
        "unlock image render error",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_image.c",
        '        FT_ERROR_MSG("FT_Get_Glyph", error);\n        return false;',
        '        FT_ERROR_MSG("FT_Get_Glyph", error);\n        lv_mutex_unlock(&dsc->cache_node->face_lock);\n        return false;',
        "",
        "unlock image glyph error",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_image.c",
        "    FT_Done_Glyph(glyph);\n\n    return true;",
        "    FT_Done_Glyph(glyph);\n\n    lv_mutex_unlock(&dsc->cache_node->face_lock);\n\n    return true;",
        "",
        "unlock image cache create",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_outline.c",
        "    lv_freetype_outline_t outline;\n    outline = outline_create(dsc->context,",
        "    lv_freetype_outline_t outline;\n    lv_mutex_lock(&dsc->cache_node->face_lock);\n    outline = outline_create(dsc->context,",
        "",
        "lock outline cache create",
        log,
    )
    changed += _patch(
        root / "src" / "libs" / "freetype" / "lv_freetype_outline.c",
        "                             dsc->style & LV_FREETYPE_FONT_STYLE_BOLD ? 1 : 0);\n\n    if(!outline) {",
        "                             dsc->style & LV_FREETYPE_FONT_STYLE_BOLD ? 1 : 0);\n    lv_mutex_unlock(&dsc->cache_node->face_lock);\n\n    if(!outline) {",
        "",
        "unlock outline cache create",
        log,
    )
    return changed


def apply(lvgl_dir, log=print) -> int:
    """Patch one LVGL source tree.  Returns the number of changes applied."""
    root = Path(lvgl_dir)
    changed = 0
    changed += _patch(
        root / "src" / "others" / "observer" / "lv_observer.c",
        OBSERVER_OLD,
        OBSERVER_NEW,
        OBSERVER_MARKER,
        "lv_observer_remove dangling LV_EVENT_DELETE hook",
        log,
    )
    changed += _patch(
        root / "src" / "others" / "observer" / "lv_observer.c",
        UNSUBSCRIBE_OLD,
        UNSUBSCRIBE_NEW,
        "maix_lvgl: the object is being deleted",
        "lv_observer delete-hook recursion",
        log,
    )
    changed += _patch(
        root / "src" / "widgets" / "canvas" / "lv_canvas.c",
        CANVAS_OLD,
        CANVAS_NEW,
        "",
        "lv_canvas_copy_buf inverted color-format assertion",
        log,
    )
    changed += _apply_freetype_face_lock(root, log)
    return changed


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_lvgl.py <path-to-lvgl-source-root>")
    print("changes:", apply(sys.argv[1]))
