private const val DEFAULT_NAME = "Kotlin"
private const val DEFAULT_RANGE_START = 1
private const val DEFAULT_RANGE_END = 5
private val DEFAULT_RANGE = DEFAULT_RANGE_START..DEFAULT_RANGE_END

fun greeting(name: String): String = "Hello, $name!"

fun counterLines(range: IntRange): List<String> = range.map { "i = $it" }

fun buildOutput(
    name: String = DEFAULT_NAME,
    range: IntRange = DEFAULT_RANGE,
): List<String> = listOf(greeting(name)) + counterLines(range)

fun main() {
    buildOutput().forEach(::println)
}
