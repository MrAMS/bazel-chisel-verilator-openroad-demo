load("@rules_cc//cc:defs.bzl", "cc_test")
load("@rules_verilator//verilator:defs.bzl", "verilator_cc_library")

target_name = "counter"

module_top = "Counter"

verilator_cc_library(
    name = "{name}-cc-library".format(name = target_name),
    copts = [
        "-Os",
        "-Wno-all",
    ],
    module = "//hdl/chisel/src/{name}:{name}-generate-verilog-split-files".format(name = target_name),
    module_top = module_top,
    tags = ["manual"],
    trace = True,
    vopts = [],
)

cc_test(
    name = "counter-test",
    srcs = ["counter.cc"],
    # copts = select({
    #     "//rules/build_settings:enable_wave_tracing": ["-DWAVEON"],
    #     "//conditions:default": [],
    # }),
    visibility = ["//visibility:public"],
    deps = [
        ":" + target_name + "-cc-library",
        "@googletest//:gtest",
        "@googletest//:gtest_main",
    ],
)
