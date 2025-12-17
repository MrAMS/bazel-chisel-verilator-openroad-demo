load("@bazel-orfs//:openroad.bzl", "orfs_flow", "orfs_run")

exports_files(
    [
        "constraints.sdc",
        "results.tcl",
    ],
    visibility = ["//visibility:public"],
)

target_name = "counter"
top_module = "Counter"

orfs_flow(
    name = target_name,
    top = top_module,
    # Some simple parameters, we don't care about physical size, we're counting
    # instances.
    arguments = {
        # Speed up the flow by skipping things
        "FILL_CELLS": "",
        "TAPCELL_TCL": "",
        "SKIP_REPORT_METRICS": "1",
        "SKIP_CTS_REPAIR_TIMING": "1",
        "SKIP_INCREMENTAL_REPAIR": "1",
        "GND_NETS_VOLTAGES": "",
        "PWR_NETS_VOLTAGES": "",
        "GPL_ROUTABILITY_DRIVEN": "0",
        "GPL_TIMING_DRIVEN": "0",
        "SETUP_SLACK_MARGIN": "-10000",
        "TNS_END_PERCENT": "0",
        # Normal parameters
        "PLACE_DENSITY": "0.40",
        "CORE_UTILIZATION": "20",
    },
    sources = {
        "SDC_FILE": [":constraints.sdc"],
    },
    verilog_files = ["//hdl/chisel/src/{name}:{name}-generate-verilog-single-file.sv".format(name = target_name)],
)

orfs_run(
    name = "{base}_results".format(base = target_name),
    # count instances after floorplan, more than accurate enough and faster
    src = "{name}_floorplan".format(name = target_name),
    outs = [
        "{name}_stats".format(name = target_name),
    ],
    arguments = {
        "OUTPUT": "$(location :{name}_stats)".format(name = target_name),
        "NAME": target_name,
    },
    script = ":results.tcl",
)
