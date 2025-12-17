package counter

import chisel3._
import _root_.circt.stage.{ChiselStage}

class Counter(dataBits: Int) extends Module {
  val io = IO(new Bundle {
    val out = Output(UInt(dataBits.W))
  })

  val reg = RegInit(0.U(dataBits.W))
  reg := reg + 1.U
  io.out := reg
}

object EmitCounter extends App {
  // Split by first "--"
  val (appArgs, rest1) = args.span(_ != "--")
  val rest1Dropped = rest1.drop(1)

  // Split by second "--"
  val (chiselArgs, rest2) = rest1Dropped.span(_ != "--")
  val firtoolArgs = rest2.drop(1)

  // Parse app configs
  val configs: Map[String, String] = appArgs.collect {
    case arg if arg.startsWith("--") && arg.contains("=") =>
      val Array(key, value) = arg.stripPrefix("--").split("=", 2)
      key -> value
  }.toMap

  println(s"Configs: $configs")
  println(s"Chisel Args: ${chiselArgs.mkString(" ")}")
  println(s"Firtool Args: ${firtoolArgs.mkString(" ")}")

  ChiselStage.emitSystemVerilogFile(
    new Counter(configs.getOrElse("dataBits", "4").toInt),
    args = chiselArgs,
    firtoolOpts = firtoolArgs
  )
}
