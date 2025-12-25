load("@bazel-orfs//:openroad.bzl", "orfs_flow", "orfs_run")

exports_files(
    [
        "constraints.sdc",
        "results.tcl",
    ],
    visibility = ["//visibility:public"],
)

target_name = "SimdDotProduct"
top_module = "SimdDotProduct"

orfs_flow(
    name = target_name,
    arguments = {
        # Core utilization and placement density
        "CORE_UTILIZATION": "50",
        "PLACE_DENSITY": "0.20",

        # Clock period controlled via --define=CLOCK_PERIOD=<value_in_ps>
        # Example: bazel build --define=CLOCK_PERIOD=20000 ...
        # Default (from constraints.sdc): 10000ps = 10ns = 100MHz

        # Standard configuration
        "SETUP_SLACK_MARGIN": "0",

        # Enable timing-driven optimization
        "GPL_TIMING_DRIVEN": "1",
        "GPL_ROUTABILITY_DRIVEN": "1",

        # CTS and repair timing
        "SKIP_CTS_REPAIR_TIMING": "0",
        "SKIP_INCREMENTAL_REPAIR": "0",

        # Enable all reporting
        "SKIP_REPORT_METRICS": "0",
    },
    sources = {
        "SDC_FILE": [":constraints.sdc"],
    },
    top = top_module,
    verilog_files = [
        "//hdl/chisel/src/{name}:{name}-generate-verilog-single-file.sv".format(name = target_name)
    ],
)

# PPA metrics extraction (after CTS stage for accurate timing)
orfs_run(
    name = "{base}_ppa".format(base = target_name),
    src = "{name}_cts".format(name = target_name),
    outs = [
        "{name}_ppa.txt".format(name = target_name),
    ],
    arguments = {
        "DESIGN_NAME": top_module,
        "OUTPUT": "$(location :{name}_ppa.txt)".format(name = target_name),
    },
    script = ":results.tcl",
)
