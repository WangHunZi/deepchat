if(NOT DEFINED APPLICATION_ROOT)
    message(FATAL_ERROR "Provide APPLICATION_ROOT from the prepared, patched Xiaozhi source")
endif()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(Threads REQUIRED)
set(DC_APPLICATION_SOURCE "${APPLICATION_ROOT}/application.cc")
set(DC_APPLICATION_METHODS "${CMAKE_CURRENT_BINARY_DIR}/DCApplicationMethods.cpp")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${DC_APPLICATION_SOURCE}" "${APPLICATION_ROOT}/application.h"
    "${CMAKE_CURRENT_SOURCE_DIR}/extract_application.py")
execute_process(COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/extract_application.py"
    "${DC_APPLICATION_SOURCE}" "${DC_APPLICATION_METHODS}"
    COMMAND_ERROR_IS_FATAL ANY)
add_executable(DCPttApplicationTest DCApplicationTest.cpp "${DC_APPLICATION_METHODS}"
    "${UPSTREAM_ROOT}/main/device_state_machine.cc")
target_include_directories(DCPttApplicationTest PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}" "${APPLICATION_ROOT}"
    "${UPSTREAM_ROOT}/main" "${CMAKE_CURRENT_SOURCE_DIR}/../pet")
target_link_libraries(DCPttApplicationTest PRIVATE Threads::Threads)
target_compile_options(DCPttApplicationTest PRIVATE -Wall -Wextra -Wpedantic -Werror)
foreach(case coalesced-tap release-before-connect release-during-connect release-before-audio
    release-repress normal open-failure network-error channel-close reset-during-connect
    reset-before-scheduled-open disconnect toggle-auto auto-after-manual wake-after-manual diagnostic speaking-interrupt)
    add_test(NAME ptt-${case} COMMAND DCPttApplicationTest ${case})
    set_tests_properties(ptt-${case} PROPERTIES TIMEOUT 10)
endforeach()
