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
    # Some simple parameters, we don't care about physical size, we're counting
    # instances.
    arguments = {
        "CORE_UTILIZATION": "20",
        # Speed up the flow by skipping things
        "FILL_CELLS": "",
        "GND_NETS_VOLTAGES": "",
        "GPL_ROUTABILITY_DRIVEN": "0",
        "GPL_TIMING_DRIVEN": "0",
        # Normal parameters
        "PLACE_DENSITY": "0.40",
        "PWR_NETS_VOLTAGES": "",
        "SETUP_SLACK_MARGIN": "-10000",
        "SKIP_CTS_REPAIR_TIMING": "1",
        "SKIP_INCREMENTAL_REPAIR": "1",
        "SKIP_REPORT_METRICS": "1",
        "TAPCELL_TCL": "",
        "TNS_END_PERCENT": "0",
    },
    sources = {
        "SDC_FILE": [":constraints.sdc"],
    },
    top = top_module,
    verilog_files = ["//hdl/chisel/src/{name}:{name}-{name}-generate-verilog-single-file.sv".format(name = target_name)],
)

orfs_run(
    name = "{base}_results".format(base = target_name),
    # count instances after floorplan, more than accurate enough and faster
    src = "{name}_floorplan".format(name = target_name),
    outs = [
        "{name}_stats".format(name = target_name),
    ],
    arguments = {
        "NAME": target_name,
        "OUTPUT": "$(location :{name}_stats)".format(name = target_name),
    },
    script = ":results.tcl",
)
