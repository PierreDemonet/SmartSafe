cmake_minimum_required(VERSION 3.20)
project(pvrtx_optix LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python3 COMPONENTS Development REQUIRED)
find_package(pybind11 REQUIRED)

if(NOT DEFINED OPTIX_ROOT)
  message(FATAL_ERROR "OPTIX_ROOT must point to the OptiX SDK")
endif()

include_directories(${OPTIX_ROOT}/include)

add_library(pvrtx_optix MODULE bindings.cpp optix_impl.cu)
set_target_properties(pvrtx_optix PROPERTIES PREFIX "" OUTPUT_NAME "pvrtx_optix")

if (WIN32)
  set_target_properties(pvrtx_optix PROPERTIES SUFFIX ".pyd")
endif()

target_link_libraries(pvrtx_optix PRIVATE pybind11::module cuda)
