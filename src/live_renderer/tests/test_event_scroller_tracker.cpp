/**
 * @file test_event_scroller_tracker.cpp
 * @brief Unit tests for EventScrollerTracker continuous smooth scroll.
 */

#include <gtest/gtest.h>
#include <cmath>
#include "live_renderer/components/event_scroller_tracker.hpp"

using namespace live_renderer;

TEST(EventScrollerTrackerTest, InitialOffsetReturnsTargetDirectly) {
    EventScrollerTracker tracker;
    float offset = tracker.GetScrollOffset("scroller1", 5, 20.0f, 1000);
    // 5 events, idx = 4, target_offset = 4 * 20 = 80.0f
    EXPECT_FLOAT_EQ(offset, 80.0f);
}

TEST(EventScrollerTrackerTest, SmoothEaseInOutScrollingOnNewEvent) {
    EventScrollerTracker tracker;
    // Initial: 5 events at t=1000
    tracker.GetScrollOffset("scroller1", 5, 20.0f, 1000,
                            "ease-in-and-ease-out", 0.5f);

    // New event arrives at t=2000 (total 6 events, target = 100.0f)
    float start = tracker.GetScrollOffset("scroller1", 6, 20.0f, 2000,
                                         "ease-in-and-ease-out", 0.5f);
    // At t=2000, elapsed = 0, should still be at start position 80.0f
    EXPECT_FLOAT_EQ(start, 80.0f);

    // Halfway through 500ms duration at t=2250 (250ms elapsed)
    float mid = tracker.GetScrollOffset("scroller1", 6, 20.0f, 2250,
                                       "ease-in-and-ease-out", 0.5f);
    // Cosine ease at p=0.5 is 0.5 * (1 - cos(0.5*pi)) = 0.5
    // 80.0f + (100.0f - 80.0f) * 0.5 = 90.0f
    EXPECT_NEAR(mid, 90.0f, 0.05f);

    // At completion at t=2500 (500ms elapsed)
    float end = tracker.GetScrollOffset("scroller1", 6, 20.0f, 2500,
                                       "ease-in-and-ease-out", 0.5f);
    EXPECT_FLOAT_EQ(end, 100.0f);
}

TEST(EventScrollerTrackerTest, LinearScrollingOnNewEvent) {
    EventScrollerTracker tracker;
    tracker.GetScrollOffset("scroller1", 2, 30.0f, 1000, "linear", 0.4f);

    // New event arrives at t=2000 (3 events, target = 60.0f)
    float t0 = tracker.GetScrollOffset("scroller1", 3, 30.0f, 2000,
                                      "linear", 0.4f);
    EXPECT_FLOAT_EQ(t0, 30.0f);

    // At 100ms into 400ms duration (p = 0.25)
    float t1 = tracker.GetScrollOffset("scroller1", 3, 30.0f, 2100,
                                      "linear", 0.4f);
    EXPECT_NEAR(t1, 30.0f + 30.0f * 0.25f, 0.01f);

    // At 400ms (p = 1.0)
    float t2 = tracker.GetScrollOffset("scroller1", 3, 30.0f, 2400,
                                      "linear", 0.4f);
    EXPECT_FLOAT_EQ(t2, 60.0f);
}

TEST(EventScrollerTrackerTest, NoneAnimationSnapsInstantly) {
    EventScrollerTracker tracker;
    tracker.GetScrollOffset("scroller1", 3, 25.0f, 1000, "none", 0.5f);

    // New event arrives with anim_type "none"
    float offset = tracker.GetScrollOffset("scroller1", 4, 25.0f, 1001,
                                          "none", 0.5f);
    // Immediately snaps to target 3 * 25 = 75.0f
    EXPECT_FLOAT_EQ(offset, 75.0f);
}

TEST(EventScrollerTrackerTest, InterruptedMidScrollSmoothlyContinues) {
    EventScrollerTracker tracker;
    // 10 events (target = 90.0f)
    tracker.GetScrollOffset("scroller1", 10, 10.0f, 1000, "linear", 1.0f);

    // 11th event arrives at t=2000 (target = 100.0f, duration 1000ms)
    tracker.GetScrollOffset("scroller1", 11, 10.0f, 2000, "linear", 1.0f);

    // Advance 500ms -> halfway: 90 + 0.5 * 10 = 95.0f
    float mid = tracker.GetScrollOffset("scroller1", 11, 10.0f, 2500,
                                       "linear", 1.0f);
    EXPECT_NEAR(mid, 95.0f, 0.01f);

    // 12th event arrives at t=2500 (target = 110.0f, duration 1000ms)
    // It must start seamlessly from visual 95.0f!
    float interrupted_start = tracker.GetScrollOffset(
        "scroller1", 12, 10.0f, 2500, "linear", 1.0f);
    EXPECT_NEAR(interrupted_start, 95.0f, 0.01f);

    // Advance 500ms to t=3000 (halfway from 95.0f to 110.0f -> 102.5f)
    float new_mid = tracker.GetScrollOffset("scroller1", 12, 10.0f, 3000,
                                           "linear", 1.0f);
    EXPECT_NEAR(new_mid, 95.0f + (110.0f - 95.0f) * 0.5f, 0.05f);
}

TEST(EventScrollerTrackerTest, HandlesBufferPruningWithoutJump) {
    EventScrollerTracker tracker;
    // 200 events at step_y = 10.0f -> target = 1990.0f
    tracker.GetScrollOffset("scroller1", 200, 10.0f, 1000, "none", 0.0f);

    // LiveStateStore caps at 200: adds 1 and erases 50 -> net size is 151
    // Net dropped count is 200 - 151 = 49 events.
    // Shift is 49 * 10 = 490.0f. Visual 1990 - 490 = 1500.0f
    // New target is (151 - 1) * 10 = 1500.0f.
    float offset = tracker.GetScrollOffset("scroller1", 151, 10.0f, 1001,
                                          "linear", 0.5f);
    EXPECT_FLOAT_EQ(offset, 1500.0f);
}

TEST(EventScrollerTrackerTest, HandlesSessionResetSafely) {
    EventScrollerTracker tracker;
    tracker.GetScrollOffset("scroller1", 100, 10.0f, 1000, "none", 0.0f);

    // Full session reset to 1 event
    float reset_offset = tracker.GetScrollOffset(
        "scroller1", 1, 10.0f, 2000, "ease-in-and-ease-out", 0.5f);
    EXPECT_FLOAT_EQ(reset_offset, 0.0f);
}

TEST(EventScrollerTrackerTest, ClockJitterSafety) {
    EventScrollerTracker tracker;
    tracker.GetScrollOffset("scroller1", 5, 20.0f, 1000);

    // New event at t=2000
    tracker.GetScrollOffset("scroller1", 6, 20.0f, 2000);

    // Slight clock jitter backwards (t=1995 < t_start=2000)
    float guarded = tracker.GetScrollOffset("scroller1", 6, 20.0f, 1995);
    // Must return start position, NOT jump forward to target!
    EXPECT_FLOAT_EQ(guarded, 80.0f);
}

