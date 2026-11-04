#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>
#include "live_renderer/diagnostics/crash_handler.hpp"

using namespace live_renderer;

TEST(CrashHandlerTest, InstallsAndUninstallsSafely) {
    CrashHandler::Install("test_crash.log");
    EXPECT_EQ(CrashHandler::GetLogFilePath(), "test_crash.log");
    CrashHandler::Uninstall();
}

TEST(CrashHandlerTest, LogsDiagnosticMessage) {
    const std::string log_file = "test_custom_diag.log";
    if (std::filesystem::exists(log_file)) {
        std::filesystem::remove(log_file);
    }

    CrashHandler::Install(log_file);
    CrashHandler::LogMessage("Test diagnostic entry 12345");
    CrashHandler::Uninstall();

    ASSERT_TRUE(std::filesystem::exists(log_file));
    std::ifstream file(log_file);
    std::string content((std::istreambuf_iterator<char>(file)),
                        std::istreambuf_iterator<char>());
    EXPECT_NE(content.find("Test diagnostic entry 12345"), std::string::npos);

    file.close();
    std::filesystem::remove(log_file);
}

TEST(CrashHandlerTest, CapturesStackTraceNonEmpty) {
    std::string stack = CrashHandler::CaptureStackTrace(0, 16);
    EXPECT_FALSE(stack.empty());
    EXPECT_NE(stack.find("#00"), std::string::npos);
}

