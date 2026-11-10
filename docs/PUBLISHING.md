# 发布到 PyPI

本文说明如何把 `maix-lvgl` 的预编译 wheel 发布到 TestPyPI 和正式 PyPI。
项目使用交叉编译，**只发布平台 wheel，不发布 sdist**（源码包无法在普通主机上
构建，需要 MaixCDK 和目标工具链）。

包名：`maix-lvgl`（安装后 `import maix_lvgl`）。

---

## 1. 一次性准备

### 1.1 PyPI 账号与 2FA

1. 注册 <https://pypi.org/account/register/>。
2. 在 **Account settings → Two-factor authentication** 中启用 2FA（PyPI 强制要求）。
3. TestPyPI 是独立账号：<https://test.pypi.org/account/register/>，同样启用 2FA。

### 1.2 创建 API token

在 <https://pypi.org/manage/account/token/> 创建 token：

- 首次发布时项目还不存在，只能选 **Entire account**。
- 上传成功后，建议回到该页面创建 **project-scoped** token（仅 `maix-lvgl`），
  然后删除 account-scoped token。
- token 只在创建时显示一次，形如 `pypi-AgEIcHlwaS5vcmc...`。

TestPyPI 的 token 在 <https://test.pypi.org/manage/account/token/> 单独创建。

### 1.3 配置凭据（二选一）

**方式 A：环境变量（推荐，最简单）**

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-...        # 对应目标仓库的 token
```

**方式 B：`~/.pypirc`**

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-...
```

```bash
chmod 600 ~/.pypirc
```

> 不要把真实 token 写进仓库、脚本或聊天记录。

### 1.4 安装 twine

```bash
python3 -m pip install twine
```

---

## 2. 构建 wheel

每个板子必须用对应的 **host Python** 运行 `setup.py`，因为 `bdist_wheel` 会用
当前解释器决定 `cp3xx` tag。切换板卡会清空 `build/`，所以一次构建一个板子。

```bash
export MAIXCDK_PATH=/path/to/MaixCDK

# MaixCAM2：aarch64 / Python 3.13（已实机验证）
python3.13 setup.py bdist_wheel --board maixcam2

# MaixCAM：RISC-V 64 / Python 3.11（未实机验证）
python3.11 setup.py bdist_wheel --board maixcam
```

产物：

```text
dist/maix_lvgl-0.1.0-cp313-cp313-manylinux2014_aarch64.whl
dist/maix_lvgl-0.1.0-cp311-cp311-musllinux_1_2_riscv64.whl
```

> PyPI 不接受裸 `linux_riscv64` 标签（会返回 400 unsupported platform tag）。
> MaixCAM 运行 musl 1.2.2，因此 wheel 使用 `musllinux_1_2_riscv64`；pip 在
> 设备上按 musllinux 标签匹配。

如果 MaixCDK 已经构建过、只想重新打包（例如只改了 README/元数据）：

```bash
python3.13 setup.py bdist_wheel --board maixcam2 --skip-build
```

`--skip-build` 会跳过 MaixCDK 的 `project.py build`，但仍会重新构建
`build_py` 并复制已有的 `liblvgl_binding.so`。它不会跳过 Python 包本身。

> `dist/maix_lvgl_release/` 是 MaixCDK 的主程序输出，**不是**可上传的包；
> `scripts/publish.sh` 只匹配 `maix_lvgl-*.whl`。

---

## 3. 本地检查

```bash
python3 -m twine check dist/maix_lvgl-*.whl
```

预期每个文件输出 `PASSED`。再确认 wheel 内容：

```bash
unzip -l dist/maix_lvgl-0.1.0-cp313-cp313-manylinux2014_aarch64.whl
```

应包含：

```text
maix_lvgl/__init__.py
maix_lvgl/driver.py
maix_lvgl/lvgl.cpython-313-aarch64-linux-gnu.so
maix_lvgl/dl_lib/libdatachannel.so
maix_lvgl-0.1.0.dist-info/{METADATA,WHEEL,LICENSE,RECORD,top_level.txt}
```

确认 `WHEEL` 中 `Root-Is-Purelib: false`，`top_level.txt` 只有 `maix_lvgl`。

---

## 4. 先发 TestPyPI 验证

```bash
scripts/publish.sh testpypi
```

脚本会列出文件、运行 `twine check`、上传到
`https://test.pypi.org/legacy/`。

在设备或普通 Linux 上验证安装：

```bash
python3 -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  maix-lvgl==0.1.0

python3 -c "import maix_lvgl as lv; print(lv.__version__)"
```

> TestPyPI 与正式 PyPI 的版本号互相独立，但 TestPyPI 也**不允许覆盖已上传版本**。

---

## 5. 发布正式 PyPI

确认 TestPyPI 安装无误后：

```bash
scripts/publish.sh pypi
```

脚本会在上传前要求输入 `yes` 确认。CI 或脚本化场景可以：

```bash
PUBLISH_YES=1 TWINE_PASSWORD=pypi-... scripts/publish.sh pypi
```

上传成功后：

- 项目页：<https://pypi.org/project/maix-lvgl/>
- 文件页：<https://pypi.org/project/maix-lvgl/#files>

---

## 6. 设备端安装验证

MaixCAM2（aarch64 / Python 3.13）：

```bash
python3 -m pip install --force-reinstall --no-deps maix-lvgl
python3 -c "import maix_lvgl as lv; print(lv.__version__)"
```

MaixCAM（RISC-V 64 / Python 3.11）：

```bash
python3 -m pip install --force-reinstall --no-deps maix-lvgl
```

`pip` 会按平台标签自动选择对应 wheel：

| 设备 | wheel tag |
| --- | --- |
| MaixCAM2 | `cp313-cp313-manylinux2014_aarch64` |
| MaixCAM | `cp311-cp311-musllinux_1_2_riscv64` |

如果提示 `No matching distribution found`，先在设备上查看 pip 支持的标签：

```bash
python3 -m pip debug --verbose
```

确认 `cp311-musllinux_1_2_riscv64` 或 `cp313-manylinux2014_aarch64` 在列表中。

---

## 7. 版本升级

版本号唯一来源是 `maix_lvgl/__init__.py`：

```python
__version__ = "0.1.1"
```

`setup.py` 会读取它，不要再在 `setup.py` 里硬编码版本。

发布新版本的流程：

1. 修改 `maix_lvgl/__init__.py` 的 `__version__`（建议遵循语义化版本）。
2. 更新 `README.md` / `README_ZH.md` 的变更说明（可选）。
3. 用对应的 host Python 重新构建两个板的 wheel。
4. `scripts/publish.sh testpypi` 验证。
5. `scripts/publish.sh pypi` 正式发布。

**PyPI 不允许覆盖已存在的版本**。如果 0.1.0 已上传，任何内容修正都必须
升到 0.1.1；不能重新上传 0.1.0（`File already exists`）。

---

## 8. 常见问题

| 现象 | 原因 / 处理 |
| --- | --- |
| `File already exists` | 该版本已上传；升版本号后重试 |
| `403 Forbidden` | token 错误、无权限，或账号未启用 2FA |
| `InvalidDistribution` | wheel 文件名/元数据不合法；先运行 `twine check` |
| `No matching distribution found` | 设备 Python/平台与 wheel tag 不匹配；用 `pip debug --verbose` 对比 |
| 上传了错误的板子 | 删除该版本不可行；发布新版本并在 Release 说明中注明 |
| `--skip-build` 后 wheel 缺 `maix_lvgl/*.py` | 已修复：脚本会先执行 `build_py`；请使用当前 `setup.py` |

---

## 9. 为什么不发布 sdist

`maix-lvgl` 的扩展由 MaixCDK 用交叉工具链编译，依赖：

- MaixCDK 及其 `dl/extracted` 下的目标 Python 头文件/库，
- 目标板的 LVGL/freetype 构建，
- 对应 host Python（3.13 或 3.11）。

普通 `pip install` 环境无法满足这些条件，构建 sdist 只会让用户遇到无法解决的
编译错误。因此只发布两个平台 wheel；`setup.py` 的 `bdist_wheel` 也不会生成
sdist（请勿运行 `sdist` 后上传）。
