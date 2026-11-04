#include <gtest/gtest.h>
#include "live_renderer/windows/ui_editor_interaction.hpp"

using namespace live_renderer;

class UIEditorInteractionTest : public ::testing::Test {
protected:
    void SetUp() override {
        elements_.clear();

        // Element 0: top-left region [100, 100, 200, 200] in 1000x1000 window
        ElementConfig el0;
        el0.type = "user_text";
        el0.rect = {0.10f, 0.10f, 0.20f, 0.20f};
        el0.z_position = 1;
        elements_.push_back(el0);

        // Element 1: region [800, 450, 480, 180] in 1000x900 window
        ElementConfig el1;
        el1.type = "game_timer";
        el1.rect = {0.50f, 0.50f, 0.30f, 0.20f};
        el1.z_position = 2;
        elements_.push_back(el1);
    }

    std::vector<ElementConfig> elements_;
    // Non-16:9 window: 1000x900. Height 900 -> unit_w = 900*16/9 = 1600.
    const int win_w_ = 1000;
    const int win_h_ = 900;
};

TEST_F(UIEditorInteractionTest, SelectsElementOnClickWhenNoneSelected) {
    UIEditorInteraction interaction;
    int selected_index = -1;

    // Element 0: [160, 90, 320, 180]. Click inside at (200, 150)
    bool handled = interaction.HandleMouseDown(
        200, 150, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(handled);
    EXPECT_EQ(selected_index, 0);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::Move);
}

TEST_F(UIEditorInteractionTest, DoesNotSwitchSelectionWhenClickingAlreadySelectedElement) {
    UIEditorInteraction interaction;

    // Add overlapping element 2 with higher Z over element 0
    // el2 is {0.15, 0.15, 0.20, 0.20} -> [240, 135, 320, 180]
    ElementConfig el2;
    el2.type = "player_name";
    el2.rect = {0.15f, 0.15f, 0.20f, 0.20f};
    el2.z_position = 10;
    elements_.push_back(el2);

    // Element 0 is currently selected
    int selected_index = 0;

    // Click at (260, 160) which is inside BOTH element 0 and element 2
    bool handled = interaction.HandleMouseDown(
        260, 160, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(handled);
    // Should NOT switch to element 2 because element 0 was already selected at that position
    EXPECT_EQ(selected_index, 0);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::Move);
}

TEST_F(UIEditorInteractionTest, SwitchesSelectionWhenClickingOutsideSelectedElement) {
    UIEditorInteraction interaction;
    int selected_index = 0;

    // Element 1 is {0.50, 0.50, 0.30, 0.20} -> [800, 450, 480, 180]
    // Click inside element 1 at (850, 500), which is outside element 0
    bool handled = interaction.HandleMouseDown(
        850, 500, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(handled);
    EXPECT_EQ(selected_index, 1);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::Move);
}

TEST_F(UIEditorInteractionTest, DragsToMoveElement) {
    UIEditorInteraction interaction;
    int selected_index = 0;

    // Mouse down on element 0 at (200, 150)
    interaction.HandleMouseDown(
        200, 150, win_w_, win_h_, elements_, selected_index);

    // Drag by (+160px, +90px) to (360, 240)
    bool moved = interaction.HandleMouseMove(
        360, 240, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(moved);
    // Element 0 initial rect was {0.10, 0.10, 0.20, 0.20} -> should now be {0.20, 0.20, 0.20, 0.20}
    EXPECT_NEAR(elements_[0].rect[0], 0.20f, 0.001f);
    EXPECT_NEAR(elements_[0].rect[1], 0.20f, 0.001f);
    EXPECT_NEAR(elements_[0].rect[2], 0.20f, 0.001f);
    EXPECT_NEAR(elements_[0].rect[3], 0.20f, 0.001f);

    // Mouse up concludes drag
    interaction.HandleMouseUp(360, 240);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::None);
}

TEST_F(UIEditorInteractionTest, DragsBottomRightCornerToResize) {
    UIEditorInteraction interaction;
    int selected_index = 0;

    // Element 0 bounds are [160, 90, 320, 180], so bottom-right corner is at (480, 270)
    // Click within resize handle margin (e.g. at 478, 268)
    bool handled = interaction.HandleMouseDown(
        478, 268, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(handled);
    EXPECT_EQ(selected_index, 0);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::Resize);

    // Drag corner from (480, 270) to (640, 360)
    bool resized = interaction.HandleMouseMove(
        640, 360, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(resized);
    // Top-left stays at {0.10, 0.10}
    EXPECT_NEAR(elements_[0].rect[0], 0.10f, 0.001f);
    EXPECT_NEAR(elements_[0].rect[1], 0.10f, 0.001f);
    // New width = (640 - 160) / 1600 = 0.30f, height = (360 - 90) / 900 = 0.30f
    EXPECT_NEAR(elements_[0].rect[2], 0.30f, 0.001f);
    EXPECT_NEAR(elements_[0].rect[3], 0.30f, 0.001f);

    interaction.HandleMouseUp(640, 360);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::None);
}

TEST_F(UIEditorInteractionTest, SelectsTopmostElementWhenOverlapping) {
    // Add two overlapping elements at the same position with different Z
    elements_.clear();

    ElementConfig bottom_el;
    bottom_el.type = "bottom";
    bottom_el.rect = {0.1f, 0.1f, 0.3f, 0.3f};
    bottom_el.z_position = 1;
    elements_.push_back(bottom_el);

    ElementConfig top_el;
    top_el.type = "top";
    top_el.rect = {0.1f, 0.1f, 0.3f, 0.3f};
    top_el.z_position = 10;
    elements_.push_back(top_el);

    UIEditorInteraction interaction;
    int selected_index = -1;

    // Bounds are [160, 90, 480, 270]. Click at (200, 150)
    interaction.HandleMouseDown(
        200, 150, win_w_, win_h_, elements_, selected_index);

    // Should select top_el (index 1) because of higher Z
    EXPECT_EQ(selected_index, 1);
}

TEST_F(UIEditorInteractionTest, HandleSdlEventDispatchesCorrectly) {
    UIEditorInteraction interaction;
    int selected_index = -1;

    // 1. Mouse down event inside element 0 [160, 90, 320, 180]
    SDL_Event down_event;
    down_event.type = SDL_MOUSEBUTTONDOWN;
    down_event.button.button = SDL_BUTTON_LEFT;
    down_event.button.x = 200;
    down_event.button.y = 150;

    EXPECT_TRUE(interaction.HandleSdlEvent(
        down_event, win_w_, win_h_, elements_, selected_index));
    EXPECT_EQ(selected_index, 0);

    // 2. Mouse motion event
    SDL_Event motion_event;
    motion_event.type = SDL_MOUSEMOTION;
    motion_event.motion.state = SDL_BUTTON_LMASK;
    motion_event.motion.x = 220;
    motion_event.motion.y = 170;

    EXPECT_TRUE(interaction.HandleSdlEvent(
        motion_event, win_w_, win_h_, elements_, selected_index));

    // 3. Mouse up event
    SDL_Event up_event;
    up_event.type = SDL_MOUSEBUTTONUP;
    up_event.button.button = SDL_BUTTON_LEFT;
    up_event.button.x = 220;
    up_event.button.y = 170;

    EXPECT_TRUE(interaction.HandleSdlEvent(
        up_event, win_w_, win_h_, elements_, selected_index));
    EXPECT_EQ(interaction.GetDragMode(), DragMode::None);
}

