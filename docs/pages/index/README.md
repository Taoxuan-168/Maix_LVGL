---
title: Maix_LVGL
id: home_page
---

# Maix_LVGL

LVGL 9.1 bindings for MaixPy on MaixCAM / MaixCAM2.

- [API documentation](/api/index.html)
- [GitHub repository](https://github.com/Taoxuan-168/Maix_LVGL)
- [PyPI package](https://pypi.org/project/maix-lvgl/)

## Local preview

Build the generated API documentation first (only needed when `api/` is
missing), from the repository root:

```bash
python3 tools/gen_api_docs.py --pyi binding/lvgl.pyi --out docs/api
```

Then start the site from this `docs/` directory:

```bash
./serve.sh
```

Open <http://127.0.0.1:8000/api/>.
