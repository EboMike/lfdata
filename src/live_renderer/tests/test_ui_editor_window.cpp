#include <gtest/gtest.h>
#include <filesystem>
#include "live_renderer/config/config_serializer.hpp"
#include <imgui.h>
#include "live_renderer/windows/ui_editor_window.hpp"

using namespace live_renderer;

TEST(UIEditorWindowTest, NavigationBetweenWindows) {
    UIConfig ui;
    WindowConfig w1{1, "Window 1", {0, 0, 800, 600}};
    WindowConfig w2{2, "Window 2", {100, 100, 1024, 768}};
    WindowConfig w3{3, "Window 3", {200, 200, 1920, 1080}};
    ui.windows = {w1, w2, w3};

    UIEditorWindow editor(ui);
    EXPECT_EQ(editor.GetActiveWindowIndex(), 0);

    editor.ClickNextWindow();
    EXPECT_EQ(editor.GetActiveWindowIndex(), 1);

    editor.ClickNextWindow();
    EXPECT_EQ(editor.GetActiveWindowIndex(), 2);

    // Wraps around
    editor.ClickNextWindow();
    EXPECT_EQ(editor.GetActiveWindowIndex(), 0);

    editor.ClickPreviousWindow();
    EXPECT_EQ(editor.GetActiveWindowIndex(), 2);
}

TEST(UIEditorWindowTest, CreatingNewWindow) {
    UIConfig ui;
    UIEditorWindow editor(ui);
    size_t initial_count = ui.windows.size();

    editor.ClickNewWindow();
    EXPECT_TRUE(editor.IsNewWindowModalOpen());

    EXPECT_FALSE(editor.ConfirmNewWindow("")); // Empty title rejected
    EXPECT_TRUE(editor.IsNewWindowModalOpen());

    EXPECT_TRUE(editor.ConfirmNewWindow("Arena Scoreboard Window"));
    EXPECT_FALSE(editor.IsNewWindowModalOpen());
    EXPECT_EQ(ui.windows.size(), initial_count + 1);
    EXPECT_EQ(editor.GetActiveWindowIndex(), static_cast<int>(ui.windows.size() - 1));
    EXPECT_EQ(ui.windows.back().title, "Arena Scoreboard Window");
}

TEST(UIEditorWindowTest, TemplateEditingModeLifecycle) {
    UIConfig ui;
    TemplateConfig tmpl;
    tmpl.id = 10;
    tmpl.name = "My Scorecard Row";
    tmpl.type = "scorecard_row";
    ui.templates.push_back(tmpl);

    UIEditorWindow editor(ui);
    EXPECT_FALSE(editor.IsEditingTemplate());
    EXPECT_EQ(editor.GetSelectedTemplateId(), -1);

    // Enter template editing mode
    editor.SelectTemplateForEditing(10);
    EXPECT_TRUE(editor.IsEditingTemplate());
    EXPECT_EQ(editor.GetSelectedTemplateId(), 10);

    // In template editing mode, window cycling should be disabled (no-op)
    int win_idx = editor.GetActiveWindowIndex();
    editor.ClickNextWindow();
    EXPECT_EQ(editor.GetActiveWindowIndex(), win_idx);

    // Creating window should be disabled in template editing mode
    editor.ClickNewWindow();
    EXPECT_FALSE(editor.IsNewWindowModalOpen());

    // Done with template returns to window view
    editor.DoneWithTemplate();
    EXPECT_FALSE(editor.IsEditingTemplate());
    EXPECT_EQ(editor.GetSelectedTemplateId(), -1);
}

TEST(UIEditorWindowTest, CreatingNewTemplateEntersTemplateMode) {
    UIConfig ui;
    UIEditorWindow editor(ui);

    editor.ClickNewTemplate();
    EXPECT_TRUE(editor.IsNewTemplateModalOpen());

    EXPECT_FALSE(editor.ConfirmNewTemplate("", "scorecard_row"));
    EXPECT_TRUE(editor.IsNewTemplateModalOpen());

    EXPECT_TRUE(editor.ConfirmNewTemplate("Header Template", "scorecard_header_row"));
    EXPECT_FALSE(editor.IsNewTemplateModalOpen());
    ASSERT_EQ(ui.templates.size(), 1u);
    EXPECT_EQ(ui.templates[0].name, "Header Template");
    EXPECT_EQ(ui.templates[0].type, "scorecard_header_row");
    EXPECT_TRUE(editor.IsEditingTemplate());
    EXPECT_EQ(editor.GetSelectedTemplateId(), ui.templates[0].id);
}

TEST(UIEditorWindowTest, AddElementRespectsContext) {
    UIConfig ui;
    TemplateConfig tmpl;
    tmpl.id = 1;
    tmpl.name = "Player Row";
    tmpl.type = "scorecard_row";
    ui.templates.push_back(tmpl);

    UIEditorWindow editor(ui);

    // Top-level context
    auto top_types = editor.GetAvailableElementTypes();
    EXPECT_FALSE(top_types.empty());
    bool has_game_timer = false;
    for (const auto& t : top_types) {
        if (t == "game_timer") has_game_timer = true;
    }
    EXPECT_TRUE(has_game_timer);

    editor.ClickAddElement();
    EXPECT_TRUE(editor.IsAddElementModalOpen());
    EXPECT_TRUE(editor.ConfirmAddElement("game_timer"));
    EXPECT_FALSE(editor.IsAddElementModalOpen());
    ASSERT_FALSE(ui.windows[editor.GetActiveWindowIndex()].elements.empty());
    EXPECT_EQ(ui.windows[editor.GetActiveWindowIndex()].elements.back().type, "game_timer");

    // Switch to scorecard_row template context
    editor.SelectTemplateForEditing(1);
    auto tmpl_types = editor.GetAvailableElementTypes();
    bool has_player_lives = false;
    for (const auto& t : tmpl_types) {
        if (t == "player_lives") has_player_lives = true;
    }
    EXPECT_TRUE(has_player_lives);

    editor.ClickAddElement();
    EXPECT_TRUE(editor.ConfirmAddElement("player_lives"));
    ASSERT_FALSE(ui.templates[0].elements.empty());
    EXPECT_EQ(ui.templates[0].elements.back().type, "player_lives");
}

TEST(UIEditorWindowTest, SaveAndBackPersistsConfigFile) {
    std::string test_ui_path = "test_ui_editor_save.yaml";
    UIConfig ui;
    WindowConfig w{1, "Saved Window", {0, 0, 1920, 1080}};
    ui.windows.push_back(w);

    bool callback_called = false;
    UIEditorWindow editor(ui, test_ui_path);
    UIEditorWindow::Callbacks cbs;
    cbs.on_save_and_back = [&]() { callback_called = true; };
    editor.SetCallbacks(cbs);

    EXPECT_TRUE(editor.ClickSaveAndBack());
    EXPECT_TRUE(callback_called);

    UIConfig loaded;
    EXPECT_TRUE(ConfigSerializer::LoadUIConfig(test_ui_path, loaded));
    ASSERT_FALSE(loaded.windows.empty());
    EXPECT_EQ(loaded.windows[0].title, "Saved Window");

    std::filesystem::remove(test_ui_path);
}

TEST(UIEditorWindowTest, SaveAndExitPersistsConfigFile) {
    std::string test_ui_path = "test_ui_editor_save_exit.yaml";
    UIConfig ui;
    WindowConfig w{1, "Exit Saved Window", {0, 0, 1920, 1080}};
    ui.windows.push_back(w);

    bool callback_called = false;
    UIEditorWindow editor(ui, test_ui_path);
    UIEditorWindow::Callbacks cbs;
    cbs.on_save_and_back = [&]() { callback_called = true; };
    editor.SetCallbacks(cbs);

    EXPECT_TRUE(editor.ClickSaveAndExit());
    EXPECT_TRUE(callback_called);

    UIConfig loaded;
    EXPECT_TRUE(ConfigSerializer::LoadUIConfig(test_ui_path, loaded));
    ASSERT_FALSE(loaded.windows.empty());
    EXPECT_EQ(loaded.windows[0].title, "Exit Saved Window");

    std::filesystem::remove(test_ui_path);
}

TEST(UIEditorWindowTest, SaveAndExitFromTemplateModeExitsTemplateAndPersists) {
    std::string test_ui_path = "test_ui_editor_template_exit.yaml";
    UIConfig ui;
    TemplateConfig t;
    t.id = 5;
    t.name = "MyTmpl";
    t.type = "player_profile";
    ui.templates.push_back(t);

    bool callback_called = false;
    UIEditorWindow editor(ui, test_ui_path);
    UIEditorWindow::Callbacks cbs;
    cbs.on_save_and_back = [&]() { callback_called = true; };
    editor.SetCallbacks(cbs);

    editor.SelectTemplateForEditing(5);
    EXPECT_TRUE(editor.IsEditingTemplate());

    EXPECT_TRUE(editor.SaveAndExit());
    EXPECT_FALSE(editor.IsEditingTemplate());
    EXPECT_TRUE(callback_called);

    UIConfig loaded;
    EXPECT_TRUE(ConfigSerializer::LoadUIConfig(test_ui_path, loaded));
    ASSERT_FALSE(loaded.templates.empty());
    EXPECT_EQ(loaded.templates[0].name, "MyTmpl");

    std::filesystem::remove(test_ui_path);
}

TEST(UIEditorWindowTest, SelectElementAndInspectProperties) {
    UIConfig ui;
    UIEditorWindow editor(ui);

    EXPECT_EQ(editor.GetSelectedElementIndex(), -1);
    EXPECT_EQ(editor.GetSelectedElement(), nullptr);

    editor.ClickAddElement();
    EXPECT_TRUE(editor.ConfirmAddElement("user_text"));
    EXPECT_EQ(editor.GetSelectedElementIndex(), 0);

    auto* el = editor.GetSelectedElement();
    ASSERT_NE(el, nullptr);
    EXPECT_EQ(el->type, "user_text");

    // Modify properties
    el->text = "Live Match Countdown";
    el->font_size = 36.0f;
    el->color = "#ff8800";
    el->rect = {0.1f, 0.2f, 0.5f, 0.15f};

    // Verify properties updated on underlying window element
    const auto& active_win_elems = ui.windows[editor.GetActiveWindowIndex()].elements;
    ASSERT_EQ(active_win_elems.size(), 1u);
    EXPECT_EQ(active_win_elems[0].text, "Live Match Countdown");
    EXPECT_FLOAT_EQ(active_win_elems[0].font_size, 36.0f);
    EXPECT_EQ(active_win_elems[0].color, "#ff8800");
    EXPECT_FLOAT_EQ(active_win_elems[0].rect[0], 0.1f);
}

TEST(UIEditorWindowTest, DeleteAndReorderElements) {
    UIConfig ui;
    UIEditorWindow editor(ui);

    editor.ClickAddElement();
    editor.ConfirmAddElement("user_text");     // Index 0
    editor.ClickAddElement();
    editor.ConfirmAddElement("game_timer");    // Index 1
    editor.ClickAddElement();
    editor.ConfirmAddElement("team_scorecard");// Index 2

    ASSERT_EQ(editor.GetActiveElements().size(), 3u);
    EXPECT_EQ(editor.GetSelectedElementIndex(), 2);

    // Select index 1 (game_timer)
    editor.SetSelectedElementIndex(1);
    EXPECT_EQ(editor.GetSelectedElementIndex(), 1);
    EXPECT_EQ(editor.GetSelectedElement()->type, "game_timer");

    // Move Up: swaps with index 0
    editor.MoveSelectedElementUp();
    EXPECT_EQ(editor.GetSelectedElementIndex(), 0);
    EXPECT_EQ(editor.GetActiveElements()[0].type, "game_timer");
    EXPECT_EQ(editor.GetActiveElements()[1].type, "user_text");

    // Move Down: swaps back with index 1
    editor.MoveSelectedElementDown();
    EXPECT_EQ(editor.GetSelectedElementIndex(), 1);
    EXPECT_EQ(editor.GetActiveElements()[1].type, "game_timer");

    // Delete selected element (game_timer)
    editor.DeleteSelectedElement();
    ASSERT_EQ(editor.GetActiveElements().size(), 2u);
    EXPECT_EQ(editor.GetActiveElements()[0].type, "user_text");
    EXPECT_EQ(editor.GetActiveElements()[1].type, "team_scorecard");
    // Selection stays within bounds
    EXPECT_EQ(editor.GetSelectedElementIndex(), 1);

    // Delete remaining elements
    editor.DeleteSelectedElement();
    editor.DeleteSelectedElement();
    EXPECT_TRUE(editor.GetActiveElements().empty());
    EXPECT_EQ(editor.GetSelectedElementIndex(), -1);
    EXPECT_EQ(editor.GetSelectedElement(), nullptr);
}

TEST(UIEditorWindowTest, TemplateModeActiveElementsAndResetSelection) {
    UIConfig ui;
    TemplateConfig tmpl;
    tmpl.id = 5;
    tmpl.name = "Custom Row";
    tmpl.type = "scorecard_row";
    ui.templates.push_back(tmpl);

    UIEditorWindow editor(ui);
    editor.ClickAddElement();
    editor.ConfirmAddElement("user_text");
    EXPECT_EQ(editor.GetSelectedElementIndex(), 0);

    // Enter template mode: selection should reset to -1
    editor.SelectTemplateForEditing(5);
    EXPECT_TRUE(editor.IsEditingTemplate());
    EXPECT_EQ(editor.GetSelectedElementIndex(), -1);
    EXPECT_TRUE(editor.GetActiveElements().empty());

    // Add element into template
    editor.ClickAddElement();
    EXPECT_TRUE(editor.ConfirmAddElement("player_score"));
    EXPECT_EQ(editor.GetSelectedElementIndex(), 0);
    ASSERT_EQ(editor.GetActiveElements().size(), 1u);
    EXPECT_EQ(editor.GetActiveElements()[0].type, "player_score");

    // Done with template mode: selection should reset to -1, active elements reverts to window
    editor.DoneWithTemplate();
    EXPECT_FALSE(editor.IsEditingTemplate());
    EXPECT_EQ(editor.GetSelectedElementIndex(), -1);
    ASSERT_EQ(editor.GetActiveElements().size(), 1u);
    EXPECT_EQ(editor.GetActiveElements()[0].type, "user_text");
}
TEST(UIEditorWindowTest, RenderImGuiAfterCreatingTemplate) {
    IMGUI_CHECKVERSION();
    ImGuiContext* ctx = ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.DisplaySize = ImVec2(800.0f, 600.0f);

    unsigned char* pixels;
    int width, height;
    io.Fonts->GetTexDataAsRGBA32(&pixels, &width, &height);

    UIConfig ui;
    WindowConfig w1{1, "Window 1", {0, 0, 800, 600}};
    ui.windows = {w1};

    UIEditorWindow editor(ui);

    // Frame 1: Normal editor
    ImGui::NewFrame();
    editor.RenderImGui();
    ImGui::Render();

    // Frame 2: Click new template
    editor.ClickNewTemplate();
    ImGui::NewFrame();
    editor.RenderImGui();
    ImGui::Render();

    // Frame 3: Confirm new template
    EXPECT_TRUE(editor.ConfirmNewTemplate("Template 1", "scorecard_row"));
    ImGui::NewFrame();
    editor.RenderImGui();
    ImGui::Render();

    // Frame 4: Next frame in template mode
    ImGui::NewFrame();
    editor.RenderImGui();
    ImGui::Render();

    ImGui::DestroyContext(ctx);
}

TEST(UIEditorWindowTest, EditTemplateWidthAndHeight) {
    UIConfig ui;
    TemplateConfig tmpl;
    tmpl.id = 1;
    tmpl.name = "Profile Template";
    tmpl.type = "player_profile";
    tmpl.size = {0.25f, 0.40f};
    ui.templates.push_back(tmpl);

    UIEditorWindow editor(ui);
    EXPECT_EQ(editor.GetActiveTemplate(), nullptr);
    EXPECT_FLOAT_EQ(editor.GetActiveTemplateSize()[0], 0.0f);

    editor.SelectTemplateForEditing(1);
    EXPECT_TRUE(editor.IsEditingTemplate());
    ASSERT_NE(editor.GetActiveTemplate(), nullptr);
    EXPECT_FLOAT_EQ(editor.GetActiveTemplateSize()[0], 0.25f);
    EXPECT_FLOAT_EQ(editor.GetActiveTemplateSize()[1], 0.40f);

    editor.SetActiveTemplateSize(0.30f, 0.50f);
    EXPECT_FLOAT_EQ(editor.GetActiveTemplateSize()[0], 0.30f);
    EXPECT_FLOAT_EQ(editor.GetActiveTemplateSize()[1], 0.50f);
    EXPECT_FLOAT_EQ(editor.GetActiveTemplate()->size[0], 0.30f);
    EXPECT_FLOAT_EQ(editor.GetActiveTemplate()->size[1], 0.50f);

    // Clamping to positive minimum
    editor.SetActiveTemplateSize(-1.0f, 0.0f);
    EXPECT_GE(editor.GetActiveTemplateSize()[0], 0.001f);
    EXPECT_GE(editor.GetActiveTemplateSize()[1], 0.001f);

    editor.DoneWithTemplate();
    EXPECT_FALSE(editor.IsEditingTemplate());
    EXPECT_EQ(editor.GetActiveTemplate(), nullptr);
}
