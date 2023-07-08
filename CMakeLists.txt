cmake_minimum_required(VERSION 3.8)

SET(MAIN_SRC_FILE ${CMAKE_CURRENT_SOURCE_DIR}/src/main.flo)
set(VERSION_REGEX "[ \t]*let COMPILER_VERSION[ \t]*\=[ \t]*\"(.+)\"")
file(STRINGS "${MAIN_SRC_FILE}"
    VERSION_STRING REGEX ${VERSION_REGEX})

string(REGEX REPLACE ${VERSION_REGEX} "\\1" VERSION_STRING "${VERSION_STRING}")

project(Flo
        VERSION ${VERSION_STRING}
        DESCRIPTION "The Flo Programming Language"
        LANGUAGES C CXX
        )
find_package(LLVM REQUIRED CONFIG)
message(STATUS "COMPILER VERSION: ${VERSION_STRING}")
message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

set (CMAKE_CXX_STANDARD 17)
add_link_options(-no-pie)

add_definitions(${LLVM_DEFINITIONS})
separate_arguments(LLVM_DEFINITIONS_LIST NATIVE_COMMAND ${LLVM_DEFINITIONS})
include_directories(${LLVM_INCLUDE_DIRS})


add_executable(helper bootstrap/helper.cc)
target_link_libraries(helper PRIVATE LLVM)

SET(STAGE0_OBJ
  ${CMAKE_BINARY_DIR}/stage0.o
)
SET(LLVM_BIND_SRC
    ${CMAKE_CURRENT_SOURCE_DIR}/src/llvm/FloLLVMBind.cc
)
add_custom_target(
    stage0.o ALL
    COMMAND helper ${CMAKE_CURRENT_SOURCE_DIR}/bootstrap/flo.ll ${STAGE0_OBJ}
    DEPENDS helper
)
add_executable(stage0 ${STAGE0_OBJ} ${LLVM_BIND_SRC})
set_source_files_properties(
  ${STAGE0_OBJ}
  PROPERTIES
  EXTERNAL_OBJECT true
  GENERATED true
)
target_link_libraries(stage0 PRIVATE LLVM)


function(compile_stage PREV_STAGE CURR_STAGE)
    add_custom_target(
        ${CURR_STAGE}.o ALL
        COMMAND ${PREV_STAGE} ${MAIN_SRC_FILE} --emit obj -o  ${CMAKE_BINARY_DIR}/${CURR_STAGE}.o -O 3 -I ${CMAKE_CURRENT_SOURCE_DIR}/lib/
        DEPENDS ${PREV_STAGE}
    )
    add_executable(${CURR_STAGE} ${CMAKE_BINARY_DIR}/${CURR_STAGE}.o ${LLVM_BIND_SRC})
    set_source_files_properties(
        ${CMAKE_BINARY_DIR}/${CURR_STAGE}.o
        PROPERTIES
        EXTERNAL_OBJECT true
        GENERATED true
    )
    target_link_libraries(${CURR_STAGE} PRIVATE LLVM)

endfunction()

compile_stage(stage0 stage1)
compile_stage(stage1 flo)