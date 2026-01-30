load("//rules:rules.bzl", "gen_rtl_target")

target_name = "checker"
emit_class = "checker.EmitChecker"

gen_rtl_target(
    target_name=target_name,
    emit_class = "checker.EmitChecker",
    srcs=["checker.scala"],
    deps=["//hdl/chisel/src/counter:counter-lib"],
    app_opts=["--dataBits=3"],
)
