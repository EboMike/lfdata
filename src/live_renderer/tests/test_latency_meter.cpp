#include <gtest/gtest.h>

#include "live_renderer/network/protocol_parser.hpp"
#include "live_renderer/network/tcp_consumer_client.hpp"
#include "live_renderer/state/live_state_store.hpp"
#include "live_renderer/windows/latency_meter_window.hpp"
#include "live_renderer/windows/main_control_window.hpp"

namespace {

using namespace live_renderer;

TEST(LatencyMeterWindowTest, CountdownPlaysBeepAtZeroAndMeasuresLatency) {
    int beep_count = 0;
    int last_freq = 0;
    int last_dur = 0;
    LatencyMeterWindow meter([&](int freq, int dur) {
        ++beep_count;
        last_freq = freq;
        last_dur = dur;
    });

    meter.Reset(1000);
    EXPECT_EQ(meter.GetCurrentCount(), 5);
    EXPECT_FALSE(meter.HasReachedZero());
    EXPECT_FALSE(meter.HasMeasuredLatency());

    meter.Update(1999);
    EXPECT_EQ(meter.GetCurrentCount(), 5);
    meter.Update(2000);
    EXPECT_EQ(meter.GetCurrentCount(), 4);
    meter.Update(5500);
    EXPECT_EQ(meter.GetCurrentCount(), 1);
    EXPECT_EQ(beep_count, 0);

    // Pressing before 0 does nothing
    EXPECT_FALSE(meter.TriggerResponse(5600));
    EXPECT_FALSE(meter.HasMeasuredLatency());

    // Reaching 0 at 6000ms triggers 1000Hz 200ms beep once
    meter.Update(6050);
    EXPECT_EQ(meter.GetCurrentCount(), 0);
    EXPECT_TRUE(meter.HasReachedZero());
    EXPECT_EQ(beep_count, 1);
    EXPECT_EQ(last_freq, 1000);
    EXPECT_EQ(last_dur, 200);

    // Subsequent updates before response do not re-beep
    meter.Update(6100);
    EXPECT_EQ(beep_count, 1);

    // Response at 6235ms measures 235ms from exact zero crossing (6000ms)
    EXPECT_TRUE(meter.TriggerResponse(6235));
    EXPECT_TRUE(meter.HasMeasuredLatency());
    EXPECT_EQ(meter.GetMeasuredLatencyMs(), 235);

    // Further triggers are ignored
    EXPECT_FALSE(meter.TriggerResponse(6500));
    EXPECT_EQ(meter.GetMeasuredLatencyMs(), 235);
}

TEST(LatencyMeterWindowTest, MainControlWindowLatencyMeterButtonTriggersCallback) {
    GlobalConfig global_cfg;
    UIConfig ui_cfg;
    LiveStateStore store;
    ProtocolParser parser(store);
    TcpConsumerClient client(parser, global_cfg.host, global_cfg.port);

    MainControlWindow win("test_ctrl_latency.yaml", global_cfg, ui_cfg, store, client);
    bool opened = false;
    MainControlWindow::Callbacks cbs;
    cbs.on_open_latency_meter = [&]() { opened = true; };
    win.SetCallbacks(cbs);

    win.ClickLatencyMeter();
    EXPECT_TRUE(opened);
}

}  // namespace
