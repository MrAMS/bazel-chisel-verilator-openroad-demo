# SimdDotProduct Clock Constraints
# Supports parameterized clock period via CLOCK_PERIOD environment variable

set clk_name clock
set clk_port_name clock

# Read clock period from CLOCK_PERIOD environment variable (in picoseconds)
# Can be overridden via: bazel build --define=CLOCK_PERIOD=<value_in_ps> ...
if {[info exists env(CLOCK_PERIOD)]} {
    set clk_period $env(CLOCK_PERIOD)
    puts "Using CLOCK_PERIOD from environment: $clk_period ps ([expr {$clk_period / 1000.0}] ns)"
} else {
    # Default: 10000ps = 10ns = 100MHz
    set clk_period 10000
    puts "Using default clock period: $clk_period ps (10 ns, 100 MHz)"
}

# Set I/O path max delays based on clock period
# Platform SDC checks for these variables and uses them if defined
# Default would be 80ps which is too tight for most designs
# Set to 80% of clock period for reasonable I/O timing constraints
set in2reg_max [expr {$clk_period * 0.8}]
set reg2out_max [expr {$clk_period * 0.8}]
set in2out_max [expr {$clk_period * 0.8}]

# Source platform-specific constraints
source $env(PLATFORM_DIR)/constraints.sdc
