cmake_minimum_required(VERSION 2.8.3)
project(roscompile)
find_package(catkin REQUIRED COMPONENTS
  rospack
  rospy
)
catkin_python_setup()
catkin_package()