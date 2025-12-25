load("@pip//:requirements.bzl", "requirement")

# SimdDotProduct DSE configuration library
py_library(
    name = "simd_dse_config",
    srcs = ["simd_dse_config.py"],
    visibility = ["//visibility:public"],
    deps = [
        requirement("optuna"),
    ],
)

# Main DSE execution script
py_binary(
    name = "run_simd_dse",
    srcs = ["run_simd_dse.py"],
    main = "run_simd_dse.py",
    deps = [
        ":simd_dse_config",
        "//eda/dse:dse_config",
        "//eda/dse:dse_runner",
        requirement("optuna"),
        requirement("plotly"),
    ],
    data = [
        "//eda/SimdDotProduct:constraints.sdc",
        "//eda/SimdDotProduct:results.tcl",
    ],
)
