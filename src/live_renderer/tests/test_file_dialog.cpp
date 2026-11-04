#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>
#include "live_renderer/widgets/file_dialog.hpp"

using namespace live_renderer;

TEST(FileDialogTest, PlatformSupportCheck) {
#if defined(_WIN32)
    EXPECT_TRUE(FileDialog::IsSupported());
#else
    EXPECT_FALSE(FileDialog::IsSupported());
    EXPECT_TRUE(FileDialog::ShowOpenImageDialog().empty());
#endif
}

TEST(FileDialogTest, NormalizePathEmpty) {
    EXPECT_EQ(FileDialog::NormalizePath(""), "");
}

TEST(FileDialogTest, NormalizePathPreservesRelativeForwardSlashes) {
    EXPECT_EQ(
        FileDialog::NormalizePath("assets/sm5/commander.png"),
        "assets/sm5/commander.png");
}

TEST(FileDialogTest, NormalizePathConvertsBackslashes) {
    EXPECT_EQ(
        FileDialog::NormalizePath("assets\\sm5\\commander.png"),
        "assets/sm5/commander.png");
}

TEST(FileDialogTest, NormalizePathConvertsAbsoluteInsideCwd) {
    std::error_code ec;
    auto cur = std::filesystem::current_path(ec);
    ASSERT_FALSE(ec);
    auto abs = cur / "assets" / "logo.png";
    EXPECT_EQ(FileDialog::NormalizePath(abs.string()), "assets/logo.png");
}

TEST(FileDialogTest, NormalizePathWithBaseDir) {
    std::error_code ec;
    auto cur = std::filesystem::current_path(ec);
    ASSERT_FALSE(ec);
    auto cfg_dir = cur / "config";
    auto abs_cfg = cfg_dir / "custom.yaml";
    EXPECT_EQ(
        FileDialog::NormalizePath(abs_cfg.string(), cfg_dir.string()),
        "custom.yaml");
}

TEST(FileDialogTest, IsValidPathChecksExistence) {
    EXPECT_TRUE(FileDialog::IsValidPath(""));

    // Check existing file
    std::error_code ec;
    auto cur = std::filesystem::current_path(ec);
    ASSERT_FALSE(ec);
    auto test_file = cur / "test_temp_val.txt";
    {
        std::ofstream ofs(test_file);
        ofs << "test";
    }

    EXPECT_TRUE(FileDialog::IsValidPath(test_file.string()));
    EXPECT_TRUE(FileDialog::IsValidPath("test_temp_val.txt"));

    std::filesystem::remove(test_file, ec);

    // Non-existent file must return false
    EXPECT_FALSE(FileDialog::IsValidPath("non_existent_file_12345.xyz"));
}

