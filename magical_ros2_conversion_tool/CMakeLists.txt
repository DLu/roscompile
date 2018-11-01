cmake_minimum_required(VERSION 3.0.2)
project(magical_ros2_conversion_tool)

find_package(catkin REQUIRED
    COMPONENTS ros_introspection roscompile
)
catkin_python_setup()

catkin_package(
    CATKIN_DEPENDS ros_introspection roscompile
)

if(CATKIN_ENABLE_TESTING)
  find_package(catkin REQUIRED COMPONENTS roslint)

  roslint_python()
  roslint_add_test()
endif()

catkin_install_python(
    PROGRAMS scripts/ros2_conversion
    DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
