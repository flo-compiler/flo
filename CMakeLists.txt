cmake_minimum_required(VERSION 3.8)
project(Flo
        VERSION 0.0.1
        DESCRIPTION "The Flo Programming Language"
        LANGUAGES C CXX
        )


find_package(LLVM 15...<17 REQUIRED CONFIG)
message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")

add_link_options(-no-pie)

exec_program(${LLVM_TOOLS_BINARY_DIR}/llvm-config 
ARGS --libs all
OUTPUT_VARIABLE llvm_libs)
add_executable(helper bootstrap/helper.c)
target_link_libraries(helper PRIVATE ${llvm_libs})

SET(STAGE0_OBJ
  ${CMAKE_BINARY_DIR}/stage0.o
)
SET(LLVM_BIND_SRC
    ${CMAKE_CURRENT_SOURCE_DIR}/src/llvm/FloLLVMBind.cpp
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
target_link_libraries(stage0 PRIVATE ${llvm_libs})


function(compile_stage PREV_STAGE CURR_STAGE)
    add_custom_target(
        ${CURR_STAGE}.o ALL
        COMMAND ${PREV_STAGE} ${CMAKE_CURRENT_SOURCE_DIR}/src/main.flo --emit obj -o  ${CMAKE_BINARY_DIR}/${CURR_STAGE}.o -O 3 -I ${CMAKE_CURRENT_SOURCE_DIR}/lib/
        DEPENDS ${PREV_STAGE}
    )
    add_executable(${CURR_STAGE} ${CMAKE_BINARY_DIR}/${CURR_STAGE}.o ${LLVM_BIND_SRC})
    set_source_files_properties(
        ${CMAKE_BINARY_DIR}/${CURR_STAGE}.o
        PROPERTIES
        EXTERNAL_OBJECT true
        GENERATED true
    )
    target_link_libraries(${CURR_STAGE} PRIVATE ${llvm_libs})
endfunction()

compile_stage(stage0 stage1)
compile_stage(stage1 flo)