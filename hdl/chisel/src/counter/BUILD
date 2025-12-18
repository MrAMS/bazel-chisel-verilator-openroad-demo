load("//rules:rules.bzl", "gen_rtl_target")

gen_rtl_target(
    package_name="counter",
    name="counter",
    emit_class = "counter.EmitCounter",
    srcs=["counter.scala"],
    deps=[],
    app_opts=["--dataBits=3"],
)
