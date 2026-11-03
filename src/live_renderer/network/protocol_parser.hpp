#ifndef LIVE_RENDERER_NETWORK_PROTOCOL_PARSER_HPP_
#define LIVE_RENDERER_NETWORK_PROTOCOL_PARSER_HPP_

#include <string>
#include <string_view>
#include <vector>
#include "live_renderer/state/live_state_store.hpp"

namespace live_renderer {

/**
 * @brief Parses tab-delimited protocol lines emitted by lflive and updates LiveStateStore.
 */
class ProtocolParser {
public:
    explicit ProtocolParser(LiveStateStore& store);
    ~ProtocolParser() = default;

    /**
     * @brief Parses a single line (excluding or including \r\n).
     * @param line UTF-8 text line.
     * @return true if parsed and handled, false if unrecognized or malformed.
     */
    bool ParseLine(std::string_view line);

private:
    static std::vector<std::string_view> SplitTabs(std::string_view s);
    static int ParseInt(std::string_view s, int default_val = 0);
    static int64_t ParseInt64(std::string_view s, int64_t default_val = 0);
    static std::vector<int> ParseIntList(std::string_view s);

    LiveStateStore& store_;
};

}  // namespace live_renderer

#endif  // LIVE_RENDERER_NETWORK_PROTOCOL_PARSER_HPP_

