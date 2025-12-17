load("@bazel-orfs//:verilog.bzl", "verilog_single_file_library")
load("@bazel-orfs//toolchains/scala:chisel.bzl", "chisel_binary", "chisel_library")
load("//:generate.bzl", "chisel_verilog_directory")

target_name = "counter"

emit_class = "counter.EmitCounter"

chisel_binary(
    name = target_name,
    srcs = glob(["**/*.scala"]),
    main_class = emit_class,
    scalacopts = ["-Ytasty-reader"],
    deps = [
        "@maven//:com_github_scopt_scopt_2_13",
        "@maven//:io_circe_circe_yaml_2_13",
        "@maven//:io_circe_circe_yaml_common_2_13",
    ],
)

chisel_verilog_directory(
    name = target_name + "-generate-verilog-split-files",
    app_opts = [
        "--dataBits=3",
    ],
    data = [
        ":" + target_name,
    ],
    firtool_opts = [
        "--default-layer-specialization=disable",
    ],
    generator = ":" + target_name,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

verilog_single_file_library(
    name = target_name + "-generate-verilog-single-file.sv",
    srcs = [target_name + "-generate-verilog-split-files"],
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

# Support for Metals
chisel_library(
    name = target_name + "-library",
    srcs = glob(["**/*.scala"]),
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
