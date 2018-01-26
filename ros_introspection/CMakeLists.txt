cmake_minimum_required(VERSION 2.8.3)
project(ros_introspection)

find_package(catkin REQUIRED)
catkin_python_setup()

catkin_package()

if (CATKIN_ENABLE_TESTING)
  find_package(catkin REQUIRED COMPONENTS roslint)
  roslint_python()
  roslint_add_test()
endif()
