# Extract PPA metrics for SimdDotProduct DSE
# Reports timing slack and target frequency from clock constraints

source $::env(SCRIPTS_DIR)/open.tcl

set clock [lindex [all_clocks] 0]
set clock_period [get_property $clock period]

set f [open $::env(OUTPUT) w]

# Basic design information
puts $f "design_name: $::env(DESIGN_NAME)"

# Cell area (um^2)
set cell_area [sta::format_area [rsz::design_area] 0]
puts $f "cell_area: $cell_area"

# Timing analysis - report worst setup slack
# Use report_worst_slack to get WNS (includes all clocks)
set slack [sta::worst_slack -max]
puts $f "slack: $slack"

# Target frequency from clock constraint (clock_period is in picoseconds)
# Convert ps to GHz: 1 GHz = 1000 ps, so GHz = 1000 / ps
# Convert ps to MHz: 1 MHz = 1000000 ps, so MHz = 1000000 / ps
set target_freq_ghz [expr {1000.0 / $clock_period}]
set target_freq_mhz [expr {1000000.0 / $clock_period}]
puts $f "target_frequency_ghz: $target_freq_ghz"
puts $f "target_frequency_mhz: $target_freq_mhz"
puts $f "clock_period_ps: $clock_period"

# Effective frequency accounting for WNS (for DSE performance calculation)
# If WNS >= 0: use target frequency
# If WNS < 0: actual achievable frequency is reduced
if {$slack >= 0} {
    set effective_freq_ghz $target_freq_ghz
} else {
    # F_real = 1 / (T_target + |WNS|)
    # Convert to same units: clock_period is in ps, slack is in ps
    set actual_period [expr {$clock_period + abs($slack)}]
    set effective_freq_ghz [expr {1000.0 / $actual_period}]
}
puts $f "effective_frequency_ghz: $effective_freq_ghz"

# Power analysis
set_power_activity -input -activity 0.5
report_power > power_report.txt

set power_file [open power_report.txt r]
set power_content [read $power_file]
close $power_file

# Parse power from report (line 10, last column)
set power_lines [split $power_content "\n"]
if {[llength $power_lines] > 9} {
    set power_line [lindex $power_lines 9]
    if {[regexp {(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)} $power_line -> _ _ _ _ power]} {
        puts $f "estimated_power_uw: $power"
    } else {
        puts $f "estimated_power_uw: 0"
    }
} else {
    puts $f "estimated_power_uw: 0"
}

# Instance count
set instance_count [llength [get_cells *]]
puts $f "instances: $instance_count"

close $f

puts "PPA metrics extraction complete"
puts "Clock period: $clock_period ps ([expr {$clock_period / 1000.0}] ns)"
puts "Target frequency: $target_freq_ghz GHz"
