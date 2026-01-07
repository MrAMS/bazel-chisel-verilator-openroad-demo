# 设计空间探索 (DSE) 框架

这是一个通用的、与设计解耦的 DSE 框架，用于使用 Optuna 优化硬件设计。

## 架构

```
eda/dse/
├── dse_config.py          # 配置接口和常量
├── bazel_builder.py       # 统一的构建器（单个/并行）
├── optimization.py        # Optuna 目标函数
├── dse_runner.py          # DSE 主流程编排
├── visualization.py       # 结果可视化
└── <DesignName>/          # 设计特定配置
    ├── <design>_dse_config.py
    └── run_<design>_dse.py
```

## 核心特性

### 1. 设计解耦

框架完全与具体设计解耦，通过 `DSEConfig` 接口定义设计特定的逻辑：

```python
@dataclass
class DSEConfig:
    # 设计标识
    design_name: str
    target: str  # 单个设计构建的目标（如 //eda/MyDesign:MyDesign_ppa）

    # 参数空间
    suggest_params: Callable
    get_env_vars: Callable
    get_bazel_opts: Callable

    # 指标计算
    calc_performance: Callable
    calc_area: Callable
    get_slack: Callable
    calc_constraint_violation: Callable

    # 可视化标签
    performance_label: str
    area_label: str
    param_labels: Dict[str, str]

    # 可选：并行构建支持
    get_parallel_bazel_opts: Callable | None = None
    parallel_target_package: str | None = None  # DSE 基础设施的包位置
```

### 2. 统一的批处理架构

框架采用**统一的批处理架构**，其中 N=1 是并行的特例：

- **所有执行**都通过 `build_designs()` 函数（接受参数列表）
- **batch_size=1**: 构建单个设计（串行）
- **batch_size=N**: 在单个 Bazel 调用中并行构建 N 个变体

### 3. 进度跟踪

DSE 运行时提供实时进度跟踪：

- **进度条**: 使用 tqdm 显示当前进度和剩余试验数
- **时间统计**: 显示已用时间和预估剩余时间
- **批次信息**: 显示当前批次编号和已完成的试验数

```
DSE Progress: 45%|████████████▌             | 45/100 [12:34<15:23, 16.8s/trial] elapsed: 754.2s, batch: 6
```

运行结束后会显示总优化时间统计。

### 4. BUILD 文件分离

DSE 基础设施与基础设计完全分离：

```
eda/MyDesign/BUILD         # 基础设计流程（单个设计，无并行）
    └── orfs_flow(name = "MyDesign")
    └── orfs_run(name = "MyDesign_ppa")

eda/dse/MyDesign/BUILD     # DSE 基础设施（并行变体，Python 目标）
    ├── py_library(name = "my_design_dse_config")
    ├── py_binary(name = "run_my_design_dse")
    ├── string_flag(name = "param_0" ... "param_N")
    ├── orfs_flow(name = "MyDesign_0" ... "MyDesign_N")
    └── orfs_run(name = "MyDesign_0_ppa" ... "MyDesign_N_ppa")
```

优势：
- 基础设计保持简洁（仅核心流程）
- DSE 特定逻辑集中在 `eda/dse/MyDesign/`
- 更好的关注点分离
- 更容易维护和理解

## 使用方法

### 创建新设计的 DSE

#### 步骤 1: 创建 DSE 目录

```bash
mkdir -p eda/dse/MyDesign
```

#### 步骤 2: 创建 BUILD 文件

`eda/dse/MyDesign/BUILD`:

```starlark
load("@bazel-orfs//:openroad.bzl", "orfs_flow", "orfs_run")
load("@bazel-orfs//:verilog.bzl", "verilog_single_file_library")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@pip//:requirements.bzl", "requirement")

# DSE Python 目标
py_library(
    name = "my_design_dse_config",
    srcs = ["my_design_dse_config.py"],
    visibility = ["//visibility:public"],
    deps = [requirement("optuna")],
)

py_binary(
    name = "run_my_design_dse",
    srcs = ["run_my_design_dse.py"],
    main = "run_my_design_dse.py",
    deps = [
        ":my_design_dse_config",
        "//eda/dse:dse_config",
        "//eda/dse:dse_runner",
    ],
)

# 并行 DSE 构建基础设施
N_PARALLEL = 8

# 为每个变体创建 string_flag
[string_flag(
    name = "param_{}_{}".format(param_name, i),
    build_setting_default = "default_value",
) for param_name in ["param1", "param2"]
   for i in range(N_PARALLEL)]

# 为每个变体创建 orfs_flow
[orfs_flow(
    name = "MyDesign_{}".format(i),
    settings = {
        "PARAM1": ":param1_{}".format(i),
    },
    variant = "{}".format(i),
    # ... 其他配置
    tags = ["manual"],
) for i in range(N_PARALLEL)]

# 为每个变体创建 PPA 提取
[orfs_run(
    name = "MyDesign_{}_ppa".format(i),
    src = "MyDesign_{}_{}_cts".format(i, i),
    outs = ["MyDesign_{}_ppa.txt".format(i)],
    script = "//eda/MyDesign:results.tcl",
    tags = ["manual"],
) for i in range(N_PARALLEL)]
```

#### 步骤 3: 实现 DSE 配置

`my_design_dse_config.py`:

```python
def suggest_params(trial):
    return {"param1": trial.suggest_int("param1", 1, 10)}

def get_bazel_opts(params):
    return [f"--define=PARAM1={params['param1']}"]

def get_parallel_bazel_opts(params, variant_index, package):
    """将参数转换为每个变体的 Bazel 选项"""
    # 总是使用 DSE 包位置的 string_flag
    dse_package = "//eda/dse/MyDesign"
    return [f"--{dse_package}:param1_{variant_index}={params['param1']}"]

def calc_performance(ppa_metrics, params):
    return ppa_metrics.get("throughput", 0.0)

# ... 其他必需函数
```

#### 步骤 4: 创建运行脚本

`run_my_design_dse.py`:

```python
from eda.dse import run_dse, DSEConfig
from . import my_design_dse_config as config

dse_config = DSEConfig(
    design_name="MyDesign",
    target="//eda/MyDesign:MyDesign_ppa",  # 单个设计的目标
    parallel_target_package="//eda/dse/MyDesign",  # DSE 并行变体的包
    suggest_params=config.suggest_params,
    get_bazel_opts=config.get_bazel_opts,
    get_parallel_bazel_opts=config.get_parallel_bazel_opts,
    # ... 其他配置
)

study = run_dse(
    config=dse_config,
    n_trials=50,
    parallel_trials=8,
    output_dir="results/my_design"
)
```

关键点：
- `target`: 指向基础设计的 PPA 目标（用于单个构建）
- `parallel_target_package`: 指向 DSE 包（用于并行构建）
- 如果不指定 `parallel_target_package`，将从 `target` 提取包（向后兼容）

### 并行构建要求

要支持并行构建，设计需要：

1. **实现 `get_parallel_bazel_opts()`**: 将全局选项转换为每个变体的选项
2. **BUILD 文件中定义 string_flag**: 为每个并行变体创建 flag
3. **使用 settings 参数**: 在 `orfs_flow()` 中使用 settings 从 flag 读取值

参考 `eda/SimdDotProduct/BUILD` 和 `eda/dse/SimdDotProduct/simd_dse_config.py` 的实现。

## 与 Optuna 的解耦

构建逻辑与 Optuna 完全解耦：

```python
# 不依赖 Optuna 的构建
from eda.dse.bazel_builder import build_designs

params_list = [
    {"n_lanes": 4, "clock_ps": 1000},
    {"n_lanes": 8, "clock_ps": 800},
]

results = build_designs(config, params_list, workspace_root)
# results 是普通字典，不是 Optuna Trial 对象
```

## 约束处理

框架使用统一的约束违反度量：

```python
def calc_constraint_violation(ppa_metrics) -> float:
    """
    返回:
        - 负值: 约束满足（更负 = 更多裕量）
        - 零: 约束刚好满足
        - 正值: 约束违反（更正 = 更严重）
    """
    # 检查硬约束（面积、功耗等）
    if area > MAX_AREA:
        return SEVERE_VIOLATION

    # 返回 -slack 提供梯度信息
    return -slack
```

这为 Optuna 的采样器提供了梯度信息，实现更好的探索和收敛。

## 示例：SimdDotProduct

参见 `eda/dse/SimdDotProduct/` 获取完整示例，展示了：
- 多参数探索（n_lanes, abc_clock_ps）
- 并行构建支持
- 性能指标计算（GOPS）
- 约束检查（时序、面积、功耗）

## 依赖

- Python 3.13+
- Optuna (多目标优化)
- Matplotlib (结果可视化)
- tqdm (进度条显示)
- Bazel + OpenROAD Flow Scripts

## 参考

- Optuna 文档: https://optuna.readthedocs.io/
- Bazel 文档: https://bazel.build/
- OpenROAD Flow Scripts: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts
