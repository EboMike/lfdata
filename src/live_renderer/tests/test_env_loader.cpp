#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>
#include "live_renderer/config/env_loader.hpp"

using namespace live_renderer;

class EnvLoaderTest : public ::testing::Test {
protected:
    void SetUp() override {
        EnvLoader::Clear();
    }

    void TearDown() override {
        EnvLoader::Clear();
    }
};

TEST_F(EnvLoaderTest, SetGetHasAndClear) {
    EXPECT_FALSE(EnvLoader::Has("TEST_KEY"));
    EXPECT_EQ(EnvLoader::Get("TEST_KEY", "fallback"), "fallback");

    EnvLoader::Set("TEST_KEY", "sample_secret_123");
    EXPECT_TRUE(EnvLoader::Has("TEST_KEY"));
    EXPECT_EQ(EnvLoader::Get("TEST_KEY"), "sample_secret_123");

    EnvLoader::Clear();
    EXPECT_FALSE(EnvLoader::Has("TEST_KEY"));
    EXPECT_EQ(EnvLoader::Get("TEST_KEY"), "");
}

TEST_F(EnvLoaderTest, ParsesEnvFileWithVariousFormats) {
    const std::string test_env_path = "test_sample.env";
    {
        std::ofstream out(test_env_path);
        out << "# A comment line\n";
        out << "\n";
        out << "LFSTATS_API_KEY=my_secret_token_abc\n";
        out << "  SPACED_KEY  =   spaced_value   \n";
        out << "DOUBLE_QUOTED=\"quoted_value_123\"\n";
        out << "SINGLE_QUOTED='single_quoted_val'\n";
        out << "EMPTY_VAL=\n";
        out << "# Another comment\n";
        out << "INVALID_LINE_NO_EQUALS\n";
    }

    EXPECT_TRUE(EnvLoader::Load(test_env_path));
    EXPECT_EQ(EnvLoader::Get("LFSTATS_API_KEY"), "my_secret_token_abc");
    EXPECT_EQ(EnvLoader::Get("SPACED_KEY"), "spaced_value");
    EXPECT_EQ(EnvLoader::Get("DOUBLE_QUOTED"), "quoted_value_123");
    EXPECT_EQ(EnvLoader::Get("SINGLE_QUOTED"), "single_quoted_val");
    EXPECT_EQ(EnvLoader::Get("EMPTY_VAL", "default_val"), "default_val");
    EXPECT_FALSE(EnvLoader::Has("INVALID_LINE_NO_EQUALS"));

    std::filesystem::remove(test_env_path);
}

TEST_F(EnvLoaderTest, ReturnsFalseOnNonExistentFile) {
    EXPECT_FALSE(EnvLoader::Load("non_existent_file_xyz_12345.env"));
}

