# A Demo of Chisel+Verilator+OpenROAD Workflow

[![chisel-verilator-openroad-demo](https://github.com/MrAMS/bazel-chisel-verilator-openroad-demo/actions/workflows/ci.yaml/badge.svg)](https://github.com/MrAMS/bazel-chisel-verilator-openroad-demo/actions/workflows/ci.yaml)

Bazel handles the rest. Just code the future of silicon. :rocket:


## Prerequisites

The project’s validity is confirmed by its successful execution on GitHub Actions without any manual intervention. However, due to variations across Linux distributions, you may need to install the following dependencies on your local machine:
- Docker, OpenJDK, and [coursier](https://get-coursier.io/docs/cli-installation).
- PyYAML and GNU Time

If you encounter errors regarding a missing firtool binary, try running the build command with `--spawn_strategy=local` for the first time to enable the automatic download.
