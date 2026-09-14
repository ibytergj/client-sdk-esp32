cmake_minimum_required(VERSION 3.16)
if(WIN32)
    # ESP-IDF's media dependency graph exceeds Windows' process command-line limit.
    set(CMAKE_NINJA_FORCE_RESPONSE_FILE ON CACHE BOOL "Use response files for long ESP-IDF commands" FORCE)
endif()
set(COMPONENTS main)
if(EXISTS "$ENV{IDF_PATH}/tools/test_apps/components")
    # ESP-IDF 6 moved the shared test components to tools/test_apps.
    set(EXTRA_COMPONENT_DIRS "$ENV{IDF_PATH}/tools/test_apps/components")
else()
    set(EXTRA_COMPONENT_DIRS "$ENV{IDF_PATH}/tools/unit-test-app/components")
endif()
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(test_app)

# esp_asrc 1.0.x logs a uint32_t with %d, which ESP-IDF 5.4 rejects under
# -Werror. Keep it a warning for that component only; our own code is unchanged.
idf_build_get_property(lk_build_components BUILD_COMPONENTS)
if("espressif__esp_asrc" IN_LIST lk_build_components)
    idf_component_get_property(lk_esp_asrc_lib espressif__esp_asrc COMPONENT_LIB)
    target_compile_options(${lk_esp_asrc_lib} PRIVATE "-Wno-error=format")
endif()
