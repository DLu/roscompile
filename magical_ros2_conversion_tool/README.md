# Magical ROS2 Conversion Tool

![Gif of Shia Lebeouf waving his fingers and saying Magic!](https://media.giphy.com/media/12NUbkX6p4xOO4/giphy.gif)

This tool will do a lot of the rote work involved in converting from ROS1 to ROS2.

It is invoked by calling `rosrun magical_ros2_conversion_tool ros2_conversion` which will then convert all packages found within the current folder.

Based on [the official Migration guide](https://index.ros.org/doc/ros2/Contributing/Migration-Guide/).

## Warning
Despite having magical in its name, this tool is not magic. In fact, your code is very likely to NOT compile after running this script. It is merely a blunt instrument for getting you part of the way to ROS2.

## Features
 * `package.xml`
    * Upgrades to at least version 2
    * Removes metapackage tag
    * Replace some ROS1 dependencies with their ROS2 equivalent.
 * Messages/Services/Actions
    * Use `builtin_interfaces` for `duration` and `time`
    * Forces `Header` to be preceded by `std_msgs/Header`
    * Upgrades to `package.xml` version 3
    * Uses new dependencies
    * Updates CMake
    * Forces C++14
 * Pure Python Packages
    * Remove CMake file
    * Change build type to `ament_python`
    * Some very minor Python code changes based on [this migration guide](https://index.ros.org/doc/ros2/Contributing/Migration-Guide-Python/)
 * CMake
    * Upgrade CMake to 3.5
    * Split the `find_package` command
    * Switch from catkin to ament
    * Remove catkin-specific logic from CMake
 * C++ Source Code
    * Does some general pattern recognition on C++ source code to use new `rclcpp/C++11` patterns.
