/**
 * Implementation of CrashHandler for Windows and cross-platform fallback.
 */

#include "live_renderer/diagnostics/crash_handler.hpp"

#include <chrono>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>

#include "live_renderer/version.hpp"

#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <dbghelp.h>
#endif

namespace live_renderer {

namespace {

std::string g_log_filename = "crash.log";
std::mutex g_log_mutex;

#if defined(_WIN32)
LPTOP_LEVEL_EXCEPTION_FILTER g_prev_filter = nullptr;
_invalid_parameter_handler g_prev_invalid_param = nullptr;
_purecall_handler g_prev_purecall = nullptr;
#endif

std::string GetCurrentTimestampString() {
    auto now = std::chrono::system_clock::now();
    std::time_t t = std::chrono::system_clock::to_time_t(now);
    std::tm tm_buf{};
#if defined(_WIN32)
    localtime_s(&tm_buf, &t);
#else
    localtime_r(&t, &tm_buf);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm_buf, "%Y-%m-%d %H:%M:%S");
    return oss.str();
}

#if defined(_WIN32)
const char* ExceptionCodeToString(DWORD code) {
    switch (code) {
        case EXCEPTION_ACCESS_VIOLATION:
            return "EXCEPTION_ACCESS_VIOLATION (Access Violation)";
        case EXCEPTION_ARRAY_BOUNDS_EXCEEDED:
            return "EXCEPTION_ARRAY_BOUNDS_EXCEEDED";
        case EXCEPTION_BREAKPOINT:
            return "EXCEPTION_BREAKPOINT";
        case EXCEPTION_DATATYPE_MISALIGNMENT:
            return "EXCEPTION_DATATYPE_MISALIGNMENT";
        case EXCEPTION_FLT_DENORMAL_OPERAND:
            return "EXCEPTION_FLT_DENORMAL_OPERAND";
        case EXCEPTION_FLT_DIVIDE_BY_ZERO:
            return "EXCEPTION_FLT_DIVIDE_BY_ZERO";
        case EXCEPTION_FLT_INEXACT_RESULT:
            return "EXCEPTION_FLT_INEXACT_RESULT";
        case EXCEPTION_FLT_INVALID_OPERATION:
            return "EXCEPTION_FLT_INVALID_OPERATION";
        case EXCEPTION_FLT_OVERFLOW:
            return "EXCEPTION_FLT_OVERFLOW";
        case EXCEPTION_FLT_STACK_CHECK:
            return "EXCEPTION_FLT_STACK_CHECK";
        case EXCEPTION_FLT_UNDERFLOW:
            return "EXCEPTION_FLT_UNDERFLOW";
        case EXCEPTION_ILLEGAL_INSTRUCTION:
            return "EXCEPTION_ILLEGAL_INSTRUCTION";
        case EXCEPTION_IN_PAGE_ERROR:
            return "EXCEPTION_IN_PAGE_ERROR";
        case EXCEPTION_INT_DIVIDE_BY_ZERO:
            return "EXCEPTION_INT_DIVIDE_BY_ZERO";
        case EXCEPTION_INT_OVERFLOW:
            return "EXCEPTION_INT_OVERFLOW";
        case EXCEPTION_INVALID_DISPOSITION:
            return "EXCEPTION_INVALID_DISPOSITION";
        case EXCEPTION_NONCONTINUABLE_EXCEPTION:
            return "EXCEPTION_NONCONTINUABLE_EXCEPTION";
        case EXCEPTION_PRIV_INSTRUCTION:
            return "EXCEPTION_PRIV_INSTRUCTION";
        case EXCEPTION_SINGLE_STEP:
            return "EXCEPTION_SINGLE_STEP";
        case EXCEPTION_STACK_OVERFLOW:
            return "EXCEPTION_STACK_OVERFLOW";
        default:
            return "UNKNOWN_EXCEPTION";
    }
}
#endif

void WriteCrashReport(
    const std::string& reason,
    const std::string& details,
    const std::string& callstack) {
    std::lock_guard<std::mutex> lock(g_log_mutex);
    std::ofstream file(g_log_filename, std::ios::out | std::ios::app);
    if (!file.is_open()) {
        std::cerr << "[CrashHandler] Failed to open " << g_log_filename << "\n";
        return;
    }

    file << "=========================================================\n";
    file << "LF Live Renderer Crash Report\n";
    file << "Timestamp: " << GetCurrentTimestampString() << "\n";
    file << "Version:   v" << kLiveRendererVersion << "\n";
    file << "Reason:    " << reason << "\n";
    if (!details.empty()) {
        file << "Details:   " << details << "\n";
    }
    file << "---------------------------------------------------------\n";
    file << "Callstack:\n";
    file << callstack;
    file << "=========================================================\n\n";
    file.flush();

    std::cerr << "\n[CRASH DETECTED] " << reason << "\n";
    std::cerr << "Crash log written to: " << g_log_filename << "\n\n";
    std::cerr << callstack << std::endl;

#if defined(_WIN32)
    std::string msg = "LF Live Renderer encountered a fatal error:\n" +
                      reason + "\n\nA crash log has been written to:\n" +
                      g_log_filename;
    MessageBoxA(nullptr, msg.c_str(), "LF Live Renderer Crash",
                MB_ICONERROR | MB_OK | MB_SYSTEMMODAL);
#endif
}

#if defined(_WIN32)
LONG WINAPI UnhandledCrashFilter(EXCEPTION_POINTERS* ep) {
    std::string reason = "Unhandled Win32 Exception";
    std::string details;

    if (ep && ep->ExceptionRecord) {
        DWORD code = ep->ExceptionRecord->ExceptionCode;
        std::ostringstream oss;
        oss << ExceptionCodeToString(code) << " (Code: 0x" << std::hex
            << std::uppercase << code << ") at address 0x"
            << ep->ExceptionRecord->ExceptionAddress;
        reason = oss.str();

        if (code == EXCEPTION_ACCESS_VIOLATION &&
            ep->ExceptionRecord->NumberParameters >= 2) {
            ULONG_PTR op = ep->ExceptionRecord->ExceptionInformation[0];
            ULONG_PTR addr = ep->ExceptionRecord->ExceptionInformation[1];
            std::ostringstream d_oss;
            d_oss << (op == 0 ? "Read" : (op == 1 ? "Write" : "Execute"))
                  << " access violation at address 0x" << std::hex
                  << std::uppercase << addr;
            details = d_oss.str();
        }
    }

    std::string stack = CrashHandler::CaptureStackTrace(0, 32);
    WriteCrashReport(reason, details, stack);

    return EXCEPTION_EXECUTE_HANDLER;
}

void CustomInvalidParameterHandler(
    const wchar_t* expression,
    const wchar_t* function,
    const wchar_t* file,
    unsigned int line,
    uintptr_t /*reserved*/) {
    std::string reason = "CRT Invalid Parameter";
    std::ostringstream oss;
    if (expression) {
        oss << "Expression: ";
        while (*expression) { oss << static_cast<char>(*expression++); }
        oss << " ";
    }
    if (function) {
        oss << "Function: ";
        while (*function) { oss << static_cast<char>(*function++); }
        oss << " ";
    }
    if (file) {
        oss << "File: ";
        while (*file) { oss << static_cast<char>(*file++); }
        oss << ":" << line;
    }
    std::string stack = CrashHandler::CaptureStackTrace(1, 32);
    WriteCrashReport(reason, oss.str(), stack);
    std::abort();
}

void CustomPurecallHandler() {
    std::string stack = CrashHandler::CaptureStackTrace(1, 32);
    WriteCrashReport("Pure Virtual Function Call", "", stack);
    std::abort();
}
#endif

void SignalCrashHandler(int signal_num) {
    std::string reason = "Signal Received: ";
    switch (signal_num) {
        case SIGSEGV: reason += "SIGSEGV (Segmentation Fault)"; break;
        case SIGABRT: reason += "SIGABRT (Abort)"; break;
        case SIGFPE:  reason += "SIGFPE (Floating Point Exception)"; break;
        case SIGILL:  reason += "SIGILL (Illegal Instruction)"; break;
        case SIGTERM: reason += "SIGTERM (Termination Request)"; break;
        default:      reason += std::to_string(signal_num); break;
    }
    std::string stack = CrashHandler::CaptureStackTrace(1, 32);
    WriteCrashReport(reason, "", stack);
    std::exit(1);
}

}  // namespace

void CrashHandler::Install(const std::string& log_filename) {
    if (!log_filename.empty()) {
        g_log_filename = log_filename;
    }

#if defined(_WIN32)
    g_prev_filter = SetUnhandledExceptionFilter(UnhandledCrashFilter);
    g_prev_invalid_param =
        _set_invalid_parameter_handler(CustomInvalidParameterHandler);
    g_prev_purecall = _set_purecall_handler(CustomPurecallHandler);
#endif

    std::signal(SIGSEGV, SignalCrashHandler);
    std::signal(SIGABRT, SignalCrashHandler);
    std::signal(SIGFPE, SignalCrashHandler);
    std::signal(SIGILL, SignalCrashHandler);
    std::signal(SIGTERM, SignalCrashHandler);
}

void CrashHandler::Uninstall() {
#if defined(_WIN32)
    if (g_prev_filter) {
        SetUnhandledExceptionFilter(g_prev_filter);
        g_prev_filter = nullptr;
    }
    if (g_prev_invalid_param) {
        _set_invalid_parameter_handler(g_prev_invalid_param);
        g_prev_invalid_param = nullptr;
    }
    if (g_prev_purecall) {
        _set_purecall_handler(g_prev_purecall);
        g_prev_purecall = nullptr;
    }
#endif
    std::signal(SIGSEGV, SIG_DFL);
    std::signal(SIGABRT, SIG_DFL);
    std::signal(SIGFPE, SIG_DFL);
    std::signal(SIGILL, SIG_DFL);
    std::signal(SIGTERM, SIG_DFL);
}

std::string CrashHandler::GetLogFilePath() {
    return g_log_filename;
}

void CrashHandler::LogMessage(const std::string& message) {
    std::lock_guard<std::mutex> lock(g_log_mutex);
    std::ofstream file(g_log_filename, std::ios::out | std::ios::app);
    if (file.is_open()) {
        file << "[" << GetCurrentTimestampString() << "] " << message << "\n";
        file.flush();
    }
}

std::string CrashHandler::CaptureStackTrace(
    size_t skip_frames,
    size_t max_frames) {
    std::ostringstream oss;

#if defined(_WIN32)
    HANDLE process = GetCurrentProcess();
    SymInitialize(process, nullptr, TRUE);

    void* stack[64];
    unsigned short frames = CaptureStackBackTrace(
        static_cast<DWORD>(skip_frames),
        static_cast<DWORD>(std::min(max_frames, size_t{64})),
        stack,
        nullptr);

    constexpr size_t kMaxNameLen = 256;
    alignas(SYMBOL_INFO) char buffer[sizeof(SYMBOL_INFO) + kMaxNameLen];
    SYMBOL_INFO* symbol = reinterpret_cast<SYMBOL_INFO*>(buffer);
    symbol->SizeOfStruct = sizeof(SYMBOL_INFO);
    symbol->MaxNameLen = kMaxNameLen;

    IMAGEHLP_LINE64 line_info{};
    line_info.SizeOfStruct = sizeof(IMAGEHLP_LINE64);

    for (unsigned short i = 0; i < frames; ++i) {
        DWORD64 address = reinterpret_cast<DWORD64>(stack[i]);
        DWORD displacement = 0;
        DWORD64 disp64 = 0;

        oss << "  #" << std::setw(2) << std::setfill('0') << i << " 0x"
            << std::hex << std::uppercase << address << " in ";

        if (SymFromAddr(process, address, &disp64, symbol)) {
            oss << symbol->Name;
            if (SymGetLineFromAddr64(process, address, &displacement,
                                     &line_info)) {
                oss << " at " << line_info.FileName << ":"
                    << std::dec << line_info.LineNumber;
            }
        } else {
            oss << "<unknown symbol>";
        }
        oss << "\n";
    }

    SymCleanup(process);
#else
    oss << "  <Stack trace capture not implemented for platform>\n";
#endif

    return oss.str();
}

}  // namespace live_renderer

