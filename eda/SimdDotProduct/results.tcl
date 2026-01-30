# Extract PPA metrics for SimdDotProduct DSE
# Reports timing slack and target frequency from clock constraints

source $::env(SCRIPTS_DIR)/open.tcl

set clock [lindex [all_clocks] 0]
set clock_period [get_property $clock period]

set f [open $::env(OUTPUT) w]

# Basic design information
puts $f "design_name: $::env(DESIGN_NAME)"

# ============================================================================
# Area Metrics - use OpenDB API for accurate area calculation
# ============================================================================
# Get database handle
set db [::ord::get_db]
set chip [$db getChip]
set block [$chip getBlock]

# Get die area bbox
set die_bbox [$block getDieArea]
set die_width [expr {[$die_bbox xMax] - [$die_bbox xMin]}]
set die_height [expr {[$die_bbox yMax] - [$die_bbox yMin]}]
set die_area [expr {$die_width * $die_height}]
set die_area_um2 [expr {$die_area / 1000000.0}]

# Get core area bbox
set core_bbox [$block getCoreArea]
set core_width [expr {[$core_bbox xMax] - [$core_bbox xMin]}]
set core_height [expr {[$core_bbox yMax] - [$core_bbox yMin]}]
set core_area [expr {$core_width * $core_height}]
set core_area_um2 [expr {$core_area / 1000000.0}]

# Sum all instance areas (excluding blocks/macros)
set total_cell_area 0
foreach inst [$block getInsts] {
    set master [$inst getMaster]
    if {![$master isBlock]} {
        set inst_width [$master getWidth]
        set inst_height [$master getHeight]
        set inst_area [expr {$inst_width * $inst_height}]
        set total_cell_area [expr {$total_cell_area + $inst_area}]
    }
}
# Convert from DBU^2 to um^2 (divide by 1e6 since DBU is in nanometers)
set cell_area_um2 [expr {$total_cell_area / 1000000.0}]

# Calculate utilization
if {$core_area_um2 > 0} {
    set utilization [expr {$cell_area_um2 / $core_area_um2 * 100.0}]
} else {
    set utilization 0.0
}

# Output area metrics
puts $f "die_area: $die_area_um2"
puts $f "core_area: $core_area_um2"
puts $f "cell_area: $cell_area_um2"
puts $f "utilization: $utilization"

# ============================================================================
# Cell Count Metrics
# ============================================================================
set num_cells 0
set num_sequential 0
foreach inst [$block getInsts] {
    incr num_cells
    set master [$inst getMaster]
    if {[$master isSequential]} {
        incr num_sequential
    }
}
set num_nets [llength [$block getNets]]

puts $f "num_cells: $num_cells"
puts $f "num_sequential: $num_sequential"
puts $f "num_nets: $num_nets"

# ============================================================================
# Timing Analysis
# ============================================================================
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

# Parse power from report
# Look for the "Total" line which contains the total power
set power_found 0
set power_lines [split $power_content "\n"]
foreach line $power_lines {
    # Match lines like: "Total                    1.23e-03  ..."
    if {[regexp {^\s*Total\s+(\S+)} $line -> power_value]} {
        # Convert scientific notation to microwatts
        # Power is typically in Watts, convert to uW (multiply by 1e6)
        set power_w [expr {double($power_value)}]
        set power_uw [expr {$power_w * 1e6}]
        puts $f "estimated_power_uw: $power_uw"
        set power_found 1
        break
    }
}
if {!$power_found} {
    puts $f "estimated_power_uw: 0"
}

close $f

puts "PPA metrics extraction complete"
puts "Clock period: $clock_period ps ([expr {$clock_period / 1000.0}] ns)"
puts "Target frequency: $target_freq_ghz GHz"
