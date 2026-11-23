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

class MockFeedReader : public IFeedReader {
public:
    bool Open(const std::string& url) override {
        opened_url = url;
        state = FeedConnectionState::kConnected;
        return true;
    }
    void Close() override { state = FeedConnectionState::kDisconnected; }
    bool IsOpen() const override {
        return state == FeedConnectionState::kConnected;
    }
    FeedConnectionState GetState() const override { return state; }
    std::string GetErrorMessage() const override { return error; }
    std::string GetUrl() const override { return opened_url; }
    int GetWidth() const override { return width; }
    int GetHeight() const override { return height; }
    uint64_t GetFrameSequence() const override { return seq; }
    bool CopyLatestFrameRgba(
        std::vector<uint8_t>& out_rgba,
        int& out_width,
        int& out_height,
        uint64_t& in_out_seq) const override {
        if (seq == 0 || seq == in_out_seq || frame.empty()) {
            return false;
        }
        out_rgba = frame;
        out_width = width;
        out_height = height;
        in_out_seq = seq;
        return true;
    }

    void PushSolidColor(uint8_t r, uint8_t g, uint8_t b, int w = 4, int h = 4) {
        width = w;
        height = h;
        frame.resize(static_cast<size_t>(w) * static_cast<size_t>(h) * 4);
        for (size_t i = 0; i < static_cast<size_t>(w) * static_cast<size_t>(h);
             ++i) {
            frame[i * 4 + 0] = r;
            frame[i * 4 + 1] = g;
            frame[i * 4 + 2] = b;
            frame[i * 4 + 3] = 255;
        }
        ++seq;
    }

    std::string opened_url;
    FeedConnectionState state = FeedConnectionState::kDisconnected;
    std::string error;
    std::vector<uint8_t> frame;
    int width = 0;
    int height = 0;
    uint64_t seq = 0;
};

TEST(LatencyMeterWindowTest, NormalizesRtmpUrlsAndValidatesStreamUrls) {
    EXPECT_EQ(
        LatencyMeterWindow::NormalizeRtmpUrl("192.168.1.50"),
        "rtmp://192.168.1.50");
    EXPECT_EQ(
        LatencyMeterWindow::NormalizeRtmpUrl("  rtmp://10.0.0.5/live  "),
        "rtmp://10.0.0.5/live");
    EXPECT_EQ(LatencyMeterWindow::NormalizeRtmpUrl("   "), "");

    std::string err;
    EXPECT_TRUE(
        RtspFeedReader::ValidateStreamUrl("rtmp://192.168.1.50/live", true, err));
    EXPECT_FALSE(
        RtspFeedReader::ValidateStreamUrl("rtmp://192.168.1.50/live", false, err));
}

TEST(LatencyMeterWindowTest, ColorDetectionChecksMajorityPixels) {
    // 3 of 4 pixels red -> majority red
    std::vector<uint8_t> mostly_red = {
        200, 20, 20, 255,
        180, 40, 30, 255,
        220, 10, 10, 255,
        200, 200, 200, 255,
    };
    EXPECT_TRUE(LatencyMeterWindow::IsMajorityRed(mostly_red, 2, 2));
    EXPECT_FALSE(LatencyMeterWindow::IsMajorityGreen(mostly_red, 2, 2));

    // 2 of 4 pixels green -> not strictly majority (> 50%)
    std::vector<uint8_t> half_green = {
        20, 200, 20, 255,
        30, 180, 40, 255,
        200, 200, 200, 255,
        10, 10, 10, 255,
    };
    EXPECT_FALSE(LatencyMeterWindow::IsMajorityGreen(half_green, 2, 2));

    // 3 of 4 pixels green -> majority green
    half_green[8] = 20;
    half_green[9] = 210;
    half_green[10] = 20;
    EXPECT_TRUE(LatencyMeterWindow::IsMajorityGreen(half_green, 2, 2));
}

TEST(LatencyMeterWindowTest, AutomaticModeDetectsRedCountsDownAndMeasuresGreen) {
    MockFeedReader* mock_ptr = nullptr;
    LatencyMeterWindow meter(nullptr, [&]() {
        auto ptr = std::make_unique<MockFeedReader>();
        mock_ptr = ptr.get();
        return ptr;
    });

    meter.ShowModeSelection();
    EXPECT_EQ(meter.GetMode(), LatencyMeterWindow::Mode::kSelection);

    meter.StartAutomaticSetup();
    EXPECT_EQ(meter.GetMode(), LatencyMeterWindow::Mode::kAutomatic);
    EXPECT_EQ(
        meter.GetAutoPhase(),
        LatencyMeterWindow::AutoPhase::kEnterAddress);

    // Invalid empty address stays in kEnterAddress
    EXPECT_FALSE(meter.StartAutomaticFeed("   ", 1000));
    EXPECT_FALSE(meter.GetRtmpError().empty());
    EXPECT_EQ(
        meter.GetAutoPhase(),
        LatencyMeterWindow::AutoPhase::kEnterAddress);

    // Valid IP normalizes to rtmp:// and waits for red
    EXPECT_TRUE(meter.StartAutomaticFeed("192.168.1.99", 1000));
    ASSERT_NE(mock_ptr, nullptr);
    EXPECT_EQ(mock_ptr->opened_url, "rtmp://192.168.1.99");
    EXPECT_EQ(
        meter.GetAutoPhase(),
        LatencyMeterWindow::AutoPhase::kWaitingForRed);

    // Non-red frame keeps waiting for red
    mock_ptr->PushSolidColor(200, 200, 200);
    meter.Update(1200);
    EXPECT_EQ(
        meter.GetAutoPhase(),
        LatencyMeterWindow::AutoPhase::kWaitingForRed);

    // Red frame starts 3..0 countdown
    mock_ptr->PushSolidColor(220, 20, 20);
    meter.Update(2000);
    EXPECT_EQ(
        meter.GetAutoPhase(),
        LatencyMeterWindow::AutoPhase::kCountdownToGreen);
    EXPECT_EQ(meter.GetAutoCount(), 3);

    meter.Update(3000);
    EXPECT_EQ(meter.GetAutoCount(), 2);
    meter.Update(4500);
    EXPECT_EQ(meter.GetAutoCount(), 1);

    // At 5000ms (3000ms elapsed), switches to green and waits for green frame
    meter.Update(5000);
    EXPECT_EQ(meter.GetAutoCount(), 0);
    EXPECT_EQ(
        meter.GetAutoPhase(),
        LatencyMeterWindow::AutoPhase::kWaitingForGreen);
    EXPECT_FALSE(meter.HasMeasuredLatency());

    // Still seeing red -> does not trigger yet
    mock_ptr->PushSolidColor(220, 20, 20);
    meter.Update(5150);
    EXPECT_EQ(
        meter.GetAutoPhase(),
        LatencyMeterWindow::AutoPhase::kWaitingForGreen);

    // Green detected at 5275ms -> 275ms latency
    mock_ptr->PushSolidColor(20, 220, 20);
    meter.Update(5275);
    EXPECT_EQ(
        meter.GetAutoPhase(),
        LatencyMeterWindow::AutoPhase::kMeasured);
    EXPECT_TRUE(meter.HasMeasuredLatency());
    EXPECT_EQ(meter.GetMeasuredLatencyMs(), 275);
}

}  // namespace
