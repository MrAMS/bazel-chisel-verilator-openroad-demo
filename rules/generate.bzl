"""
Chisel Verilog generation rules for Bazel.

This module provides rules for generating SystemVerilog from Chisel:
- chisel_verilog_directory: Generates split Verilog files in a directory
"""

load("@rules_verilator//verilog:providers.bzl", "make_dag_entry", "make_verilog_info")

def _chisel_verilog_impl(ctx):
    """Common implementation for Chisel Verilog generation.

    Args:
        ctx: Rule context
    """
    output = ctx.actions.declare_directory(ctx.attr.name)

    args = ctx.actions.args()

    # Add application custom options (e.g., --dataBits=4)
    args.add_all([ctx.expand_location(opt, ctx.attr.data) for opt in ctx.attr.app_opts])

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
    attrs = chisel_verilog_attrs(),
    doc = "Generates split SystemVerilog files from Chisel in a directory.",
)
