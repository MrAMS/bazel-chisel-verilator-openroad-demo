# SimdDotProduct Clock Constraints
# Supports parameterized clock period via environment variables
# Priority: ABC_CLOCK_PERIOD_IN_PS > CLOCK_PERIOD > default

set clk_name clock
set clk_port_name clock

# Read clock period (in picoseconds) with fallback priority:
# 1. ABC_CLOCK_PERIOD_IN_PS (ORFS standard for synthesis timing)
# 2. CLOCK_PERIOD (legacy/custom variable)
# 3. Default: 10000ps = 10ns = 100MHz
if {[info exists env(ABC_CLOCK_PERIOD_IN_PS)]} {
    set clk_period $env(ABC_CLOCK_PERIOD_IN_PS)
    puts "Using ABC_CLOCK_PERIOD_IN_PS from environment: $clk_period ps ([expr {$clk_period / 1000.0}] ns)"
} elseif {[info exists env(CLOCK_PERIOD)]} {
    set clk_period $env(CLOCK_PERIOD)
    puts "Using CLOCK_PERIOD from environment: $clk_period ps ([expr {$clk_period / 1000.0}] ns)"
} else {
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
