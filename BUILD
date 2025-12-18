load("@hedron_compile_commands//:refresh_compile_commands.bzl", "refresh_compile_commands")
load("@rules_python//python:pip.bzl", "compile_pip_requirements")
load("@rules_scala//scala:scala_toolchain.bzl", "scala_toolchain")

# python pip
compile_pip_requirements(
    name = "requirements",
    srcs = ["requirements.in"],
    requirements_txt = "requirements_lock.txt",
)

# compile_commands.json
refresh_compile_commands(
    name = "refresh_compile_commands",
    exclude_external_sources = True,
    targets = {
        "//cpp/verilator_tests/...": "",
    },
)

# Custom Scala toolchain with SemanticDB enabled
scala_toolchain(
    name = "semanticdb_toolchain_impl",
    enable_semanticdb = True,
    semanticdb_bundle_in_jar = False,
    visibility = ["//visibility:public"],
)

toolchain(
    name = "semanticdb_toolchain",
    toolchain = ":semanticdb_toolchain_impl",
    toolchain_type = "@rules_scala//scala:toolchain_type",
)
