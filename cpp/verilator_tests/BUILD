load("@rules_cc//cc:defs.bzl", "cc_test")
load("@rules_verilator//verilator:defs.bzl", "verilator_cc_library")
load("@bazel_skylib//rules:common_settings.bzl", "bool_flag")

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

bool_flag(
    name = "wave_tracing",
    build_setting_default = False,
)
config_setting(
    name = "enable_wave_tracing",
    flag_values = {
        ":wave_tracing": "True",
    },
)

cc_test(
    name = "counter-test",
    srcs = ["counter.cc"],
    copts = select({
        ":enable_wave_tracing": ["-DWAVEON"],
        "//conditions:default": [],
    }),
    visibility = ["//visibility:public"],
    deps = [
        ":" + target_name + "-cc-library",
        "@googletest//:gtest",
        "@googletest//:gtest_main",
    ],
)
