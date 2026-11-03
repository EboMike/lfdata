cmake_minimum_required(VERSION 3.24)
project(live_renderer C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

# yaml-cpp (master / latest release compatible with CMake 3.5+)
set(YAML_MSVC_SHARED_RT ON CACHE BOOL "" FORCE)
FetchContent_Declare(
    yaml-cpp
    GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
    GIT_TAG master
)
set(YAML_CPP_BUILD_TESTS OFF CACHE INTERNAL "")
set(YAML_CPP_BUILD_TOOLS OFF CACHE INTERNAL "")
FetchContent_MakeAvailable(yaml-cpp)

# GoogleTest
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)
FetchContent_MakeAvailable(googletest)

# Core library
set(CORE_SOURCES
    config/config_serializer.cpp
    state/live_state_store.cpp
    state/mock_game_state.cpp
    network/protocol_parser.cpp
    network/tcp_consumer_client.cpp
    render/rich_text_layout.cpp
    components/game_timer_element.cpp
    components/scorecard_helper.cpp
)

add_library(live_renderer_core STATIC ${CORE_SOURCES})
target_include_directories(live_renderer_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/..
)
target_link_libraries(live_renderer_core PUBLIC yaml-cpp::yaml-cpp)

if(WIN32)
    target_link_libraries(live_renderer_core PUBLIC ws2_32)
endif()

# Tests
enable_testing()

add_executable(live_renderer_tests
    tests/test_protocol_parser.cpp
    tests/test_config_serializer.cpp
    tests/test_rich_text_layout.cpp
    tests/test_scorecard_sorting.cpp
)
target_link_libraries(live_renderer_tests PRIVATE
    live_renderer_core
    gtest_main
)

include(GoogleTest)
gtest_discover_tests(live_renderer_tests)

