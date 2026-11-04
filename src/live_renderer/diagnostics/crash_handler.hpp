#ifndef LIVE_RENDERER_DIAGNOSTICS_CRASH_HANDLER_HPP_
#define LIVE_RENDERER_DIAGNOSTICS_CRASH_HANDLER_HPP_

/**
 * Crash handler and diagnostic logger for LF Live Renderer.
 *
 * Intercepts unhandled exceptions, CRT invalid parameters, pure virtual calls,
 * and fatal signals, formatting a detailed crash report with stack backtraces
 * and writing it to 'crash.log'.
 *
 * Example:
 *   live_renderer::CrashHandler::Install("crash.log");
 */

#include <string>

namespace live_renderer {

/**
 * @brief Global crash handler installer and exception logger.
 */
class CrashHandler {
public:
    /**
     * @brief Installs global exception and signal handlers.
     *
     * Registers Windows unhandled exception filters, CRT invalid parameter
     * handlers, and standard POSIX/C signals.
     *
     * @param log_filename Optional target filename for the crash log.
     */
    static void Install(const std::string& log_filename = "crash.log");

    /**
     * @brief Uninstalls previously registered handlers.
     */
    static void Uninstall();

    /**
     * @brief Gets the path of the crash log file.
     *
     * @return Path to the crash log file.
     */
    static std::string GetLogFilePath();

    /**
     * @brief Writes a diagnostic message directly into the crash log file.
     *
     * @param message Informational or diagnostic message to record.
     */
    static void LogMessage(const std::string& message);

    /**
     * @brief Captures and formats the current call stack.
     *
     * @param skip_frames Number of initial stack frames to omit.
     * @param max_frames Maximum number of frames to capture.
     * @return Formatted multi-line string with symbolized stack frames.
     */
    static std::string CaptureStackTrace(
        size_t skip_frames = 1,
        size_t max_frames = 32);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_DIAGNOSTICS_CRASH_HANDLER_HPP_

