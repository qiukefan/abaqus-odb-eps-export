# -*- coding: utf-8 -*-

import os
import ast
import math

from abaqus import session
from abaqusConstants import *
from viewerModules import *

__version__ = "1.1.0"

# ==================== 可修改参数 ====================

# 留空：使用当前活动窗口正在显示的 ODB
# 也可以填写完整路径，例如 r"C:\ABAQUS\temp\example.odb"
ODB_PATH = ""

VARIABLE_NAME = "PEMAG"

STEP_INDEX = -1       # 从 0 开始；-1 表示最后一个分析步
FRAME_INDEX = 180      # 从 0 开始；-1 表示该分析步最后一帧

# None 或 "" 表示自动计算；数字表示指定值；上下限可分别设置。
# 例如：CONTOUR_MIN = None / CONTOUR_MAX = ""
# 不要写成 CONTOUR_MIN =（这是无效的 Python 语法）。
CONTOUR_MIN = None
CONTOUR_MAX = None

# 将录制的完整视角命令粘贴在三引号之间。
# 支持连续粘贴多条 view.setValues(...) 命令。
# 命令中的视口名称会被忽略，统一应用到当前活动视口。
# 留空，即 VIEW_COMMAND = r""" """，则保持当前视角。
VIEW_COMMAND = r"""
# session.viewports['Viewport: 1'].view.setValues(nearPlane=104.162, 
    # farPlane=187.48, width=42.1921, height=20.8932, cameraPosition=(-79.6749, 
    # -72.6502, 28.1212), cameraUpVector=(0.0771268, 0.656612, 0.750275), 
    # cameraTarget=(27.8524, 21.5363, -0.585108), viewOffsetX=-8.61496, 
    # viewOffsetY=-1.02414)
# session.viewports['Viewport: 1'].view.setValues(nearPlane=101.19, 
    # farPlane=185.678, width=92.6393, height=38.1713, cameraPosition=(-55.5395, 
    # 122.416, 67.9221), cameraUpVector=(0.245784, 0.678793, -0.691975), 
    # cameraTarget=(25.0405, 25.3817, 1.35738))
"""

# ===================================================


def build_contour_options(minimum, maximum):
    """Build independent automatic/manual contour limit settings."""
    options = {}
    values = {}
    for name, value in (("min", minimum), ("max", maximum)):
        if value is None or (isinstance(value, str) and not value.strip()):
            options[name + "AutoCompute"] = ON
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError("CONTOUR_{} must be a number, None or an empty string.".format(name.upper()))
        if isinstance(value, bool) or not math.isfinite(number):
            raise ValueError("CONTOUR_{} must be a finite number.".format(name.upper()))
        options[name + "AutoCompute"] = OFF
        options[name + "Value"] = number
        values[name] = number
    if "min" in values and "max" in values and values["max"] <= values["min"]:
        raise ValueError("CONTOUR_MAX must be greater than CONTOUR_MIN.")
    return options


def apply_view_commands(viewport, command_text):
    """Read recorded view.setValues commands and apply to this viewport."""
    command_text = command_text.strip()
    if not command_text:
        return

    tree = ast.parse(command_text)
    parameter_sets = []

    for statement in tree.body:
        if not isinstance(statement, ast.Expr):
            raise ValueError(
                "VIEW_COMMAND must contain only view.setValues(...) commands."
            )

        call = statement.value

        if not isinstance(call, ast.Call):
            raise ValueError("Invalid view command.")

        # Expected:
        # session.viewports['Viewport: 1'].view.setValues(...)
        method = call.func
        if not (
            isinstance(method, ast.Attribute)
            and method.attr == "setValues"
            and isinstance(method.value, ast.Attribute)
            and method.value.attr == "view"
        ):
            raise ValueError(
                "Only recorded view.setValues(...) commands are supported."
            )

        viewport_ref = method.value.value
        if not (
            isinstance(viewport_ref, ast.Subscript)
            and isinstance(viewport_ref.value, ast.Attribute)
            and viewport_ref.value.attr == "viewports"
            and isinstance(viewport_ref.value.value, ast.Name)
            and viewport_ref.value.value.id == "session"
        ):
            raise ValueError(
                "Expected session.viewports['...'].view.setValues(...)."
            )

        if call.args:
            raise ValueError(
                "Paste a recorded view command with named camera parameters."
            )

        parameters = {}
        for keyword in call.keywords:
            if keyword.arg is None:
                raise ValueError("Expanded keyword arguments are unsupported.")
            parameters[keyword.arg] = ast.literal_eval(keyword.value)

        parameter_sets.append(parameters)

    # Apply only after all commands have been parsed successfully
    for parameters in parameter_sets:
        viewport.view.setValues(**parameters)


# 获取当前活动视口
vp = session.viewports[session.currentViewportName]

# 获取 ODB
if ODB_PATH.strip():
    odb_path = os.path.abspath(ODB_PATH)

    if not os.path.isfile(odb_path):
        raise IOError("ODB file not found: " + odb_path)

    odb = None
    for opened_odb in session.odbs.values():
        opened_path = os.path.normcase(
            os.path.abspath(opened_odb.path)
        )
        if opened_path == os.path.normcase(odb_path):
            odb = opened_odb
            break

    if odb is None:
        odb = session.openOdb(name=odb_path)

else:
    odb = vp.displayedObject

    if (
        odb is None
        or not hasattr(odb, "steps")
        or not hasattr(odb, "path")
    ):
        raise ValueError(
            "The current viewport is not displaying an ODB."
        )

    odb_path = os.path.abspath(odb.path)

# 检查并生成云图上下限设置；只有两端均为手动值时才比较大小
contour_options = build_contour_options(CONTOUR_MIN, CONTOUR_MAX)

# 获取分析步实际索引
step_names = list(odb.steps.keys())

step_index = STEP_INDEX
if step_index < 0:
    step_index += len(step_names)

if not 0 <= step_index < len(step_names):
    raise ValueError("STEP_INDEX is out of range.")

step_name = step_names[step_index]
step = odb.steps[step_name]

# 获取帧实际索引
frame_index = FRAME_INDEX
if frame_index < 0:
    frame_index += len(step.frames)

if not 0 <= frame_index < len(step.frames):
    raise ValueError("FRAME_INDEX is out of range.")

frame = step.frames[frame_index]

# 检查所选帧是否包含指定变量
if VARIABLE_NAME not in frame.fieldOutputs.keys():
    raise ValueError(
        "Variable '{}' is unavailable in step '{}', frame {}.".format(
            VARIABLE_NAME, step_name, frame_index
        )
    )

# 使用当前活动视口
vp.makeCurrent()

# 同一个 ODB 已经显示时，不重复设置 displayedObject
if vp.displayedObject is not odb:
    vp.setValues(displayedObject=odb)

# 指定分析步和帧
vp.odbDisplay.setFrame(
    step=step_index,
    frame=frame_index
)

# 设置主变量
vp.odbDisplay.setPrimaryVariable(
    variableLabel=VARIABLE_NAME,
    outputPosition=INTEGRATION_POINT
)

# 显示变形云图
vp.odbDisplay.display.setValues(
    plotState=CONTOURS_ON_DEF
)

# 在导出前分别设置自动/手动上下限；自动端不传入数值
vp.odbDisplay.contourOptions.setValues(**contour_options)

# 应用粘贴的视角命令
# 此后不要调用 fitView()，否则会改变录制的缩放和平移
apply_view_commands(vp, VIEW_COMMAND)

# 设置 EPS 导出质量
session.epsOptions.setValues(
    resolution=DPI_1200,
    shadingQuality=EXTRA_FINE
)

# 文件名：PEMAG_frame索引_ODB原文件名.eps
odb_dir = os.path.dirname(odb_path)
odb_basename = os.path.splitext(os.path.basename(odb_path))[0]

eps_basename = "{}_frame{}_{}".format(
    VARIABLE_NAME,
    frame_index,
    odb_basename
)

# 由 Abaqus 自动添加 .eps 扩展名
eps_path = os.path.join(odb_dir, eps_basename)

session.printToFile(
    fileName=eps_path,
    format=EPS,
    canvasObjects=(vp,)
)

print("export_odb_PEMAG_viewset v" + __version__)
print("Exported: " + eps_path + ".eps")
print("Step: {}".format(step_name))
print("Frame index: {}".format(frame_index))
print("Frame value: {}".format(frame.frameValue))
