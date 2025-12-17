load("@hedron_compile_commands//:refresh_compile_commands.bzl", "refresh_compile_commands")
load("@rules_python//python:pip.bzl", "compile_pip_requirements")

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
