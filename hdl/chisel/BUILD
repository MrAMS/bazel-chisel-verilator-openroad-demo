load("@bazel-orfs//toolchains/scala:scala_library.bzl", "scala_library")
load("@bazel-orfs//toolchains/scala:scala_bloop.bzl", "scala_bloop")

genrule(
    name = "dummy_scala_file",
    outs = ["Dummy.scala"],
    cmd = "echo 'package dummy' > $@",
)

scala_library(
    name = "bloop_aggregator",
    srcs = [":dummy_scala_file"],
    deps = [
        # add your packages here to use bloop
        "//hdl/chisel/src/counter:blooplib-counter",
    ],
    tags = ["manual"],
)

# Support for metals
# One bloop to rule them all
scala_bloop(
    name = "bloop",
    src = ":bloop_aggregator",
)
