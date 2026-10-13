# Abaqus ODB EPS Export

脚本：`export_eps_odb_PEMAG_viewset_v1.4.0.py`  
当前版本：**1.4.0**  
更新日期：2026-10-13

## 使用方法

在 Abaqus/Viewer 或 Abaqus/CAE 中打开 ODB，激活目标视口，通过 **File → Run Script** 运行脚本。脚本依赖 Abaqus 会话，不能使用普通 Python 完成图片导出。面向 Abaqus 2024。

## 云图上下限

两端均自动计算（对应 Limits 面板中的 Min/Max → Auto-compute）：

```python
CONTOUR_MIN = None
CONTOUR_MAX = None
```

也可使用空字符串，或仅包含空格的字符串：

```python
CONTOUR_MIN = ""
CONTOUR_MAX = ""
```

两端固定：

```python
CONTOUR_MIN = 0.0
CONTOUR_MAX = 0.022
```

固定最小值、最大值自动计算：

```python
CONTOUR_MIN = 0.0
CONTOUR_MAX = None
```

最小值自动计算、固定最大值：

```python
CONTOUR_MIN = None
CONTOUR_MAX = 0.022
```

注意：

- Python 不允许等号右侧完全为空，例如 `CONTOUR_MIN =`。请使用 `None` 或 `""`。
- `0.0` 是有效的固定值，不代表自动。
- 两端均为固定值时，最大值必须大于最小值；不接受非有限数值。
- 自动端设置 `minAutoCompute=ON` 或 `maxAutoCompute=ON`，不传入对应的固定数值；手动端设置为 `OFF` 并传入数值。
- 上下限设置在导出之前生效。动画自动范围（例如截图中的 Use limits from all frames）沿用当前会话设置，本次功能仅控制 Min/Max 的自动开关。
- 当前脚本保留用户配置：上下限均为 `None`，`FRAME_INDEX = 180`。

## 其他参数

| 参数 | 含义 |
| --- | --- |
| `ODB_PATH = ""` | 使用当前活动视口正在显示的 ODB；填写路径则打开或复用指定 ODB |
| `VARIABLE_NAME = "PEMAG"` | 默认显示 PEMAG 积分点标量场；张量或矢量变量可能需要额外指定分量或不变量 |
| `STEP_INDEX = -1` | 最后一个分析步；索引从 0 开始 |
| `FRAME_INDEX = -1` | 所选分析步的最后一帧；索引从 0 开始 |
| `VIEW_COMMAND` | 粘贴录制的 `session.viewports['...'].view.setValues(...)` 命令；空白时保持当前视角 |

视角命令粘贴到 `r""" ... """` 之间，支持多条带数值参数的录制命令，统一应用到当前活动视口。请从 `.rpy` 文件复制完整 Python 命令，不要包含 Markdown 或 HTML 转义字符。数值相机参数命令应用后不调用 `fitView()`；标准视角命令应用后自动调用 `fitView()`，适应当前 ODB 的可见模型。

## 标准视角（1.2.0）

直接将下面任意一条粘贴到 `VIEW_COMMAND` 的三引号内：

```python
session.viewports['Viewport: 1'].view.setValues(session.views['Front'])
session.viewports['Viewport: 1'].view.setValues(session.views['Back'])
session.viewports['Viewport: 1'].view.setValues(session.views['Top'])
session.viewports['Viewport: 1'].view.setValues(session.views['Bottom'])
session.viewports['Viewport: 1'].view.setValues(session.views['Left'])
session.viewports['Viewport: 1'].view.setValues(session.views['Right'])
session.viewports['Viewport: 1'].view.setValues(session.views['Iso'])
```

标准视角确定观察方向，随后自动居中和缩放到当前显示的模型，因此不需要给不同 ODB 填写相机位置。方向以 Abaqus 标准坐标方向为准，不会识别不同模型自身的“正面”；显示组隐藏的部分不会自动恢复。

多条命令按顺序执行，只在最后导出一张图片；上述七条全部粘贴时最终导出 Iso。可以先使用标准视角，再追加数值参数命令作微调，后续数值参数不会触发自动缩放。留空或仅有注释则不调整视角。应使用原始 Python 命令中的 `.view.setValues`，不要加入 `\.` 转义。

## 相机参数导出（1.3.0）

兼容 **ExportCurrentView v0.2.2**，代码通过 `EXPORT_CURRENT_VIEW_COMPAT_VERSION = "v0.2.2"` 显式声明。已内置该版本的采集和 JSON 写入函数，无需外部脚本路径，也不弹出保存对话框。

```python
EXPORT_CAMERA = True   # 开启
# EXPORT_CAMERA = False  # 关闭（默认）
```

开启时，在 EPS 所在目录输出 `PEMAG_frame180_原ODB文件名_camera.json`。JSON 与 EPS 使用同一个视口、帧和最终视角；采集在标准视角自动适应及数值相机命令执行之后。

JSON 根字段与 ExportCurrentView v0.2.2 一致：`cameraPosition`、`cameraTarget`、`cameraUpVector`、`width`、`height`、`viewOffsetX`、`viewOffsetY`、`nearPlane`、`farPlane`、`projection`、`deformation`。变形记录包含 `mode`、三轴 `factors` 和 `source`，支持 AUTO、UNIFORM、NONUNIFORM。重建仍以当前 EPS 中的变形比例标签为准，JSON 变形信息是诊断记录。

JSON 不允许 NaN/Infinity，也不会覆盖已有文件。若目标 JSON 已存在，脚本在导出 EPS 之前报错；请重命名/移走原 JSON，或关闭相机导出。若 EPS 成功但 JSON 写入失败，脚本会明确报告部分成功，失败写入创建的不完整 JSON 会被清理。关闭时不采集相机信息，也不检查或写入 JSON。

## 标量、分量和不变量（1.4.0）

一次运行导出一种结果。文件名保留历史 PEMAG 字样，但脚本已支持其他可显示的场变量。

| 结果 | VARIABLE_NAME | REFINEMENT_TYPE | REFINEMENT_LABEL | OUTPUT_POSITION |
| --- | --- | --- | --- | --- |
| 塑性应变大小 | PEMAG | 空字符串 | 空字符串 | INTEGRATION_POINT |
| 等效塑性应变 | PEEQ | 空字符串 | 空字符串 | INTEGRATION_POINT |
| 塑性应变分量 | PE | COMPONENT | PE11（或 PE22、PE33、PE12、PE13、PE23） | INTEGRATION_POINT |
| 最大主塑性应变 | PE | INVARIANT | Max. Principal | INTEGRATION_POINT |
| 绝对值最大主塑性应变 | PE | INVARIANT | Max. Principal (Abs) | INTEGRATION_POINT |
| 中间主塑性应变 | PE | INVARIANT | Mid. Principal | INTEGRATION_POINT |
| 最小主塑性应变 | PE | INVARIANT | Min. Principal | INTEGRATION_POINT |
| Mises 应力 | S | INVARIANT | Mises | INTEGRATION_POINT |
| 位移分量 | U | COMPONENT | U1 | NODAL |
| 位移大小 | U | INVARIANT | Magnitude | NODAL |

例如导出图中的最大主塑性应变：

```python
VARIABLE_NAME = "PE"
REFINEMENT_TYPE = "INVARIANT"
REFINEMENT_LABEL = "Max. Principal"
OUTPUT_POSITION = INTEGRATION_POINT
```

导出 PE11 时把类型改为 `"COMPONENT"`、名称改为 `"PE11"`。名称区分大小写，请使用 Abaqus 下拉菜单中的完整名称。具体分量/不变量能否使用取决于当前 ODB 的所选帧和场类型，二维模型可能没有所有三维分量。脚本检查分量名称；不变量及输出位置由 Abaqus 接口检查，不支持时停止导出。壳截面点、平均和坐标变换仍沿用当前视口设置。

文件名包含所选子数据，例如 `PE_PE11_frame180_原ODB文件名.eps`、`PE_Max_Principal_frame180_原ODB文件名.eps`，可选 JSON 使用同样前缀。标量 PEMAG 的原命名方式不变。默认仍保留 PEMAG 配置。

接口依据：[Abaqus OdbDisplay setPrimaryVariable 文档](https://ceae-server.colorado.edu/v2016/books/ker/pt01ch35pyo01.html)。

## 输出

EPS 保存在 ODB 所在文件夹，命名为：

```text
PEMAG_frame100_原ODB文件名.eps
```

`frame100` 指实际帧索引，不是时间值 `frameValue`。导出设置为 `DPI_1200`、`EXTRA_FINE`。文件名不包含分析步名或视角名；重复导出至相同路径可能覆盖原图。

## 验证范围

1.1.0 已进行 Python 语法检查和独立参数逻辑检查，覆盖四种上下限组合、空字符串、零值和非法输入。尚未在 Abaqus 图形会话中执行 EPS 导出验证。

1.2.0 已通过语法检查和模拟视口检查：七种标准视角、混合命令顺序、空白/注释、非法命令提前拒绝。尚未在 Abaqus 图形会话中验证不同 ODB 的实际构图。

1.3.0 验证：Python 语法和模拟会话测试（开关、相机格式、三种变形模式、重名保护）；尚未在 Abaqus 中实际运行本版导出。

1.4.0 已通过语法及模拟参数测试；尚未在 Abaqus 中实际验证本版的子数据导出。

## 历史版本

- [export_eps_odb_PEMAG_viewset_v1.1.0.py](export_eps_odb_PEMAG_viewset_v1.1.0.py)
- [export_eps_odb_PEMAG_viewset_v1.2.0.py](export_eps_odb_PEMAG_viewset_v1.2.0.py)
- [export_eps_odb_PEMAG_viewset_v1.3.0.py](export_eps_odb_PEMAG_viewset_v1.3.0.py)
- [export_eps_odb_PEMAG_viewset_v1.4.0.py](export_eps_odb_PEMAG_viewset_v1.4.0.py)

版本变更见 [CHANGELOG.md](CHANGELOG.md)。最新版本为 v1.4.0。
