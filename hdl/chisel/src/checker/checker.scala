package checker

import chisel3._
import _root_.circt.stage.{ChiselStage}
import counter._
import BazelApp.BazelApp

class Checker(dataBits: Int) extends Module {
  val io = IO(new Bundle {
    val out = Output(Bool())
  })

  val counter = Module(new Counter(dataBits))

  io.out := counter.io.out === 0.U
}

object EmitChecker extends BazelApp {
  print_args()
  ChiselStage.emitSystemVerilogFile(
    new Checker(getIntArg("dataBits", 4)),
    args = chiselArgs,
    firtoolOpts = firtoolArgs
  )
}
