load("@bazel-orfs//:openroad.bzl", "orfs_flow", "orfs_run")
load("@bazel-orfs//:verilog.bzl", "verilog_single_file_library")
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")
load("@pip//:requirements.bzl", "requirement")
load("//rules:generate.bzl", "chisel_verilog_directory")

# ============================================================================
# DSE Python Infrastructure
# ============================================================================

# SimdDotProduct DSE configuration library
py_library(
    name = "simd_dse_config",
    srcs = ["simd_dse_config.py"],
    visibility = ["//visibility:public"],
    deps = [
        requirement("optuna"),
    ],
)

# Main DSE execution script
py_binary(
    name = "run_simd_dse",
    srcs = ["run_simd_dse.py"],
    main = "run_simd_dse.py",
    deps = [
        ":simd_dse_config",
        "//eda/dse:dse_config",
        "//eda/dse:dse_runner",
        requirement("optuna"),
        requirement("plotly"),
    ],
    data = [
        "//eda/SimdDotProduct:constraints.sdc",
        "//eda/SimdDotProduct:results.tcl",
    ],
)

# ============================================================================
# Parallel DSE Build Infrastructure
# ============================================================================

target_name = "SimdDotProduct"
top_module = "SimdDotProduct"

# Number of max parallel variants for DSE
N_PARALLEL = 8

# Create string flags for each parallel variant
# These allow passing different parameters to each variant
[string_flag(
    name = "chisel_opts_{}".format(i),
    build_setting_default = "",
) for i in range(N_PARALLEL)]

[string_flag(
    name = "abc_clock_ps_{}".format(i),
    build_setting_default = "1000",
) for i in range(N_PARALLEL)]

[string_flag(
    name = "batch_id_{}".format(i),
    build_setting_default = "0",
) for i in range(N_PARALLEL)]

# ============================================================================
# DSE-specific Verilog generation targets
# Generate independent Verilog files for each parallel variant
# ============================================================================

# Generate split Verilog files for each variant with different chisel_opts
# batch_id is included to force Bazel to invalidate cache between batches
[chisel_verilog_directory(
    name = "{}_variant_{}_verilog_split".format(target_name, i),
    app_opts = [],
    batch_id = ":batch_id_{}".format(i),
    chisel_app_opts = ":chisel_opts_{}".format(i),
    data = ["//hdl/chisel/src/{}:{}".format(target_name, target_name)],
    firtool_opts = [
        "--default-layer-specialization=disable",
        "--lowering-options=disallowLocalVariables,disallowPackedArrays,locationInfoStyle=wrapInAtSquareBracket,noAlwaysComb",
        "--disable-all-randomization",
        "--preserve-aggregate=none",
    ],
    generator = "//hdl/chisel/src/{}:{}".format(target_name, target_name),
    tags = ["manual"],
) for i in range(N_PARALLEL)]

# Convert split files to single file for each variant
[verilog_single_file_library(
    name = "{}_variant_{}_verilog.sv".format(target_name, i),
    srcs = [":{}_variant_{}_verilog_split".format(target_name, i)],
    tags = ["manual"],
) for i in range(N_PARALLEL)]

# ============================================================================
# Parallel flow variants for DSE
# Each variant uses its own Verilog file generated with different chisel_opts
# ============================================================================

[orfs_flow(
    name = "{}_{}".format(target_name, i),
    arguments = {
        "CORE_UTILIZATION": "50",
        "PLACE_DENSITY": "0.20",
        # Synthesis
        "SYNTH_HDL_FRONTEND": "slang",
        # Not used, just slows things down
        "SKIP_REPORT_METRICS": "1",
        # repair only worst, only if we actually want to close timing do we
        # want to run repair on all endpoints
        "TNS_END_PERCENT": "0",
    },
    settings = {
        # Per-variant clock period from string_flag
        # Set via: --//eda/dse/SimdDotProduct:abc_clock_ps_0=1000
        "ABC_CLOCK_PERIOD_IN_PS": ":abc_clock_ps_{}".format(i),
    },
    sources = {
        "SDC_FILE": ["//eda/SimdDotProduct:constraints.sdc"],
    },
    tags = ["manual"],  # Don't build by default
    top = top_module,
    variant = "{}".format(i),
    # Use per-variant Verilog file generated with chisel_opts_N
    verilog_files = [
        ":{}_variant_{}_verilog.sv".format(target_name, i)
    ],
) for i in range(N_PARALLEL)]

# ============================================================================
# PPA metrics extraction for parallel variants
# ============================================================================

[orfs_run(
    name = "{}_{}_ppa".format(target_name, i),
    src = "{}_{}_{}_cts".format(target_name, i, i),  # orfs_flow generates name_variant_variant_stage
    outs = [
        "{}_{}_ppa.txt".format(target_name, i),
    ],
    arguments = {
        "DESIGN_NAME": top_module,
        "OUTPUT": "$(location :{}_{}_ppa.txt)".format(target_name, i),
    },
    script = "//eda/SimdDotProduct:results.tcl",
    tags = ["manual"],  # Don't build by default
) for i in range(N_PARALLEL)]
