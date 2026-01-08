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

## 参考

- Chisel 源码: `hdl/chisel/src/SimdDotProduct/SimdDotProduct.scala`
- BUILD 文件: `eda/SimdDotProduct/BUILD`
- PPA 提取: `eda/SimdDotProduct/results.tcl`
- DSE 配置: `eda/dse/SimdDotProduct/simd_dse_config.py`
- DSE 框架: `eda/dse/README.md`
