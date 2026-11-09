idf_component_register(SRCS "Main.c" INCLUDE_DIRS "." REQUIRES esp_app_format esp_system log)
set_property(TARGET ${COMPONENT_LIB} PROPERTY C_STANDARD 11)
set_property(TARGET ${COMPONENT_LIB} PROPERTY C_STANDARD_REQUIRED ON)
set_property(TARGET ${COMPONENT_LIB} PROPERTY C_EXTENSIONS OFF)
# IDF 6.1 adds its default GNU standard through directory options after C_STANDARD.
# Override only the application component; third-party components retain SDK flags.
target_compile_options(${COMPONENT_LIB} PRIVATE "$<$<COMPILE_LANGUAGE:C>:-std=c11>")
