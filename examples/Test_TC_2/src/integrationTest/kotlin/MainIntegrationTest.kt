import org.junit.jupiter.api.Assertions.assertIterableEquals
import org.junit.jupiter.api.Test
import java.io.ByteArrayOutputStream
import java.io.PrintStream

class MainIntegrationTest {
    @Test
    fun `main prints the default output`() {
        val originalOut = System.out
        val capturedOutput = ByteArrayOutputStream()

        System.setOut(PrintStream(capturedOutput, true, Charsets.UTF_8))

        try {
            main()
        } finally {
            System.setOut(originalOut)
        }

        assertIterableEquals(
            listOf("Hello, Kotlin!", "i = 1", "i = 2", "i = 3", "i = 4", "i = 5"),
            capturedOutput.toString(Charsets.UTF_8).trim().lines(),
        )
    }
}
