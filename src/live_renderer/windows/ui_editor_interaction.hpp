/**
 * @file ui_editor_interaction.hpp
 * @brief Handles mouse interaction (selection, moving, resizing) in the UI editor.
 *
 * Provides hit testing, element selection, move dragging, and bottom-right corner
 * resize dragging for visualization windows during UI Editor Mode.
 *
 * Usage example:
 * @code
 * live_renderer::UIEditorInteraction interaction;
 * int selected_index = -1;
 * interaction.HandleMouseDown(150, 120, 1280, 720, elements, selected_index);
 * interaction.HandleMouseMove(180, 140, 1280, 720, elements, selected_index);
 * interaction.HandleMouseUp(180, 140);
 * @endcode
 */

#ifndef LIVE_RENDERER_WINDOWS_UI_EDITOR_INTERACTION_HPP_
#define LIVE_RENDERER_WINDOWS_UI_EDITOR_INTERACTION_HPP_

#include <array>
#include <vector>
#include <SDL.h>
#include "live_renderer/config/ui_config.hpp"

namespace live_renderer {

/**
 * @brief Current drag interaction mode.
 */
enum class DragMode {
    None,
    Move,
    Resize
};

/**
 * @brief Manages element selection, moving, and resizing via mouse in UI editor.
 *
 * Intercepts SDL mouse events, computes pixel-to-relative coordinate translations,
 * and updates element bounding boxes during interactive drag operations.
 */
class UIEditorInteraction {
public:
    UIEditorInteraction() = default;
    ~UIEditorInteraction() = default;

    /**
     * @brief Gets the current drag mode.
     *
     * Returns whether the user is actively moving, resizing, or idle.
     *
     * @return Current DragMode enum value.
     */
    DragMode GetDragMode() const { return drag_mode_; }

    /**
     * @brief Handles mouse button press at given pixel coordinates.
     *
     * If clicking on the bottom-right corner of the currently selected element,
     * begins resize drag. If clicking inside the currently selected element,
     * begins move drag. Otherwise, selects the element under the cursor (if any)
     * and begins move drag.
     *
     * @param mouse_x Horizontal pixel coordinate in window.
     * @param mouse_y Vertical pixel coordinate in window.
     * @param win_w Window width in pixels.
     * @param win_h Window height in pixels.
     * @param elements Vector of elements to test and manipulate.
     * @param in_out_selected_index In/out index of currently selected element.
     * @return True if an element was clicked or drag began, false otherwise.
     */
    bool HandleMouseDown(
        int mouse_x,
        int mouse_y,
        int win_w,
        int win_h,
        std::vector<ElementConfig>& elements,
        int& in_out_selected_index);

    /**
     * @brief Handles mouse motion during an active drag operation.
     *
     * Updates the position or size of the currently selected element based
     * on active DragMode.
     *
     * @param mouse_x Current horizontal pixel coordinate.
     * @param mouse_y Current vertical pixel coordinate.
     * @param win_w Window width in pixels.
     * @param win_h Window height in pixels.
     * @param elements Vector of elements containing the selected element.
     * @param selected_index Index of the currently selected element.
     * @return True if element geometry changed, false otherwise.
     */
    bool HandleMouseMove(
        int mouse_x,
        int mouse_y,
        int win_w,
        int win_h,
        std::vector<ElementConfig>& elements,
        int selected_index);

    /**
     * @brief Handles mouse button release.
     *
     * Concludes any active move or resize drag operation.
     *
     * @param mouse_x Horizontal pixel coordinate on release.
     * @param mouse_y Vertical pixel coordinate on release.
     * @return True if an active drag was concluded, false otherwise.
     */
    bool HandleMouseUp(int mouse_x, int mouse_y);

    /**
     * @brief Processes an SDL event for UI editor mouse interactions.
     *
     * Dispatches SDL_MOUSEBUTTONDOWN, SDL_MOUSEMOTION, and SDL_MOUSEBUTTONUP.
     *
     * @param event SDL_Event to inspect and handle.
     * @param win_w Window width in pixels.
     * @param win_h Window height in pixels.
     * @param elements Vector of elements to test and manipulate.
     * @param in_out_selected_index In/out index of currently selected element.
     * @return True if event was handled, false otherwise.
     */
    bool HandleSdlEvent(
        const SDL_Event& event,
        int win_w,
        int win_h,
        std::vector<ElementConfig>& elements,
        int& in_out_selected_index);

    /**
     * @brief Tests if a point lies within a pixel bounding box.
     *
     * @param px X coordinate of point.
     * @param py Y coordinate of point.
     * @param rect_px Pixel rectangle [x, y, width, height].
     * @return True if point is inside rectangle, false otherwise.
     */
    static bool IsPointInRect(
        float px,
        float py,
        const std::array<float, 4>& rect_px);

    /**
     * @brief Tests if a point lies in the bottom-right resize handle region.
     *
     * @param px X coordinate of point.
     * @param py Y coordinate of point.
     * @param rect_px Pixel rectangle [x, y, width, height].
     * @param handle_size Size of the square handle in pixels.
     * @return True if point is inside resize handle, false otherwise.
     */
    static bool IsPointInResizeHandle(
        float px,
        float py,
        const std::array<float, 4>& rect_px,
        float handle_size = 16.0f);

    /**
     * @brief Finds the topmost element covering the given pixel coordinate.
     *
     * Evaluates elements in visual render order (highest Z-position on top).
     *
     * @param px X coordinate in pixels.
     * @param py Y coordinate in pixels.
     * @param elements Vector of elements.
     * @param win_w Window width in pixels.
     * @param win_h Window height in pixels.
     * @return Index of topmost hit element, or -1 if none hit.
     */
    static int FindHitElementIndex(
        float px,
        float py,
        const std::vector<ElementConfig>& elements,
        int win_w,
        int win_h);

private:
    DragMode drag_mode_ = DragMode::None;
    float drag_offset_x_ = 0.0f;
    float drag_offset_y_ = 0.0f;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_UI_EDITOR_INTERACTION_HPP_

