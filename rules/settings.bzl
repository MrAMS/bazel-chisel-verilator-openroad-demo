BuildSettingInfo = provider(fields = ["value"])

def _string_flag_impl(ctx):
    return [BuildSettingInfo(value = ctx.build_setting_value)]

string_flag = rule(
    implementation = _string_flag_impl,
    build_setting = config.string(flag = True),
)
