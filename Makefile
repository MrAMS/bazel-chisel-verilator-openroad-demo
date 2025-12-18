gen:
	bazel build //hdl/chisel/src/counter:counter-generate-verilog-split-files

sim:
	bazel run //cpp/verilator_tests:counter-test

debug:
	bazel run //cpp/verilator_tests:counter-test --config=debug
	-gtkwave bazel-bin/cpp/verilator_tests/counter-test.runfiles/_main/wave.vcd -a gtkwave.sav --saveonexit

clangd: sim
	bazel run :refresh_compile_commands

.PHONY: gen sim debug clangd
