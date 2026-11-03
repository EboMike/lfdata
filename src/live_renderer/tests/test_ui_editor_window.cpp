#include <gtest/gtest.h>
#include <filesystem>
#include "live_renderer/config/config_serializer.hpp"
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

