#include <gtest/gtest.h>
#include "live_renderer/components/messages_display_tracker.hpp"

using namespace live_renderer;

TEST(MessagesDisplayTrackerTest, AssignsNewMessagesToFirstSlotFromTop) {
    MessagesDisplayTracker tracker;
    std::vector<ImportantEventItem> events = {
        {10, 1000, "Commander activates nuke"}
    };

    tracker.Update("win1_el1", events, 3, 4.0f, 1.0f, 1000);
    const auto& slots = tracker.GetSlots("win1_el1");
    ASSERT_EQ(slots.size(), 3);
    EXPECT_TRUE(slots[0].active);
    EXPECT_EQ(slots[0].message_id, 10);
    EXPECT_EQ(slots[0].message, "Commander activates nuke");
    EXPECT_FLOAT_EQ(slots[0].opacity, 1.0f);
    EXPECT_FALSE(slots[1].active);
    EXPECT_FALSE(slots[2].active);

    // Second message issued
    events.push_back({11, 2000, "Medic eliminated"});
    tracker.Update("win1_el1", events, 3, 4.0f, 1.0f, 2000);
    const auto& slots2 = tracker.GetSlots("win1_el1");
    EXPECT_TRUE(slots2[0].active);
    EXPECT_EQ(slots2[0].message_id, 10);
    EXPECT_TRUE(slots2[1].active);
    EXPECT_EQ(slots2[1].message_id, 11);
    EXPECT_EQ(slots2[1].message, "Medic eliminated");
    EXPECT_FALSE(slots2[2].active);

    // Third message issued
    events.push_back({12, 3000, "Red Base destroyed"});
    tracker.Update("win1_el1", events, 3, 4.0f, 1.0f, 3000);
    const auto& slots3 = tracker.GetSlots("win1_el1");
    EXPECT_TRUE(slots3[2].active);
    EXPECT_EQ(slots3[2].message_id, 12);
}

TEST(MessagesDisplayTrackerTest, ReplacesExistingMessageWithSameId) {
    MessagesDisplayTracker tracker;
    std::vector<ImportantEventItem> events = {
        {10, 1000, "Commander activates nuke"},
        {11, 2000, "Medic eliminated"}
    };

    tracker.Update("display", events, 3, 4.0f, 1.0f, 1000);
    tracker.Update("display", events, 3, 4.0f, 1.0f, 2000);

    // Re-issue ID 10 with new text at t=3500
    events[0] = {10, 3500, "Commander detonates nuke"};
    tracker.Update("display", events, 3, 4.0f, 1.0f, 3500);

    const auto& slots = tracker.GetSlots("display");
    EXPECT_EQ(slots[0].message_id, 10);
    EXPECT_EQ(slots[0].message, "Commander detonates nuke");
    EXPECT_FLOAT_EQ(slots[0].opacity, 1.0f);
    EXPECT_EQ(slots[0].start_time_ms, 3500);

    // At t=6500 (5500ms after original 1000ms):
    // ID 10 timer was reset at 3500ms, so elapsed is 3000ms (< 4000ms)
    // Therefore it is still fully visible with opacity 1.0.
    tracker.Update("display", events, 3, 4.0f, 1.0f, 6500);
    const auto& slots_later = tracker.GetSlots("display");
    EXPECT_TRUE(slots_later[0].active);
    EXPECT_FLOAT_EQ(slots_later[0].opacity, 1.0f);
}

TEST(MessagesDisplayTrackerTest, FadesOutAfterDisplayTimeAndBecomesInactive) {
    MessagesDisplayTracker tracker;
    std::vector<ImportantEventItem> events = {
        {10, 1000, "Commander activates nuke"}
    };

    // Issued at t=1000 with display_time=4.0s (4000ms), fadeout=1.0s (1000ms)
    tracker.Update("disp", events, 2, 4.0f, 1.0f, 1000);

    // At t=3000 (elapsed 2000ms < 4000ms) -> fully visible
    tracker.Update("disp", events, 2, 4.0f, 1.0f, 3000);
    EXPECT_FLOAT_EQ(tracker.GetSlots("disp")[0].opacity, 1.0f);

    // At t=5500 (elapsed 4500ms: 500ms into 1000ms fadeout) -> opacity ~ 0.5
    tracker.Update("disp", events, 2, 4.0f, 1.0f, 5500);
    EXPECT_NEAR(tracker.GetSlots("disp")[0].opacity, 0.5f, 0.05f);

    // At t=6100 (elapsed 5100ms > 5000ms total lifetime) -> inactive
    tracker.Update("disp", events, 2, 4.0f, 1.0f, 6100);
    EXPECT_FALSE(tracker.GetSlots("disp")[0].active);
    EXPECT_FLOAT_EQ(tracker.GetSlots("disp")[0].opacity, 0.0f);
}

TEST(MessagesDisplayTrackerTest, FreesSlotAfterFadeoutForNewMessage) {
    MessagesDisplayTracker tracker;
    std::vector<ImportantEventItem> events = {
        {10, 1000, "Msg 10"}
    };

    tracker.Update("disp", events, 2, 4.0f, 1.0f, 1000);

    events.push_back({11, 2000, "Msg 11"});
    tracker.Update("disp", events, 2, 4.0f, 1.0f, 2000);

    // At t=6100, Msg 10 (t=1000) has expired (elapsed 5100ms > 5000ms)
    // Msg 11 (t=2000) is fading (elapsed 4100ms)
    tracker.Update("disp", events, 2, 4.0f, 1.0f, 6100);
    EXPECT_FALSE(tracker.GetSlots("disp")[0].active);
    EXPECT_TRUE(tracker.GetSlots("disp")[1].active);

    // Now a new message ID 12 arrives at t=6200
    events.push_back({12, 6200, "Msg 12"});
    tracker.Update("disp", events, 2, 4.0f, 1.0f, 6200);

    // Slot 0 was free, so Msg 12 is placed into Slot 0!
    const auto& slots = tracker.GetSlots("disp");
    EXPECT_TRUE(slots[0].active);
    EXPECT_EQ(slots[0].message_id, 12);
    EXPECT_EQ(slots[0].message, "Msg 12");
}

TEST(MessagesDisplayTrackerTest, ReplacesOldestSlotWhenAllSlotsOccupied) {
    MessagesDisplayTracker tracker;
    std::vector<ImportantEventItem> events = {
        {1, 1000, "First"},
        {2, 2000, "Second"}
    };

    tracker.Update("disp", events, 2, 10.0f, 1.0f, 1000);
    tracker.Update("disp", events, 2, 10.0f, 1.0f, 2000);

    // Both slots 0 and 1 occupied. Third message arrives at t=3000.
    events.push_back({3, 3000, "Third"});
    tracker.Update("disp", events, 2, 10.0f, 1.0f, 3000);

    // Slot 0 (oldest: start_time 1000) was replaced by ID 3
    const auto& slots = tracker.GetSlots("disp");
    EXPECT_EQ(slots[0].message_id, 3);
    EXPECT_EQ(slots[0].message, "Third");
    EXPECT_EQ(slots[1].message_id, 2);
}

TEST(MessagesDisplayTrackerTest, ResetsWhenEventsAreCleared) {
    MessagesDisplayTracker tracker;
    std::vector<ImportantEventItem> events = {
        {1, 1000, "First"}
    };
    tracker.Update("disp", events, 2, 4.0f, 1.0f, 1000);
    EXPECT_TRUE(tracker.GetSlots("disp")[0].active);

    // Cleared events (session reset)
    events.clear();
    tracker.Update("disp", events, 2, 4.0f, 1.0f, 2000);
    EXPECT_FALSE(tracker.GetSlots("disp")[0].active);
}
