package SimdDotProduct

import chisel3._
import chisel3.util._

case class DotProductParams(
  nLanes: Int,
  inputWidth: Int,
  outputWidth: Int
)

class SimdDotProduct(p: DotProductParams) extends Module {
  require(p.outputWidth >= p.inputWidth * 2, "Output width should typically hold at least one product result")

  val io = IO(new Bundle {
    val a = Input(Vec(p.nLanes, UInt(p.inputWidth.W)))
    val b = Input(Vec(p.nLanes, UInt(p.inputWidth.W)))
    val out = Output(UInt(p.outputWidth.W))
  })

  val products = io.a.zip(io.b).map { case (op1, op2) => op1 * op2 }

  val productsReg = RegNext(VecInit(products.map { prod =>
    val extended = Wire(UInt(p.outputWidth.W))
    extended := prod
    extended
  }))

  val sumTree = productsReg.reduce { (x, y) =>
    val sum = x +& y
    sum(p.outputWidth - 1, 0)
  }

  io.out := RegNext(sumTree)
}

import BazelApp.BazelApp
import _root_.circt.stage.ChiselStage

object EmitSimdDotProduct extends BazelApp {
  print_args()
  ChiselStage.emitSystemVerilogFile(
    new SimdDotProduct(DotProductParams(
      getIntArg("nLanes", 4),
      getIntArg("inputWidth", 8),
      getIntArg("outputWidth", 16)
    )),
    args = chiselArgs,
    firtoolOpts = firtoolArgs
  )
}
