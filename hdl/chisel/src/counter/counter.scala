package counter

import chisel3._
import _root_.circt.stage.{ChiselStage}
import BazelApp.BazelApp

class Counter(dataBits: Int) extends Module {
  val io = IO(new Bundle {
    val out = Output(UInt(dataBits.W))
  })

  val reg = RegInit(0.U(dataBits.W))
  reg := reg + 1.U
  io.out := reg
}

object EmitCounter extends BazelApp {
  print_args()
  ChiselStage.emitSystemVerilogFile(
    new Counter(getIntArg("dataBits", 4)),
    args = chiselArgs,
    firtoolOpts = firtoolArgs
  )
}
