load("@bazel_skylib//rules:common_settings.bzl", "bool_flag")

bool_flag(
    name = "wave_tracing",
    build_setting_default = False,
)
config_setting(
    name = "enable_wave_tracing",
    flag_values = {
        ":wave_tracing": "True",
    },
)
