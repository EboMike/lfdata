/**
 * @file ui_editor_interaction.cpp
 * @brief Implementation of UIEditorInteraction.
 */

#include "live_renderer/windows/ui_editor_interaction.hpp"
#include <algorithm>

namespace live_renderer {

bool UIEditorInteraction::IsPointInRect(
    float px,
    float py,
    const std::array<float, 4>& rect_px) {
    return (px >= rect_px[0] &&
            px <= rect_px[0] + rect_px[2] &&
            py >= rect_px[1] &&
            py <= rect_px[1] + rect_px[3]);
}

bool UIEditorInteraction::IsPointInResizeHandle(
    float px,
    float py,
    const std::array<float, 4>& rect_px,
    float handle_size) {
    const float right = rect_px[0] + rect_px[2];
    const float bottom = rect_px[1] + rect_px[3];
    constexpr float kOuterMargin = 4.0f;

    return (px >= right - handle_size &&
            px <= right + kOuterMargin &&
            py >= bottom - handle_size &&
            py <= bottom + kOuterMargin);
}

int UIEditorInteraction::FindHitElementIndex(
    float px,
    float py,
    const std::vector<ElementConfig>& elements,
    int win_w,
    int win_h) {
    if (win_w <= 0 || win_h <= 0 || elements.empty()) {
        return -1;
    }

    // Sort element indices by z_position ascending (render order)
    std::vector<size_t> ordered_indices;
    ordered_indices.reserve(elements.size());
    for (size_t i = 0; i < elements.size(); ++i) {
        ordered_indices.push_back(i);
    }
    std::stable_sort(
        ordered_indices.begin(),
        ordered_indices.end(),
        [&elements](size_t a, size_t b) {
            return elements[a].z_position < elements[b].z_position;
        });

    // Check from top to bottom (highest Z on top)
    for (auto it = ordered_indices.rbegin(); it != ordered_indices.rend(); ++it) {
        const size_t idx = *it;
        const auto& el = elements[idx];
        const std::array<float, 4> rect_px{
            el.rect[0] * static_cast<float>(win_w),
            el.rect[1] * static_cast<float>(win_h),
            el.rect[2] * static_cast<float>(win_w),
            el.rect[3] * static_cast<float>(win_h)
        };

        if (IsPointInRect(px, py, rect_px)) {
            return static_cast<int>(idx);
        }
    }

    return -1;
}

bool UIEditorInteraction::HandleMouseDown(
    int mouse_x,
    int mouse_y,
    int win_w,
    int win_h,
    std::vector<ElementConfig>& elements,
    int& in_out_selected_index) {
    if (win_w <= 0 || win_h <= 0 || elements.empty()) {
        drag_mode_ = DragMode::None;
        return false;
    }

    const float mx = static_cast<float>(mouse_x);
    const float my = static_cast<float>(mouse_y);

    // 1. If an element is already selected and covers mouse, keep selection and drag it
    if (in_out_selected_index >= 0 &&
        in_out_selected_index < static_cast<int>(elements.size())) {
        const auto& sel_el = elements[in_out_selected_index];
        const std::array<float, 4> sel_px{
            sel_el.rect[0] * static_cast<float>(win_w),
            sel_el.rect[1] * static_cast<float>(win_h),
            sel_el.rect[2] * static_cast<float>(win_w),
            sel_el.rect[3] * static_cast<float>(win_h)
        };

        if (IsPointInResizeHandle(mx, my, sel_px)) {
            drag_mode_ = DragMode::Resize;
            return true;
        }

        if (IsPointInRect(mx, my, sel_px)) {
            drag_mode_ = DragMode::Move;
            drag_offset_x_ = mx - sel_px[0];
            drag_offset_y_ = my - sel_px[1];
            return true;
        }
    }

    // 2. If there isn't already one selected at the position, clicking will select it
    int hit = FindHitElementIndex(mx, my, elements, win_w, win_h);
    if (hit >= 0) {
        in_out_selected_index = hit;
        const auto& hit_el = elements[hit];
        const float el_x = hit_el.rect[0] * static_cast<float>(win_w);
        const float el_y = hit_el.rect[1] * static_cast<float>(win_h);

        drag_mode_ = DragMode::Move;
        drag_offset_x_ = mx - el_x;
        drag_offset_y_ = my - el_y;
        return true;
    }

    drag_mode_ = DragMode::None;
    return false;
}

bool UIEditorInteraction::HandleMouseMove(
    int mouse_x,
    int mouse_y,
    int win_w,
    int win_h,
    std::vector<ElementConfig>& elements,
    int selected_index) {
    if (drag_mode_ == DragMode::None || win_w <= 0 || win_h <= 0) {
        return false;
    }
    if (selected_index < 0 || selected_index >= static_cast<int>(elements.size())) {
        drag_mode_ = DragMode::None;
        return false;
    }

    auto& el = elements[selected_index];
    const float mx = static_cast<float>(mouse_x);
    const float my = static_cast<float>(mouse_y);
    const float fw = static_cast<float>(win_w);
    const float fh = static_cast<float>(win_h);

    if (drag_mode_ == DragMode::Move) {
        float new_px_x = mx - drag_offset_x_;
        float new_px_y = my - drag_offset_y_;

        float rel_w = el.rect[2];
        float rel_h = el.rect[3];
        float rel_x = new_px_x / fw;
        float rel_y = new_px_y / fh;

        rel_x = std::clamp(rel_x, 0.0f, std::max(0.0f, 1.0f - rel_w));
        rel_y = std::clamp(rel_y, 0.0f, std::max(0.0f, 1.0f - rel_h));

        el.rect[0] = rel_x;
        el.rect[1] = rel_y;
        return true;
    }

    if (drag_mode_ == DragMode::Resize) {
        float el_px_x = el.rect[0] * fw;
        float el_px_y = el.rect[1] * fh;

        float new_px_w = mx - el_px_x;
        float new_px_h = my - el_px_y;

        constexpr float kMinPx = 10.0f;
        new_px_w = std::max(kMinPx, new_px_w);
        new_px_h = std::max(kMinPx, new_px_h);

        float rel_w = new_px_w / fw;
        float rel_h = new_px_h / fh;

        rel_w = std::clamp(rel_w, 0.01f, 1.0f - el.rect[0]);
        rel_h = std::clamp(rel_h, 0.01f, 1.0f - el.rect[1]);

        el.rect[2] = rel_w;
        el.rect[3] = rel_h;
        return true;
    }

    return false;
}

bool UIEditorInteraction::HandleMouseUp(int, int) {
    if (drag_mode_ != DragMode::None) {
        drag_mode_ = DragMode::None;
        return true;
    }
    return false;
}

bool UIEditorInteraction::HandleSdlEvent(
    const SDL_Event& event,
    int win_w,
    int win_h,
    std::vector<ElementConfig>& elements,
    int& in_out_selected_index) {
    switch (event.type) {
        case SDL_MOUSEBUTTONDOWN:
            if (event.button.button == SDL_BUTTON_LEFT) {
                return HandleMouseDown(
                    event.button.x, event.button.y,
                    win_w, win_h,
                    elements, in_out_selected_index);
            }
            break;

        case SDL_MOUSEMOTION:
            if (event.motion.state & SDL_BUTTON_LMASK) {
                return HandleMouseMove(
                    event.motion.x, event.motion.y,
                    win_w, win_h,
                    elements, in_out_selected_index);
            }
            break;

        case SDL_MOUSEBUTTONUP:
            if (event.button.button == SDL_BUTTON_LEFT) {
                return HandleMouseUp(event.button.x, event.button.y);
            }
            break;

        default:
            break;
    }
    return false;
}

}  // namespace live_renderer

