cmake_minimum_required(VERSION 2.8.3)
project(roscompile)
find_package(catkin REQUIRED COMPONENTS
  rospack
  rospy
  resource_retriever
)
catkin_python_setup()
catkin_package(CATKIN_DEPENDS resource_retriever)
catkin_install_python(PROGRAMS scripts/roscompile scripts/convert_to_format_2 test/format_cmakes.py
                      DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
install(FILES stdeb.cfg .gitignore README.md DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION})
install(FILES cmake.ignore package.ignore cmake_patterns.ignore DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/data)