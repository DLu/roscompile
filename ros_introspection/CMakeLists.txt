cmake_minimum_required(VERSION 3.0.2)
project(ros_introspection)

find_package(catkin REQUIRED COMPONENTS rosmsg)
catkin_python_setup()

catkin_package(
    CATKIN_DEPENDS rosmsg
)

if (CATKIN_ENABLE_TESTING)
  find_package(catkin REQUIRED COMPONENTS roslint)
  roslint_python()
  roslint_add_test()
endif()
catkin_install_python(PROGRAMS scripts/print_packages.py DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
