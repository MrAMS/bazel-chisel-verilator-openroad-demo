# SimdDotProduct Design Space Exploration (DSE)

基于Optuna的SIMD点积引擎设计空间探索，用于验证"逻辑深度墙"假设。

## 项目概述

本项目探索SimdDotProduct设计的参数空间，寻找**Area**和**TOPS**之间的帕累托最优解。

### 核心假设

随着SIMD并行度（n_lanes）增加，组合逻辑深度增长导致时序违例，有效频率下降，最终导致性能饱和——即"逻辑深度墙"现象。

### 优化目标

- **最大化**: TOPS (Tera Operations Per Second)
  - `TOPS = 2 × n_lanes × F_real / 1000`
  - F_real = 基于WNS的有效频率

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
        ├── simd_dse_config.py   # 参数空间和TOPS计算
        └── run_simd_dse.py      # 主执行脚本
```

## DSE参数空间

| 参数 | 范围 | 说明 |
|------|------|------|
| `n_lanes` | [4, 8, 16, 32, 64, 128] | SIMD并行度 |
| `target_clock_ns` | 2.0 ~ 20.0 ns | 目标时钟周期 (50MHz ~ 500MHz) |
| `input_width` | 8 (固定) | 输入位宽 |
| `output_width` | 16 (固定) | 输出位宽 |

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

1. **Area vs TOPS帕累托前沿** - 主图，标注最优解
2. **n_lanes参数扫描** - n_lanes vs Area/TOPS
3. **target_clock参数扫描** - clock vs Area/TOPS
4. **优化历史曲线** - 收敛性分析

### HTML交互式Dashboard

- `SimdDotProduct_pareto.html` - 帕累托前沿（可交互）

### 文本报告 (`SimdDotProduct_results.txt`)

- 帕累托最优解列表
- 所有可行解的参数组合

## 预期结果

根据"逻辑深度墙"假设，Area-TOPS曲线应呈现：

1. **线性区** (n_lanes = 4~16)
   - 陡峭上升，面积增加直接换来性能提升
   - slack > 0，时序裕量充足

2. **膝点** (n_lanes = 32~64)
   - 最佳性价比点
   - slack ≈ 0，接近时序边界

3. **饱和区** (n_lanes = 128+)
   - 曲线趋于平缓甚至下降
   - slack < 0，有效频率暴跌
   - 面积翻倍但TOPS几乎不增长

## 关键技术特性

### 有效频率计算

```python
if WNS < 0:
    F_real = 1 / (T_target + |WNS|)  # 惩罚时序违例
else:
    F_real = 1 / T_target
```

### 连续约束优化

```python
# 使用slack的连续值而非二元0/1
constraint = -slack  # 提供梯度信息给Optuna
```

### 参数化时钟约束

```tcl
# constraints.sdc中读取环境变量
if {[info exists env(TARGET_CLOCK_NS)]} {
    set clk_period [expr {$env(TARGET_CLOCK_NS) * 1000}]
}
```

## 扩展到其他设计

DSE框架是通用的，添加新设计只需：

1. 在`eda/<DesignName>/`创建EDA流程文件
2. 在`eda/dse/<DesignName>/`创建专用配置：
   - 实现`suggest_params()` - 参数空间
   - 实现`calc_performance()` - 性能计算
   - 实现`check_constraints()` - 约束检查
3. 创建主执行脚本调用`run_dse()`

参考`eda/dse/SimdDotProduct/`的实现。

## 依赖

- Bazel (构建系统)
- OpenROAD (EDA工具链)
- Python ≥ 3.8
- Optuna ≥ 3.0.0
- Matplotlib ≥ 3.5.0
- NumPy ≥ 1.21.0

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
