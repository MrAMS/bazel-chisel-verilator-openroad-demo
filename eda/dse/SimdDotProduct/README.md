# SimdDotProduct 设计空间探索

SimdDotProduct 的 DSE 探索架构参数（n_lanes）和物理约束（时钟周期）的设计空间，以找到面积和性能的 Pareto 最优解。

## 设计参数

### 架构参数

- **n_lanes** (4-32): SIMD 通道数
  - 决定"道路有多宽"
  - 更多通道 = 更高吞吐量，但逻辑深度增加

### 物理约束

- **abc_clock_ps** (350-5000 ps): ABC 综合时钟周期
  - 决定"加速器踩多狠"
  - 更紧的约束 → 更大的门 → 更多面积
  - 更松的约束 → 更小的门 → 更少面积

### 固定参数

- **input_width**: 8 位
- **output_width**: 32 位（累加器宽度）

## 性能指标

### GOPS (Giga Operations Per Second)

```
GOPS = 2 × n_lanes × F_effective

其中:
- 2: 每个点积通道执行 1 次乘法 + 1 次加法 = 2 次操作
- n_lanes: 并行通道数
- F_effective: 有效频率（考虑 WNS）
```

### 有效频率计算

```python
if WNS >= 0:
    F_effective = F_target
else:
    F_effective = 1 / (T_target + |WNS|)
```

这考虑了"逻辑深度墙"效应：
- 随着 n_lanes 增加，组合逻辑深度增加
- WNS 变为负值，F_effective 下降
- GOPS 增长受限

## 预期行为

1. **线性扩展区域** (n_lanes = 4-16):
   - 面积 ∝ GOPS
   - 时序容易满足
   - 最佳性价比

2. **拐点** (n_lanes = 16-32):
   - 性能/面积比最优
   - 时序开始紧张

3. **饱和区域** (n_lanes > 32):
   - 逻辑深度墙
   - F_effective 下降
   - GOPS 增长停滞，面积继续增加

## 使用方法

### 快速测试

```bash
bazel run //eda/dse/SimdDotProduct:run_simd_dse -- --n-trials 2
```

### 完整 DSE

```bash
bazel run //eda/dse/SimdDotProduct:run_simd_dse -- \
    --n-trials 100 \
    --parallel-trials 8 \
    --seed 42 \
    --output-dir results/simd_dse
```

### 持久化研究

```bash
bazel run //eda/dse/SimdDotProduct:run_simd_dse -- \
    --n-trials 100 \
    --parallel-trials 8 \
    --storage "sqlite:///results/simd_dse.db" \
    --study-name "simd_v1"
```

## 并行构建实现

### BUILD 文件配置

```starlark
# 定义并行变体数量
N_PARALLEL = 8

# 为每个变体创建 string_flag
[string_flag(
    name = "chisel_opts_{}".format(i),
    build_setting_default = "",
) for i in range(N_PARALLEL)]

[string_flag(
    name = "abc_clock_ps_{}".format(i),
    build_setting_default = "1000",
) for i in range(N_PARALLEL)]

# Cache invalidation: batch_id 用于强制 Bazel 在批次间失效缓存
[string_flag(
    name = "batch_id_{}".format(i),
    build_setting_default = "0",
) for i in range(N_PARALLEL)]

# 创建并行 orfs_flow 变体
[orfs_flow(
    name = "SimdDotProduct_{}".format(i),
    settings = {
        "ABC_CLOCK_PERIOD_IN_PS": ":abc_clock_ps_{}".format(i),
    },
    variant = "{}".format(i),
    ...
) for i in range(N_PARALLEL)]
```

### Bazel 缓存失效机制

DSE 在并行构建时使用 **batch_id** 作为 string_flag 来强制 Bazel 在不同批次间失效缓存：

**问题**：Bazel 的 action cache 只跟踪 string_flag 的**标签**（如 `:chisel_opts_0`），而不跟踪其**值**。当 DSE 运行多个批次时，每批都重用相同的变体索引（0-3），导致 Bazel 错误地复用缓存的构建结果。

**解决方案**：
1. 添加 `batch_id` string_flag（每个变体一个）
2. 在 Chisel Verilog 生成规则中读取 batch_id 值
3. 每个批次使用不同的 batch_id（0, 1, 2, ...）
4. Bazel 检测到 batch_id 改变，强制重新生成 Verilog

```python
# rules/generate.bzl
def _chisel_verilog_impl(ctx):
    # 读取 batch_id 使其成为 action 输入
    if hasattr(ctx.attr, "batch_id") and ctx.attr.batch_id:
        batch_id_attr = ctx.attr.batch_id
        _ = batch_id_attr[BuildSettingInfo].value
    ...
```

### DSE 配置

```python
def get_parallel_bazel_opts(params, variant_index, package, batch_id=0):
    """将参数转换为每个变体的 Bazel 选项"""
    chisel_opts = f"--nLanes={params['n_lanes']} ..."

    return [
        f"--{package}:chisel_opts_{variant_index}={chisel_opts}",
        f"--{package}:abc_clock_ps_{variant_index}={params['abc_clock_ps']}",
        f"--{package}:batch_id_{variant_index}={batch_id}",  # Cache invalidation
    ]
```

## 约束检查

DSE 检查以下约束：

1. **面积约束**: < 100 mm² (硬约束)
2. **频率约束**: > 1 MHz (硬约束)
3. **功耗约束**: < 1W (硬约束)
4. **时序约束**: slack >= 0 (软约束，提供梯度)

```python
def calc_constraint_violation(ppa_metrics):
    # 检查硬约束
    if area >= 1e8:  # 100 mm²
        return SEVERE_VIOLATION
    if effective_freq <= 0.001:  # 1 MHz
        return SEVERE_VIOLATION
    if power >= 1e9:  # 1W
        return SEVERE_VIOLATION

    # 返回 -slack 提供梯度信息
    return -slack
```

## 结果分析

DSE 生成以下输出：

1. **PDF 图表** (`SimdDotProduct_dse_results.pdf`):
   - Pareto 前沿（面积 vs GOPS）
   - 参数扫描图
   - 约束违反分布

2. **HTML 仪表板** (`SimdDotProduct_pareto.html`):
   - 交互式 Pareto 前沿
   - 参数重要性分析
   - 优化历史

3. **文本报告** (`SimdDotProduct_results.txt`):
   - Pareto 最优解列表
   - 所有可行解
   - 参数统计

## 示例结果

经过 cache invalidation 修复后，DSE 现在能够正确探索设计空间：

```
✓ Found 6 Pareto optimal solutions (from 10 trials)

Best area solution:
  n_lanes = 8
  abc_clock_ps = 1050 ps
  Area = 335.267 um²
  GOPS = 15.238

Best performance solution:
  n_lanes = 32
  abc_clock_ps = 980 ps
  Area = 1229.079 um²
  GOPS = 65.306

所有 Pareto 最优解：
  Trial 0: n_lanes=8, abc_clock_ps=752, Area=335.704, Perf=21.277
  Trial 1: n_lanes=12, abc_clock_ps=682, Area=491.142, Perf=35.191
  Trial 3: n_lanes=32, abc_clock_ps=980, Area=1229.079, Perf=65.306
  Trial 5: n_lanes=24, abc_clock_ps=1094, Area=960.968, Perf=43.876
  Trial 6: n_lanes=8, abc_clock_ps=1005, Area=335.690, Perf=15.920
  Trial 8: n_lanes=8, abc_clock_ps=1050, Area=335.267, Perf=15.238
```

**验证**：
- ✓ 所有 trial 数据唯一（无重复）
- ✓ 相同 n_lanes 在不同时钟周期下产生不同面积（符合预期）
- ✓ 4 个 trial 因时序违例失败（slack < 0）
- ✓ Batch ID 正确触发 Bazel cache invalidation

## 性能

- **串行模式**: ~5 分钟/trial
- **并行模式 (N=8)**: ~5 分钟/batch (8 trials)
- **加速比**: ~8x

## 已知问题与修复

### ✅ 已修复：Bazel Cache Invalidation Bug

**问题描述**：
在并行构建模式下（`--parallel-trials 4`），DSE 会将 trials 分批处理。每批使用相同的变体索引（0-3），但由于 Bazel 只跟踪 string_flag 的标签而非值，导致不同批次的相同索引变体错误地复用了缓存结果。

**症状**：
```
# 错误的结果 - Trial 0 和 Trial 4 完全相同
Trial 0: n_lanes=8, abc_clock_ps=752, Area=335.748, Perf=21.312
Trial 4: n_lanes=8, abc_clock_ps=752, Area=335.748, Perf=21.312  # 重复！
```

**根本原因**：
Bazel 的 action cache 机制：
- ✓ 跟踪：string_flag 标签（`:chisel_opts_0`）
- ✗ 不跟踪：string_flag 的值（`"--nLanes=8 ..."`）

当 batch 1 使用 `--:chisel_opts_0="--nLanes=8"` 时，Bazel 看到标签 `:chisel_opts_0` 与 batch 0 相同，直接复用了缓存的 Verilog。

**解决方案**：
1. 添加 `batch_id` string_flag 到 BUILD 文件
2. 在 Chisel Verilog 生成规则中读取 `batch_id` 值
3. DSE 为每个批次传递不同的 `batch_id`（0, 1, 2, ...）
4. Bazel 检测到 `batch_id` 改变，强制重新生成

**修复代码**：
- `eda/dse/SimdDotProduct/BUILD`: 添加 `batch_id` string_flags
- `rules/generate.bzl`: 读取 `batch_id` 作为 action 输入
- `eda/dse/SimdDotProduct/simd_dse_config.py`: `get_parallel_bazel_opts()` 传递 `batch_id`
- `eda/dse/bazel_builder.py`: 传递 `batch_id` 给每个批次

**验证**：所有 trials 现在产生唯一结果，无重复数据。

### ✅ 已优化：简化 PPA 文件路径逻辑

**改进前**：
```python
# 特殊处理 n_designs > 1
if n_designs > 1 and config.parallel_target_package:
    package_path = config.parallel_target_package.lstrip("//")
    ppa_file = os.path.join(workspace_root, f"bazel-bin/{package_path}/{design_name}_{i}_ppa.txt")
else:
    ppa_file = _get_ppa_file_path(workspace_root, design_name, None if n_designs == 1 else i)
```

**改进后**：
```python
# 统一路径构建逻辑
package_path = config.parallel_target_package.lstrip("//")
variant_suffix = f"_{i}" if n_designs > 1 else ""
ppa_file = os.path.join(workspace_root, f"bazel-bin/{package_path}/{design_name}{variant_suffix}_ppa.txt")
```

**改进点**：
- 移除了 `n_designs > 1` 的条件判断
- 删除了未使用的 `_get_ppa_file_path()` 函数
- 代码从 16 行简化为 7 行
- 逻辑更清晰，更易维护

## 参考

- Chisel 源码: `hdl/chisel/src/SimdDotProduct/SimdDotProduct.scala`
- BUILD 文件: `eda/SimdDotProduct/BUILD`
- PPA 提取: `eda/SimdDotProduct/results.tcl`
- DSE 配置: `eda/dse/SimdDotProduct/simd_dse_config.py`
- DSE 框架: `eda/dse/README.md`
