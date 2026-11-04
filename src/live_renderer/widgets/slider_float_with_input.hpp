/**
 * @file slider_float_with_input.hpp
 * @brief Custom ImGui widget pairing a float slider with a numeric text field.
 *
 * Provides a composite control combining an interactive slider with a direct
 * numeric input field and an optional unit suffix label placed outside.
 *
 * Example:
 * @code
 *   live_renderer::SliderFloatWithInput::Render(
 *       "Tilt Angle", &element.tilt, -45.0f, 45.0f, "deg");
 * @endcode
 */

#ifndef LIVE_RENDERER_WIDGETS_SLIDER_FLOAT_WITH_INPUT_HPP_
#define LIVE_RENDERER_WIDGETS_SLIDER_FLOAT_WITH_INPUT_HPP_

namespace live_renderer {

/**
 * @brief Custom UI widget with paired slider and direct float text input.
 *
 * Allows users to adjust floating point values either by dragging a horizontal
 * slider or by directly entering numbers in a text entry box without any unit
 * suffix interfering with typing.
 */
class SliderFloatWithInput {
public:
    SliderFloatWithInput() = default;
    ~SliderFloatWithInput() = default;

    /**
     * @brief Renders the slider and text input combo in the current layout.
     *
     * Displays a descriptive label, a slider for visual adjustment, a dedicated
     * float input field, and an external unit label (such as "deg").
     *
     * @param label The descriptive label displayed above the control.
     * @param value Pointer to the float value to view and modify.
     * @param v_min Minimum range value for the slider.
     * @param v_max Maximum range value for the slider.
     * @param unit_suffix Optional unit string rendered outside the text box.
     * @return True if value was modified during this frame, false otherwise.
     */
    static bool Render(
        const char* label,
        float* value,
        float v_min,
        float v_max,
        const char* unit_suffix = nullptr);
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_WIDGETS_SLIDER_FLOAT_WITH_INPUT_HPP_

