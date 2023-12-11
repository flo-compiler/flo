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
find_package(LLVM REQUIRED CONFIG PATHS ${LLVM_INSTALL_DIR} NO_DEFAULT_PATH)
message(STATUS "COMPILER VERSION: ${VERSION_STRING}")
message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

set (CMAKE_CXX_STANDARD 17)
add_link_options(-no-pie)
add_link_options("-fuse-ld=lld")

add_definitions(${LLVM_DEFINITIONS})
separate_arguments(LLVM_DEFINITIONS_LIST NATIVE_COMMAND ${LLVM_DEFINITIONS})
include_directories(${LLVM_INCLUDE_DIRS})
llvm_map_components_to_libnames(LLVM_LIBS 
    WindowsManifest
    XRay
    LibDriver
    DlltoolDriver
    Coverage
    LineEditor
    XCoreDisassembler
    XCoreCodeGen
    XCoreDesc
    XCoreInfo
    X86TargetMCA
    X86Disassembler
    X86AsmParser
    X86CodeGen
    X86Desc
    X86Info
    WebAssemblyDisassembler
    WebAssemblyAsmParser
    WebAssemblyCodeGen
    WebAssemblyUtils
    WebAssemblyDesc
    WebAssemblyInfo
    VEDisassembler
    VEAsmParser
    VECodeGen
    VEDesc
    VEInfo
    SystemZDisassembler
    SystemZAsmParser
    SystemZCodeGen
    SystemZDesc
    SystemZInfo
    SparcDisassembler
    SparcAsmParser
    SparcCodeGen
    SparcDesc
    SparcInfo
    RISCVTargetMCA
    RISCVDisassembler
    RISCVAsmParser
    RISCVCodeGen
    RISCVDesc
    RISCVInfo
    PowerPCDisassembler
    PowerPCAsmParser
    PowerPCCodeGen
    PowerPCDesc
    PowerPCInfo
    NVPTXCodeGen
    NVPTXDesc
    NVPTXInfo
    MSP430Disassembler
    MSP430AsmParser
    MSP430CodeGen
    MSP430Desc
    MSP430Info
    MipsDisassembler
    MipsAsmParser
    MipsCodeGen
    MipsDesc
    MipsInfo
    LoongArchDisassembler
    LoongArchAsmParser
    LoongArchCodeGen
    LoongArchDesc
    LoongArchInfo
    LanaiDisassembler
    LanaiCodeGen
    LanaiAsmParser
    LanaiDesc
    LanaiInfo
    HexagonDisassembler
    HexagonCodeGen
    HexagonAsmParser
    HexagonDesc
    HexagonInfo
    BPFDisassembler
    BPFAsmParser
    BPFCodeGen
    BPFDesc
    BPFInfo
    AVRDisassembler
    AVRAsmParser
    AVRCodeGen
    AVRDesc
    AVRInfo
    ARMDisassembler
    ARMAsmParser
    ARMCodeGen
    ARMDesc
    ARMUtils
    ARMInfo
    AMDGPUTargetMCA
    AMDGPUDisassembler
    AMDGPUAsmParser
    AMDGPUCodeGen
    AMDGPUDesc
    AMDGPUUtils
    AMDGPUInfo
    AArch64Disassembler
    AArch64AsmParser
    AArch64CodeGen
    AArch64Desc
    AArch64Utils
    AArch64Info
    OrcDebugging
    OrcJIT
    WindowsDriver
    MCJIT
    JITLink
    Interpreter
    ExecutionEngine
    RuntimeDyld
    OrcTargetProcess
    OrcShared
    DWP
    DebugInfoLogicalView
    DebugInfoGSYM
    Option
    ObjectYAML
    ObjCopy
    MCA
    MCDisassembler
    LTO
    Passes
    HipStdPar
    CFGuard
    Coroutines
    ipo
    Vectorize
    Linker
    Instrumentation
    FrontendOpenMP
    FrontendOffloading
    FrontendOpenACC
    FrontendHLSL
    Extensions
    DWARFLinkerParallel
    DWARFLinker
    GlobalISel
    MIRParser
    AsmPrinter
    SelectionDAG
    CodeGen
    Target
    ObjCARCOpts
    CodeGenTypes
    IRPrinter
    InterfaceStub
    FileCheck
    FuzzMutate
    ScalarOpts
    InstCombine
    AggressiveInstCombine
    TransformUtils
    BitWriter
    Analysis
    ProfileData
    Symbolize
    DebugInfoBTF
    DebugInfoPDB
    DebugInfoMSF
    DebugInfoDWARF
    Object
    TextAPI
    MCParser
    IRReader
    AsmParser
    MC
    DebugInfoCodeView
    BitReader
    FuzzerCLI
    Core
    Remarks
    BitstreamReader
    BinaryFormat
    TargetParser
    TableGen
    Support
    Demangle
)

add_executable(helper bootstrap/helper.cc)
target_link_libraries(helper PRIVATE ${LLVM_LIBS})

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

add_custom_target(copy-lib ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_SOURCE_DIR}/lib/ ${CMAKE_BINARY_DIR}/lib/
    DEPENDS ${MY_TARGET})

set_source_files_properties(
  ${STAGE0_OBJ}
  PROPERTIES
  EXTERNAL_OBJECT true
  GENERATED true
)
target_link_libraries(stage0 PRIVATE ${LLVM_LIBS})


IF(CMAKE_BUILD_TYPE MATCHES Release)
    SET(OPT_LEVEL 3)
ELSE()
    SET(OPT_LEVEL 0)
ENDIF()

function(compile_stage PREV_STAGE CURR_STAGE)
    add_custom_target(
        ${CURR_STAGE}.o ALL
        COMMAND ${PREV_STAGE} ${MAIN_SRC_FILE} --emit obj -o  ${CMAKE_BINARY_DIR}/${CURR_STAGE}.o -O ${OPT_LEVEL} -I ${CMAKE_BINARY_DIR}/lib/
        DEPENDS ${PREV_STAGE}
    )
    add_executable(${CURR_STAGE} ${CMAKE_BINARY_DIR}/${CURR_STAGE}.o ${LLVM_BIND_SRC})
    set_source_files_properties(
        ${CMAKE_BINARY_DIR}/${CURR_STAGE}.o
        PROPERTIES
        EXTERNAL_OBJECT true
        GENERATED true
    )
    target_link_libraries(${CURR_STAGE} PRIVATE ${LLVM_LIBS})

endfunction()

compile_stage(stage0 stage1)
compile_stage(stage1 stage2)
compile_stage(stage2 flo)