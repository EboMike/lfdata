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

        // Element 1: bottom-right region [500, 500, 300, 200] in 1000x1000 window
        ElementConfig el1;
        el1.type = "game_timer";
        el1.rect = {0.50f, 0.50f, 0.30f, 0.20f};
        el1.z_position = 2;
        elements_.push_back(el1);
    }

    std::vector<ElementConfig> elements_;
    const int win_w_ = 1000;
    const int win_h_ = 1000;
};

TEST_F(UIEditorInteractionTest, SelectsElementOnClickWhenNoneSelected) {
    UIEditorInteraction interaction;
    int selected_index = -1;

    // Click inside element 0 (150, 150)
    bool handled = interaction.HandleMouseDown(
        150, 150, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(handled);
    EXPECT_EQ(selected_index, 0);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::Move);
}

TEST_F(UIEditorInteractionTest, DoesNotSwitchSelectionWhenClickingAlreadySelectedElement) {
    UIEditorInteraction interaction;

    // Add overlapping element 2 with higher Z over element 0
    ElementConfig el2;
    el2.type = "player_name";
    el2.rect = {0.15f, 0.15f, 0.20f, 0.20f}; // [150, 150, 200, 200]
    el2.z_position = 10;
    elements_.push_back(el2);

    // Element 0 is currently selected
    int selected_index = 0;

    // Click at (180, 180) which is inside BOTH element 0 and element 2
    bool handled = interaction.HandleMouseDown(
        180, 180, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(handled);
    // Should NOT switch to element 2 because element 0 was already selected at that position
    EXPECT_EQ(selected_index, 0);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::Move);
}

TEST_F(UIEditorInteractionTest, SwitchesSelectionWhenClickingOutsideSelectedElement) {
    UIEditorInteraction interaction;
    int selected_index = 0;

    // Click inside element 1 (600, 550), which is outside element 0
    bool handled = interaction.HandleMouseDown(
        600, 550, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(handled);
    EXPECT_EQ(selected_index, 1);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::Move);
}

TEST_F(UIEditorInteractionTest, DragsToMoveElement) {
    UIEditorInteraction interaction;
    int selected_index = 0;

    // Mouse down on element 0 at (150, 150)
    interaction.HandleMouseDown(
        150, 150, win_w_, win_h_, elements_, selected_index);

    // Drag by (+100px, +50px) to (250, 200)
    bool moved = interaction.HandleMouseMove(
        250, 200, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(moved);
    // Element 0 initial rect was {0.10, 0.10, 0.20, 0.20} -> should now be {0.20, 0.15, 0.20, 0.20}
    EXPECT_NEAR(elements_[0].rect[0], 0.20f, 0.001f);
    EXPECT_NEAR(elements_[0].rect[1], 0.15f, 0.001f);
    EXPECT_NEAR(elements_[0].rect[2], 0.20f, 0.001f);
    EXPECT_NEAR(elements_[0].rect[3], 0.20f, 0.001f);

    // Mouse up concludes drag
    interaction.HandleMouseUp(250, 200);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::None);
}

TEST_F(UIEditorInteractionTest, DragsBottomRightCornerToResize) {
    UIEditorInteraction interaction;
    int selected_index = 0;

    // Element 0 bounds are [100, 100, 200, 200], so bottom-right corner is at (300, 300)
    // Click within resize handle margin (e.g. at 295, 295)
    bool handled = interaction.HandleMouseDown(
        295, 295, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(handled);
    EXPECT_EQ(selected_index, 0);
    EXPECT_EQ(interaction.GetDragMode(), DragMode::Resize);

    // Drag corner from (300, 300) to (400, 350)
    bool resized = interaction.HandleMouseMove(
        400, 350, win_w_, win_h_, elements_, selected_index);

    EXPECT_TRUE(resized);
    // Top-left stays at {0.10, 0.10}
    EXPECT_NEAR(elements_[0].rect[0], 0.10f, 0.001f);
    EXPECT_NEAR(elements_[0].rect[1], 0.10f, 0.001f);
    // New width = (400 - 100) / 1000 = 0.30f, height = (350 - 100) / 1000 = 0.25f
    EXPECT_NEAR(elements_[0].rect[2], 0.30f, 0.001f);
    EXPECT_NEAR(elements_[0].rect[3], 0.25f, 0.001f);

    interaction.HandleMouseUp(400, 350);
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

    // Click inside the overlapping bounds
    interaction.HandleMouseDown(
        200, 200, win_w_, win_h_, elements_, selected_index);

    // Should select top_el (index 1) because of higher Z
    EXPECT_EQ(selected_index, 1);
}

TEST_F(UIEditorInteractionTest, HandleSdlEventDispatchesCorrectly) {
    UIEditorInteraction interaction;
    int selected_index = -1;

    // 1. Mouse down event
    SDL_Event down_event;
    down_event.type = SDL_MOUSEBUTTONDOWN;
    down_event.button.button = SDL_BUTTON_LEFT;
    down_event.button.x = 150;
    down_event.button.y = 150;

    EXPECT_TRUE(interaction.HandleSdlEvent(
        down_event, win_w_, win_h_, elements_, selected_index));
    EXPECT_EQ(selected_index, 0);

    // 2. Mouse motion event
    SDL_Event motion_event;
    motion_event.type = SDL_MOUSEMOTION;
    motion_event.motion.state = SDL_BUTTON_LMASK;
    motion_event.motion.x = 180;
    motion_event.motion.y = 180;

    EXPECT_TRUE(interaction.HandleSdlEvent(
        motion_event, win_w_, win_h_, elements_, selected_index));

    // 3. Mouse up event
    SDL_Event up_event;
    up_event.type = SDL_MOUSEBUTTONUP;
    up_event.button.button = SDL_BUTTON_LEFT;
    up_event.button.x = 180;
    up_event.button.y = 180;

    EXPECT_TRUE(interaction.HandleSdlEvent(
        up_event, win_w_, win_h_, elements_, selected_index));
    EXPECT_EQ(interaction.GetDragMode(), DragMode::None);
}

