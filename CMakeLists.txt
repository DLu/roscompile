cmake_minimum_required(VERSION 2.8.3)
project(roscompile)
find_package(catkin REQUIRED COMPONENTS
  rospack
  rospy
  resource_retriever
)
catkin_python_setup()
catkin_package(CATKIN_DEPENDS resource_retriever)
catkin_install_python(PROGRAMS scripts/roscompile DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})