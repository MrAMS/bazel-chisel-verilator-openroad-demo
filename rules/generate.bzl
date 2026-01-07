"""
Chisel Verilog generation rules for Bazel.

This module provides rules for generating SystemVerilog from Chisel:
- chisel_verilog_directory: Generates split Verilog files in a directory
"""

load("@rules_verilator//verilog:providers.bzl", "make_dag_entry", "make_verilog_info")
load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _chisel_verilog_impl(ctx):
    """Common implementation for Chisel Verilog generation.

    Args:
        ctx: Rule context
    """
    output = ctx.actions.declare_directory(ctx.attr.name)

    args = ctx.actions.args()

    # Add application custom options (e.g., --dataBits=4)
    args.add_all([ctx.expand_location(opt, ctx.attr.data) for opt in ctx.attr.app_opts])

    # Check for chisel_app_opts (public attribute for custom rules)
    # or _chisel_app_opts (private attribute for default rules)
    chisel_app_opts_attr = None
    if hasattr(ctx.attr, "chisel_app_opts") and ctx.attr.chisel_app_opts:
        chisel_app_opts_attr = ctx.attr.chisel_app_opts
    elif hasattr(ctx.attr, "_chisel_app_opts"):
        chisel_app_opts_attr = ctx.attr._chisel_app_opts

    if chisel_app_opts_attr:
        raw_cli_opts = chisel_app_opts_attr[BuildSettingInfo].value
        if raw_cli_opts:
            cli_args_list = raw_cli_opts.split(" ")
            cli_args_list = [a for a in cli_args_list if a]
            args.add_all(cli_args_list)

    # Check for batch_id (used for DSE cache invalidation)
    # The batch_id value is not used in the command, but its presence in the
    # action inputs forces Bazel to invalidate cache when it changes
    batch_id_attr = None
    if hasattr(ctx.attr, "batch_id") and ctx.attr.batch_id:
        batch_id_attr = ctx.attr.batch_id
        # We read the value to make Bazel track it as an input to the action
        _ = batch_id_attr[BuildSettingInfo].value

    # Add first -- separator
    args.add("--")

    # Add ChiselStage options (e.g., --target-dir)
    args.add("--target-dir", output.path)
    args.add("--split-verilog")
    args.add_all([ctx.expand_location(opt, ctx.attr.data) for opt in ctx.attr.chisel_opts])

    # Add second -- separator
    args.add("--")

    # Add firtool options
    args.add_all([ctx.expand_location(opt, ctx.attr.data) for opt in ctx.attr.firtool_opts])
    args.add("-o", output.path)

    ctx.actions.run(
        arguments = [args],
        executable = ctx.executable.generator,
        inputs = [
            ctx.executable.generator,
        ] + ctx.files.data,
        outputs = [output],
        mnemonic = "ChiselVerilogGeneration",
    )

    verilog_info = make_verilog_info(
        new_entries = [
            make_dag_entry(
                srcs = [output],
                hdrs = [],
                includes = [
                    output.path,
                    output.path + "/Simulation",
                    output.path + "/verification",
                    output.path + "/verification/assume",
                    output.path + "/verification/cover",
                    output.path + "/verification/assert",
                ],
                data = [],
                deps = [],
                label = ctx.label,
                tags = [],
            ),
        ],
        old_infos = [],
    )
    return [
        DefaultInfo(
            runfiles = ctx.runfiles(files = []),
            files = depset([output]),
        ),
        verilog_info,
    ]

def chisel_verilog_attrs():
    """Common attributes for Chisel Verilog rules."""
    return {
        "app_opts": attr.string_list(
            default = [],
            doc = "Application-specific options (e.g., --dataBits=4)",
        ),
        "chisel_opts": attr.string_list(
            default = [],
            doc = "Additional ChiselStage command line options (e.g., --split-verilog)",
        ),
        "data": attr.label_list(
            allow_files = True,
        ),
        "firtool_opts": attr.string_list(
            default = [],
            doc = "Firtool command line options (e.g., --default-layer-specialization=disable)",
        ),
        "generator": attr.label(
            cfg = "exec",
            executable = True,
            mandatory = True,
        ),
    }

chisel_verilog_directory = rule(
    implementation = lambda ctx: _chisel_verilog_impl(ctx),
    attrs = dict(
        chisel_verilog_attrs(),
        batch_id = attr.label(
            default = None,
            doc = "Optional label to string_flag containing batch_id for DSE cache invalidation",
        ),
        chisel_app_opts = attr.label(
            default = None,
            doc = "Optional label to string_flag containing custom chisel_app_opts (overrides default)",
        ),
        _chisel_app_opts = attr.label(
            default = "//rules:chisel_app_opts",
            doc = "Default chisel_app_opts (used if chisel_app_opts is not specified)",
        ),
    ),
    doc = "Generates split SystemVerilog files from Chisel in a directory.",
)
