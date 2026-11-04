#ifndef LIVE_RENDERER_WINDOWS_ELEMENT_PROPERTY_INSPECTOR_HPP_
#define LIVE_RENDERER_WINDOWS_ELEMENT_PROPERTY_INSPECTOR_HPP_

#include <functional>
#include <string>
#include "live_renderer/config/ui_config.hpp"

namespace live_renderer {

/**
 * @brief Property inspector component for viewing and modifying ElementConfig properties.
 *
 * Renders Dear ImGui widgets for element position, typography, colors, asset paths,
 * scorecard/roster layout options, and element deletion/reordering callbacks.
 */
class ElementPropertyInspector {
public:
    struct Callbacks {
        std::function<void()> on_delete;
        std::function<void()> on_move_up;
        std::function<void()> on_move_down;
    };

    ElementPropertyInspector() = default;
    ~ElementPropertyInspector() = default;

    /**
     * @brief Renders the property inspector UI for the given element.
     * @param element Reference to the ElementConfig being inspected and edited.
     * @param ui_config Const reference to UIConfig (used to populate template dropdowns).
     * @param callbacks Actions for element deletion and reordering.
     */
    void Render(
        ElementConfig& element,
        const UIConfig& ui_config,
        const Callbacks& callbacks = {});

private:
    void RenderHeaderAndActions(
        const ElementConfig& element,
        const Callbacks& callbacks);

    void RenderGeometryControls(ElementConfig& element);
    void RenderTextControls(ElementConfig& element);
    void RenderImageControls(ElementConfig& element);
    void RenderMovieControls(ElementConfig& element);
    void RenderScorecardControls(ElementConfig& element, const UIConfig& ui_config);
    void RenderBackgroundControls(ElementConfig& element);
    void RenderScrollerControls(ElementConfig& element);
    void RenderMessagesDisplayControls(ElementConfig& element);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WINDOWS_ELEMENT_PROPERTY_INSPECTOR_HPP_

