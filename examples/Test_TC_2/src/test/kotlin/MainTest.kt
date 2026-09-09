import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertIterableEquals
import org.junit.jupiter.api.Test

class MainTest {
    @Test
    fun `greeting returns a friendly message`() {
        assertEquals("Hello, TeamCity!", greeting("TeamCity"))
    }

    @Test
    fun `counter lines contain every value from the range`() {
        assertIterableEquals(
            listOf("i = 2", "i = 3", "i = 4"),
            counterLines(2..4),
        )
    }

    @Test
    fun `build output combines greeting and counter output`() {
        assertIterableEquals(
            listOf("Hello, Kotlin!", "i = 1", "i = 2", "i = 3"),
            buildOutput(range = 1..3),
        )
    }
}
