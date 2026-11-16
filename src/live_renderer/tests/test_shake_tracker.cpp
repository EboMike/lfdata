#include <gtest/gtest.h>
#include <cmath>
#include "live_renderer/components/shake_tracker.hpp"

namespace live_renderer {

TEST(ShakeTrackerTest, ComputeShakeOffsetZeroDurationOrStrength) {
    auto off1 = ShakeTracker::ComputeShakeOffset(0.1f, 0.0f, 10.0f, 42);
    EXPECT_FLOAT_EQ(off1.first, 0.0f);
    EXPECT_FLOAT_EQ(off1.second, 0.0f);

    auto off2 = ShakeTracker::ComputeShakeOffset(0.1f, 0.5f, 0.0f, 42);
    EXPECT_FLOAT_EQ(off2.first, 0.0f);
    EXPECT_FLOAT_EQ(off2.second, 0.0f);
}

TEST(ShakeTrackerTest, ComputeShakeOffsetOutOfBounds) {
    auto off_neg = ShakeTracker::ComputeShakeOffset(-0.1f, 0.5f, 10.0f, 42);
    EXPECT_FLOAT_EQ(off_neg.first, 0.0f);
    EXPECT_FLOAT_EQ(off_neg.second, 0.0f);

    auto off_past = ShakeTracker::ComputeShakeOffset(0.51f, 0.5f, 10.0f, 42);
    EXPECT_FLOAT_EQ(off_past.first, 0.0f);
    EXPECT_FLOAT_EQ(off_past.second, 0.0f);
}

TEST(ShakeTrackerTest, ComputeShakeOffsetDecaysLinearly) {
    const float duration = 1.0f;
    const float strength = 20.0f;

    // At t=0, magnitude <= strength
    auto [dx0, dy0] = ShakeTracker::ComputeShakeOffset(
        0.0f, duration, strength, 123);
    EXPECT_LE(std::abs(dx0), strength);
    EXPECT_LE(std::abs(dy0), strength);

    // At t=0.5, max strength is 10.0
    auto [dx_mid, dy_mid] = ShakeTracker::ComputeShakeOffset(
        0.5f, duration, strength, 123);
    EXPECT_LE(std::abs(dx_mid), 10.0f);
    EXPECT_LE(std::abs(dy_mid), 10.0f);

    // At t=0.9, max strength is 2.0
    auto [dx_late, dy_late] = ShakeTracker::ComputeShakeOffset(
        0.9f, duration, strength, 123);
    EXPECT_LE(std::abs(dx_late), 2.0f + 1e-4f);
    EXPECT_LE(std::abs(dy_late), 2.0f + 1e-4f);

    // At t=1.0, exactly 0
    auto [dx_end, dy_end] = ShakeTracker::ComputeShakeOffset(
        1.0f, duration, strength, 123);
    EXPECT_FLOAT_EQ(dx_end, 0.0f);
    EXPECT_FLOAT_EQ(dy_end, 0.0f);
}

TEST(ShakeTrackerTest, DeterministicWithSameSeed) {
    auto off1 = ShakeTracker::ComputeShakeOffset(0.2f, 0.5f, 15.0f, 999);
    auto off2 = ShakeTracker::ComputeShakeOffset(0.2f, 0.5f, 15.0f, 999);
    EXPECT_FLOAT_EQ(off1.first, off2.first);
    EXPECT_FLOAT_EQ(off1.second, off2.second);
}

TEST(ShakeTrackerTest, GetShakeOffsetLifecycle) {
    ShakeTracker tracker;
    const std::string key = "player_card_1";

    // Inactive -> 0
    auto off_idle = tracker.GetShakeOffset(key, false, 1000, 0.5f, 10.0f, 1);
    EXPECT_FLOAT_EQ(off_idle.first, 0.0f);
    EXPECT_FLOAT_EQ(off_idle.second, 0.0f);

    // Trigger active at t=1000ms
    auto off_start = tracker.GetShakeOffset(key, true, 1000, 0.5f, 10.0f, 1);
    EXPECT_LE(std::abs(off_start.first), 10.0f);
    EXPECT_LE(std::abs(off_start.second), 10.0f);

    // At t=1250ms (0.25s in, half duration)
    auto off_mid = tracker.GetShakeOffset(key, true, 1250, 0.5f, 10.0f, 1);
    EXPECT_LE(std::abs(off_mid.first), 5.0f);
    EXPECT_LE(std::abs(off_mid.second), 5.0f);

    // At t=1550ms (0.55s in, expired)
    auto off_expired = tracker.GetShakeOffset(key, true, 1550, 0.5f, 10.0f, 1);
    EXPECT_FLOAT_EQ(off_expired.first, 0.0f);
    EXPECT_FLOAT_EQ(off_expired.second, 0.0f);

    // Deactivate at t=2000ms
    tracker.GetShakeOffset(key, false, 2000, 0.5f, 10.0f, 1);

    // Re-trigger at t=3000ms -> new shake started
    auto off_retrigger = tracker.GetShakeOffset(
        key, true, 3000, 0.5f, 10.0f, 1);
    EXPECT_LE(std::abs(off_retrigger.first), 10.0f);
    EXPECT_LE(std::abs(off_retrigger.second), 10.0f);

    // Reset clears everything
    tracker.Reset();
    auto off_after_reset = tracker.GetShakeOffset(
        key, false, 4000, 0.5f, 10.0f, 1);
    EXPECT_FLOAT_EQ(off_after_reset.first, 0.0f);
    EXPECT_FLOAT_EQ(off_after_reset.second, 0.0f);
}

}  // namespace live_renderer
