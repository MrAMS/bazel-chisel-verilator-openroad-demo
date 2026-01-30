# A Demo of Chisel+Verilator+OpenROAD Workflow

[![chisel-verilator-openroad-demo](https://github.com/MrAMS/bazel-chisel-verilator-openroad-demo/actions/workflows/ci.yaml/badge.svg?branch=masterV2)](https://github.com/MrAMS/bazel-chisel-verilator-openroad-demo/actions/workflows/ci.yaml)

Bazel handles the rest. Just code the future of silicon. :rocket:

## Prerequisites

The project’s validity is confirmed by its successful execution on GitHub Actions without any manual intervention. However, due to variations across Linux distributions, you may need to install the following dependencies on your local machine:
- Docker, OpenJDK, and [coursier](https://get-coursier.io/docs/cli-installation).
- PyYAML and GNU Time

If you encounter errors regarding a missing firtool binary for the first-time build, try running the build command with `--spawn_strategy=local` to enable the automatic deps download.

## Usage

This repository follows a Layered Branch Strategy. If you want to use the underlying infrastructure (build scripts, configs) without the example code (e.g. `cpp`, `eda`, `hdl/chisel/src/checker`), we recommend basing your project on the `template-core` branch.

```bash
# Setup new project based on template
git init
git remote add template https://github.com/MrAMS/bazel-chisel-verilator-openroad-demo.git
git fetch template
git merge template/template-core --allow-unrelated-histories

# Keeping template up-to-date
git fetch template
git merge template/template-core
```
