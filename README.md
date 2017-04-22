roscompile is a tool that examines ROS (Catkin) packages, analyzes the files within, fixes common errors and tweaks the style. To run, simply navigate to a folder containing the packages you'd like to tweak, and type
 `rosrun roscompile roscompile`

# Features
## Dependencies
 * Checks for dependencies by looking in the source code and launch files.
 * Inserts build and run dependencies into your package.xml
 * Inserts dependencies into your CMakeLists.txt
 * Sorts lists of dependencies (in both package.xml/CMakeLists.txt)

## CMakeLists.txt
 * Automatically looks for msg/srv/action/dynamic_reconfigure definitions and ensures they are properly documented in the CMakeLists.txt
 * Enforces the ordering of the commands

## Legacy Comments
 * Removes auto-generated comments from your CMakeLists.txt and package.xml

## Python
 * If you have python code, will automatically generate setup.py for you.

## Plugins
 * If you use pluginlib, will search your code for PLUGINLIB_EXPORT_CLASS macros, and update your plugin xml accordingly.

## People
 * Reads the &lt;author> and &lt;maintainer> tags
 * Allows you to specify a canonical name and email address to replace all variants on your name
 * 'dlu', 'Dave Lu', 'David Lu'', 'dlu@TODO' can all become 'David V. Lu!!'

## Configuration
 * Each of these features can be disabled by changing the `~/.ros/roscompile.yaml` file, which is written after your first usage.
