load("@bazel-orfs//:verilog.bzl", "verilog_single_file_library")
load("@bazel-orfs//toolchains/scala:chisel.bzl", "chisel_binary", "chisel_library")
load("//rules:generate.bzl", "chisel_verilog_directory")


def gen_rtl_target(target_name, emit_class, srcs, deps=[], app_opts=[]):

    # BazelApp handle the bazel args
    final_deps = deps + ["//hdl/chisel/src/bazelapp:BazelApp-lib"]

    chisel_binary(
        name = target_name,
        srcs = srcs,
        main_class = emit_class,
        deps = final_deps,
        scalacopts = ["-Ytasty-reader"],
        visibility = ["//visibility:public"],
        #tags = ["manual"], # speedup BSP
    )

    chisel_library(
        name = target_name + "-lib",
        srcs = srcs,
        deps = final_deps,
        visibility = ["//visibility:public"],
    )

    chisel_verilog_directory(
        name = target_name + "-generate-verilog-split-files",
        app_opts = app_opts,
        data = [
            ":" + target_name,
        ],
        firtool_opts = [
            "--default-layer-specialization=disable", # otherwise single-file.sv will fail
            "--lowering-options=disallowLocalVariables,disallowPackedArrays,locationInfoStyle=wrapInAtSquareBracket,noAlwaysComb",
            "--disable-all-randomization",
            "--preserve-aggregate=none",
        ],
        generator = ":" + target_name,
        visibility = ["//visibility:public"],
        tags = ["manual"],
    )

    verilog_single_file_library(
        name = target_name + "-generate-verilog-single-file.sv",
        srcs = [target_name + "-generate-verilog-split-files"],
        visibility = ["//visibility:public"],
        tags = ["manual"],
    )
