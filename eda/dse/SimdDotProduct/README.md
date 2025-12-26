# SimdDotProduct Design Space Exploration (DSE)

基于Optuna的SIMD点积引擎设计空间探索，用于验证"逻辑深度墙"假设。

## 项目概述

本项目探索SimdDotProduct设计的参数空间，寻找**Area**和**GOPS**之间的帕累托最优解。

### 优化目标

- **最大化**: GOPS (Giga Operations Per Second)
  - `GOPS = 2 × n_lanes × F_real`
  - F_real = 基于WNS的有效频率 (GHz)

- **最小化**: Cell Area (μm²)

## 目录结构

```
eda/
├── SimdDotProduct/              # EDA流程配置
│   ├── BUILD                    # OpenROAD综合流程
│   ├── constraints.sdc          # 参数化时钟约束
│   └── results.tcl              # PPA指标提取
│
└── dse/                         # DSE框架（通用+专用）
    ├── dse_config.py            # 配置接口定义
    ├── bazel_builder.py         # Bazel构建和PPA解析
    ├── optimization.py          # Optuna优化逻辑
    ├── visualization.py         # 可视化生成
    ├── dse_runner.py            # 主运行接口
    │
    └── SimdDotProduct/          # SimdDotProduct专用
        ├── simd_dse_config.py   # 参数空间和GOPS计算
        └── run_simd_dse.py      # 主执行脚本
```

## DSE参数空间

| 参数 | 范围 | 说明 |
|------|------|------|
| `n_lanes` | [4, 8, 12, 16, 20, 24, 28, 32] | SIMD并行度 |
| `abc_clock_ps` | 350 ~ 1250 ps | ABC时钟周期 (800MHz ~ 2.86GHz) |
| `input_width` | 8 (固定) | 输入位宽 |
| `output_width` | 32 (固定) | 输出位宽 |

## 快速开始

### 1. 快速测试 (5 trials)

```bash
bazel run //eda/dse/SimdDotProduct:run_simd_dse -- --quick-test
```

### 2. 标准运行 (20 trials)

```bash
bazel run //eda/dse/SimdDotProduct:run_simd_dse -- --n-trials=20
```

### 3. 大规模探索 (带持久化)

```bash
bazel run //eda/dse/SimdDotProduct:run_simd_dse -- \
    --n-trials=100 \
    --storage=sqlite:///simd_dse.db \
    --study-name=simd_full_exp \
    --output-dir=results/simd_full
```

### 4. 断点续传

```bash
# 使用相同的storage和study-name即可自动续传
bazel run //eda/dse/SimdDotProduct:run_simd_dse -- \
    --n-trials=50 \
    --storage=sqlite:///simd_dse.db \
    --study-name=simd_full_exp
```

## 输出结果

DSE完成后会在输出目录生成：

### PDF报告 (`SimdDotProduct_dse_results.pdf`)

1. **Area vs GOPS帕累托前沿** - 主图，标注最优解
2. **n_lanes参数扫描** - n_lanes vs Area/GOPS
3. **abc_clock_ps参数扫描** - clock vs Area/GOPS
4. **优化历史曲线** - 收敛性分析

### HTML交互式Dashboard

- `SimdDotProduct_pareto.html` - 帕累托前沿（可交互）

### 文本报告 (`SimdDotProduct_results.txt`)

- 帕累托最优解列表
- 所有可行解的参数组合

## 关键技术特性

### 有效频率计算

```python
if WNS < 0:
    F_real = 1 / (T_target + |WNS|)  # 惩罚时序违例
else:
    F_real = 1 / T_target
```

### 统一约束优化

```python
# 使用constraint_violation连续值提供梯度信息
constraint_violation = calc_constraint_violation(ppa_metrics)
# constraint_violation <= 0: 约束满足
# constraint_violation > 0: 约束违反
```

## 扩展到其他设计

DSE框架是通用的，添加新设计只需：

1. 在`eda/<DesignName>/`创建EDA流程文件
2. 在`eda/dse/<DesignName>/`创建专用配置：
   - 实现`suggest_params()` - 定义参数空间
   - 实现`get_env_vars()` - 环境变量映射
   - 实现`get_bazel_opts()` - Bazel选项生成
   - 实现`calc_area()` - 面积提取
   - 实现`calc_performance()` - 性能计算
   - 实现`get_slack()` - 时序余量提取
   - 实现`calc_constraint_violation()` - 统一约束检查
3. 创建主执行脚本调用`run_dse()`

参考`eda/dse/SimdDotProduct/`的实现。

## 命令行选项

```bash
bazel run //eda/dse/SimdDotProduct:run_simd_dse -- --help
```

主要选项：
- `--n-trials N`: Trial数量 (默认: 20)
- `--seed N`: 随机种子 (默认: 42)
- `--output-dir DIR`: 输出目录
- `--storage URL`: Optuna存储URL (用于持久化)
- `--study-name NAME`: Study名称 (用于续传)
- `--quick-test`: 快速测试模式 (5 trials)
