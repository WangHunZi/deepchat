cmake_minimum_required(VERSION 3.22)
project(DeepChatHost LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(CheckCSourceCompiles)
include(CheckCXXSourceCompiles)
check_c_source_compiles("
#if __STDC_VERSION__ != 201112L
#error C11 is required
#endif
_Static_assert(sizeof(char) == 1, \"C11 static assertion\");
int main(void) { return 0; }
" DC_HOST_C11)
check_cxx_source_compiles("
#include <type_traits>
static_assert(std::is_same_v<int, int>);
int main() { if constexpr (true) { return 0; } }
" DC_HOST_CPP17)
if(NOT DC_HOST_C11 OR NOT DC_HOST_CPP17)
    message(FATAL_ERROR "DeepChat requires working C11 and C++17 host compilers")
endif()

include(CTest)
# P1 adds real core targets and contract tests. P0 does not register placeholder tests.
