/**
 * @file test_list_animation_tracker.cpp
 * @brief Unit tests for ListAnimationTracker list reordering animations.
 */

#include <gtest/gtest.h>
#include "live_renderer/components/list_animation_tracker.hpp"

namespace live_renderer {

TEST(ListAnimationTrackerTest, ParsesAnimationTypesCorrectly) {
    EXPECT_EQ(
        ListAnimationTracker::ParseAnimationType("linear"),
        ListAnimationType::Linear);
    EXPECT_EQ(
        ListAnimationTracker::ParseAnimationType("Linear"),
        ListAnimationType::Linear);
    EXPECT_EQ(
        ListAnimationTracker::ParseAnimationType("ease-in-and-ease-out"),
        ListAnimationType::EaseInOut);
    EXPECT_EQ(
        ListAnimationTracker::ParseAnimationType("Ease-in-and-ease-out"),
        ListAnimationType::EaseInOut);
    EXPECT_EQ(
        ListAnimationTracker::ParseAnimationType("none"),
        ListAnimationType::None);
    EXPECT_EQ(
        ListAnimationTracker::ParseAnimationType(""),
        ListAnimationType::None);
}

TEST(ListAnimationTrackerTest, InitialPositionHasNoJump) {
    ListAnimationTracker tracker;
    float pos = tracker.GetAnimatedPosition(
        "scorecard", 101, 250.0f, 1000, "linear", 0.5f);
    EXPECT_FLOAT_EQ(pos, 250.0f);
}

TEST(ListAnimationTrackerTest, NoneAnimationSnapsImmediately) {
    ListAnimationTracker tracker;
    tracker.GetAnimatedPosition("scorecard", 101, 100.0f, 1000, "none", 0.5f);
    float updated = tracker.GetAnimatedPosition(
        "scorecard", 101, 200.0f, 1100, "none", 0.5f);
    EXPECT_FLOAT_EQ(updated, 200.0f);
}

TEST(ListAnimationTrackerTest, LinearInterpolation) {
    ListAnimationTracker tracker;
    // Initial position established at t=0
    tracker.GetAnimatedPosition(
        "scorecard", 101, 100.0f, 0, "linear", 1.0f);

    // Target changes at t=1000 to 200.0f with 1.0s duration
    float start = tracker.GetAnimatedPosition(
        "scorecard", 101, 200.0f, 1000, "linear", 1.0f);
    EXPECT_FLOAT_EQ(start, 100.0f);

    // 25% (t=1250)
    float p25 = tracker.GetAnimatedPosition(
        "scorecard", 101, 200.0f, 1250, "linear", 1.0f);
    EXPECT_NEAR(p25, 125.0f, 0.5f);

    // 50% (t=1500)
    float p50 = tracker.GetAnimatedPosition(
        "scorecard", 101, 200.0f, 1500, "linear", 1.0f);
    EXPECT_NEAR(p50, 150.0f, 0.5f);

    // 100% (t=2000)
    float p100 = tracker.GetAnimatedPosition(
        "scorecard", 101, 200.0f, 2000, "linear", 1.0f);
    EXPECT_FLOAT_EQ(p100, 200.0f);

    // After completion
    float past = tracker.GetAnimatedPosition(
        "scorecard", 101, 200.0f, 2500, "linear", 1.0f);
    EXPECT_FLOAT_EQ(past, 200.0f);
}

TEST(ListAnimationTrackerTest, EaseInOutInterpolation) {
    ListAnimationTracker tracker;
    tracker.GetAnimatedPosition(
        "scorecard", 101, 0.0f, 0, "ease-in-and-ease-out", 1.0f);

    // Change target at t=1000 to 100.0f
    float start = tracker.GetAnimatedPosition(
        "scorecard", 101, 100.0f, 1000, "ease-in-and-ease-out", 1.0f);
    EXPECT_FLOAT_EQ(start, 0.0f);

    // Midpoint at 50% must be exactly 50.0f for symmetric ease-in-out
    float p50 = tracker.GetAnimatedPosition(
        "scorecard", 101, 100.0f, 1500, "ease-in-and-ease-out", 1.0f);
    EXPECT_NEAR(p50, 50.0f, 0.5f);

    // At 25%, ease-in should be slower than linear (< 25.0f)
    float p25 = tracker.GetAnimatedPosition(
        "scorecard", 101, 100.0f, 1250, "ease-in-and-ease-out", 1.0f);
    EXPECT_LT(p25, 25.0f);

    // At 75%, ease-out should be faster than linear (> 75.0f)
    float p75 = tracker.GetAnimatedPosition(
        "scorecard", 101, 100.0f, 1750, "ease-in-and-ease-out", 1.0f);
    EXPECT_GT(p75, 75.0f);
}

TEST(ListAnimationTrackerTest, ConsecutiveReorderingMidAnimation) {
    ListAnimationTracker tracker;
    // Initial at 100
    tracker.GetAnimatedPosition("scorecard", 101, 100.0f, 0, "linear", 1.0f);

    // Reorders to 200 at t=1000
    tracker.GetAnimatedPosition("scorecard", 101, 200.0f, 1000, "linear", 1.0f);

    // At t=1500, pos is ~150
    float mid = tracker.GetAnimatedPosition(
        "scorecard", 101, 200.0f, 1500, "linear", 1.0f);
    EXPECT_NEAR(mid, 150.0f, 0.5f);

    // Mid-animation re-orders to 50 at t=1500
    // Should transition smoothly from ~150 toward 50 over the new duration
    float redirect_start = tracker.GetAnimatedPosition(
        "scorecard", 101, 50.0f, 1500, "linear", 1.0f);
    EXPECT_NEAR(redirect_start, 150.0f, 1.0f);
}

}  // namespace live_renderer

