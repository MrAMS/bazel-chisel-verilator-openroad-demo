load("@bazel-orfs//toolchains/scala:chisel.bzl", "chisel_library")

# bsp library aggregating all chisel modules for Bazel BSP (Metals) indexing
# Since src/counter is a subpackage, we need to depend on its library
chisel_library(
    name = "bsp",
    tags = ["manual"],
    visibility = ["//visibility:public"],
    exports = [
        # add more here
        "//hdl/chisel/src/counter:counter-library",
    ],
)
