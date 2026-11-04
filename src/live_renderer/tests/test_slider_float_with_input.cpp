#include <gtest/gtest.h>
#include <imgui.h>
#include "live_renderer/widgets/slider_float_with_input.hpp"

using namespace live_renderer;

class SliderFloatWithInputTest : public ::testing::Test {
protected:
    void SetUp() override {
        IMGUI_CHECKVERSION();
        ctx_ = ImGui::CreateContext();
        ImGuiIO& io = ImGui::GetIO();
        io.DisplaySize = ImVec2(800.0f, 600.0f);
        unsigned char* pixels;
        int width, height;
        io.Fonts->GetTexDataAsRGBA32(&pixels, &width, &height);
    }

    void TearDown() override {
        if (ctx_) {
            ImGui::DestroyContext(ctx_);
            ctx_ = nullptr;
        }
    }

    ImGuiContext* ctx_ = nullptr;
};

TEST_F(SliderFloatWithInputTest, NullPointerReturnsFalse) {
    ImGui::NewFrame();
    EXPECT_FALSE(SliderFloatWithInput::Render("Test", nullptr, 0.0f, 10.0f));
    ImGui::Render();
}

TEST_F(SliderFloatWithInputTest, RendersWithLabelAndSuffixWithoutCrashing) {
    float val = 10.0f;
    ImGui::NewFrame();
    bool changed = SliderFloatWithInput::Render(
        "Tilt Angle", &val, -45.0f, 45.0f, "deg");
    ImGui::Render();

    EXPECT_FALSE(changed);
    EXPECT_FLOAT_EQ(val, 10.0f);
}

