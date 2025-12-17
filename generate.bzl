"""
Chisel Verilog generation rules for Bazel.

This module provides rules for generating SystemVerilog from Chisel:
- chisel_verilog_directory: Generates split Verilog files in a directory
- chisel_verilog_single_file: Merges split Verilog files into a single file
"""

load("@rules_verilator//verilog:providers.bzl", "make_dag_entry", "make_verilog_info")

def _chisel_verilog_impl(ctx, split):
    """Common implementation for Chisel Verilog generation.

    Args:
        ctx: Rule context
        split: Boolean, if True generates directory output, else single file
    """
    if split:
        output = ctx.actions.declare_directory(ctx.attr.name)
    else:
        output = ctx.actions.declare_file(ctx.attr.name)

    args = ctx.actions.args()
    args.add("-jar", ctx.file.generator)
    # Add --target-dir for Chisel to know where to output files
    args.add("--target-dir", output.path)
    # Add user options (these come after -- separator)
    args.add_all([ctx.expand_location(opt, ctx.attr.data) for opt in ctx.attr.opts])
    # Add -o for firtool (in firtoolOpts after --)
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

    # Create VerilogInfo provider for verilator_cc_library (only for directory output)
    if split:
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
    else:
        return [
            DefaultInfo(
                runfiles = ctx.runfiles(files = []),
                files = depset([output]),
            ),
        ]

def chisel_verilog_attrs():
    """Common attributes for Chisel Verilog rules."""
    return {
        "data": attr.label_list(
            allow_files = True,
        ),
        "generator": attr.label(
            allow_single_file = True,
            cfg = "exec",
            executable = True,
            mandatory = True,
        ),
        "opts": attr.string_list(default = []),
    }

chisel_verilog_directory = rule(
    implementation = lambda ctx: _chisel_verilog_impl(ctx, split = True),
    attrs = chisel_verilog_attrs(),
    doc = "Generates split SystemVerilog files from Chisel in a directory.",
)

chisel_verilog_file = rule(
    implementation = lambda ctx: _chisel_verilog_impl(ctx, split = False),
    attrs = chisel_verilog_attrs(),
    doc = "Generates a single SystemVerilog file from Chisel.",
)

def _only_sv(f):
    """Filter for just SystemVerilog source files."""
    if f.extension in ["v", "sv"]:
        return f.path
    return None

def _chisel_verilog_single_file_impl(ctx):
    """Merges split Verilog files into a single file."""
    out = ctx.actions.declare_file(ctx.attr.name)

    args = ctx.actions.args()
    args.add_all(ctx.files.srcs, map_each = _only_sv)
    ctx.actions.run_shell(
        arguments = [args],
        command = "cat $@ > {}".format(out.path),
        inputs = ctx.files.srcs,
        outputs = [out],
        mnemonic = "MergeVerilog",
    )
    return [
        DefaultInfo(
            runfiles = ctx.runfiles(files = []),
            files = depset([out]),
        ),
    ]

chisel_verilog_single_file = rule(
    implementation = _chisel_verilog_single_file_impl,
    attrs = {
        "srcs": attr.label_list(
            doc = "Verilog directory or files to merge.",
            allow_files = True,
        ),
    },
    doc = "Merges multiple Verilog files into a single file.",
)

# Backward compatibility alias
chisel_verilog_library = chisel_verilog_directory
