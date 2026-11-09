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
    return changed


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_lvgl.py <path-to-lvgl-source-root>")
    print("changes:", apply(sys.argv[1]))
