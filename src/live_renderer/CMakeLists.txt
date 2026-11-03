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

# SDL2
if(WIN32 AND MSVC)
    FetchContent_Declare(
        sdl2_prebuilt
        URL https://github.com/libsdl-org/SDL/releases/download/release-2.30.11/SDL2-devel-2.30.11-VC.zip
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    )
    FetchContent_MakeAvailable(sdl2_prebuilt)
    set(SDL2_INCLUDE_DIR "${sdl2_prebuilt_SOURCE_DIR}/include")
    set(SDL2_LIB_DIR "${sdl2_prebuilt_SOURCE_DIR}/lib/x64")
    set(SDL2_DLL_PATH "${SDL2_LIB_DIR}/SDL2.dll")

    add_library(SDL2_lib SHARED IMPORTED GLOBAL)
    set_target_properties(SDL2_lib PROPERTIES
        IMPORTED_LOCATION "${SDL2_DLL_PATH}"
        IMPORTED_IMPLIB "${SDL2_LIB_DIR}/SDL2.lib"
        INTERFACE_INCLUDE_DIRECTORIES "${SDL2_INCLUDE_DIR}"
    )
else()
    FetchContent_Declare(
        SDL2
        GIT_REPOSITORY https://github.com/libsdl-org/SDL.git
        GIT_TAG release-2.30.11
    )
    FetchContent_MakeAvailable(SDL2)
    add_library(SDL2_lib ALIAS SDL2::SDL2)
endif()

# Dear ImGui
FetchContent_Declare(
    imgui
    GIT_REPOSITORY https://github.com/ocornut/imgui.git
    GIT_TAG v1.91.8
)
FetchContent_MakeAvailable(imgui)

find_package(OpenGL REQUIRED)

add_library(imgui_sdl_gl3 STATIC
    ${imgui_SOURCE_DIR}/imgui.cpp
    ${imgui_SOURCE_DIR}/imgui_draw.cpp
    ${imgui_SOURCE_DIR}/imgui_tables.cpp
    ${imgui_SOURCE_DIR}/imgui_widgets.cpp
    ${imgui_SOURCE_DIR}/backends/imgui_impl_sdl2.cpp
    ${imgui_SOURCE_DIR}/backends/imgui_impl_opengl3.cpp
)
target_include_directories(imgui_sdl_gl3 PUBLIC
    ${imgui_SOURCE_DIR}
    ${imgui_SOURCE_DIR}/backends
)
target_link_libraries(imgui_sdl_gl3 PUBLIC
    SDL2_lib
    OpenGL::GL
)

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
    windows/main_control_window.cpp
)

add_library(live_renderer_core STATIC ${CORE_SOURCES})
target_include_directories(live_renderer_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/..
)
target_link_libraries(live_renderer_core PUBLIC
    yaml-cpp::yaml-cpp
    imgui_sdl_gl3
)

if(WIN32)
    target_link_libraries(live_renderer_core PUBLIC ws2_32 comdlg32)
endif()

# Tests
enable_testing()

add_executable(live_renderer_tests
    tests/test_protocol_parser.cpp
    tests/test_config_serializer.cpp
    tests/test_rich_text_layout.cpp
    tests/test_scorecard_sorting.cpp
    tests/test_main_control_window.cpp
)
target_link_libraries(live_renderer_tests PRIVATE
    live_renderer_core
    gtest_main
)

include(GoogleTest)
gtest_discover_tests(live_renderer_tests)

# Main executable
add_executable(live_renderer
    main.cpp
)
target_link_libraries(live_renderer PRIVATE
    live_renderer_core
)

if(WIN32 AND MSVC)
    add_custom_command(TARGET live_renderer POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${SDL2_DLL_PATH}"
            "$<TARGET_FILE_DIR:live_renderer>"
    )
    add_custom_command(TARGET live_renderer_tests POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${SDL2_DLL_PATH}"
            "$<TARGET_FILE_DIR:live_renderer_tests>"
    )
endif()
