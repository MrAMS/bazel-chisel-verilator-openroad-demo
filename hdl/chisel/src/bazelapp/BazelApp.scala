package BazelApp

/**
 * Base trait for Chisel built by Bazel.
 *
 * Bazel will parse command-line arguments in the format:
 * [Custom Args] -- [Chisel Args] -- [Firtool Args]
 */
trait BazelApp extends App {
  private lazy val firstSep = args.indexOf("--")

  private lazy val secondSep = args.indexOf("--", firstSep + 1)

  def validateArgs(): Unit = {
    require(firstSep != -1 && secondSep != -1,
      s"Args format error! Expected: [Custom Args] -- [Chisel Args] -- [Firtool Args].\nReceived: ${if (args != null) args.mkString(" ") else "null"}")
  }

  private lazy val rawBazelArgs = {
    validateArgs()
    args.take(firstSep)
  }

  /**
   * Arguments passed to Chisel Stage (between two "--").
   */
  lazy val chiselArgs: Array[String] = args.slice(firstSep + 1, secondSep)

  /**
   * Arguments passed to Firtool (after second "--").
   */
  lazy val firtoolArgs: Array[String] = args.drop(secondSep + 1)

  /**
   * Parsed custom Bazel arguments.
   */
  lazy val bazelArgs: Map[String, String] = rawBazelArgs.collect {
    case arg if arg.startsWith("--") =>
      val parts = arg.stripPrefix("--").split("=", 2)
      if (parts.length == 2) parts(0) -> parts(1)
      else parts(0) -> "true" // Handle bool_flag
  }.toMap

  def print_args(): Unit = {
    println(Console.CYAN + "=" * 60)
    println(s"Debug: ${this.getClass.getSimpleName.stripSuffix("$")} Initialized")
    println(s"[-] Bazel Custom Args: $bazelArgs")
    println(s"[-] Chisel Args:       ${chiselArgs.mkString(" ")}")
    println(s"[-] Firtool Args:      ${firtoolArgs.mkString(" ")}")
    println("=" * 60 + Console.RESET)
  }

  def getArg(key: String, default: String): String = bazelArgs.getOrElse(key, default)
  def getIntArg(key: String, default: Int): Int = bazelArgs.get(key).map(_.toInt).getOrElse(default)
  def hasArg(key: String): Boolean = bazelArgs.contains(key)
}
