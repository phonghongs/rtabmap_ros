cmake_minimum_required(VERSION 3.5)
project(rtabmap_isaacsim)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch config params
   DESTINATION share/${PROJECT_NAME}
)

ament_package()
