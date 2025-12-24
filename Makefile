gen:
	bazel build //hdl/chisel/src/checker:checker-generate-verilog-split-files

sim:
	bazel run //cpp/verilator_tests:counter-test

debug:
	bazel run //cpp/verilator_tests:counter-test --config=debug
	-gtkwave bazel-bin/cpp/verilator_tests/counter-test.runfiles/_main/wave.vcd -a gtkwave.sav --saveonexit

eda:
	bazel build //eda/counter:counter_results

eda-gui:
	rm -rf /tmp/route
	bazel run //eda/counter:counter_route /tmp/route gui_route

clangd: sim
	bazel run :refresh_compile_commands

.PHONY: gen sim debug eda clangd
