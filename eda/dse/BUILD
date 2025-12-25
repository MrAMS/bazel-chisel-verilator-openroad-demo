load("@pip//:requirements.bzl", "requirement")

# DSE configuration data structures
py_library(
    name = "dse_config",
    srcs = ["dse_config.py"],
    visibility = ["//visibility:public"],
)

# Bazel builder and PPA parser
py_library(
    name = "bazel_builder",
    srcs = ["bazel_builder.py"],
    visibility = ["//visibility:public"],
    deps = [
        ":dse_config",
    ],
)

# Optuna optimization functions
py_library(
    name = "optimization",
    srcs = ["optimization.py"],
    visibility = ["//visibility:public"],
    deps = [
        ":dse_config",
        ":bazel_builder",
        requirement("optuna"),
    ],
)

# Visualization and plotting
py_library(
    name = "visualization",
    srcs = ["visualization.py"],
    visibility = ["//visibility:public"],
    deps = [
        ":dse_config",
        requirement("optuna"),
        requirement("matplotlib"),
        requirement("numpy"),
    ],
)

# Main DSE runner
py_library(
    name = "dse_runner",
    srcs = ["dse_runner.py"],
    visibility = ["//visibility:public"],
    deps = [
        ":dse_config",
        ":bazel_builder",
        ":optimization",
        ":visualization",
        requirement("optuna"),
    ],
)

