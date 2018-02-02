roscompile is a tool for improving Catkin packages by fixing common errors and tweaking the style. To run, simply navigate to a folder containing the packages you'd like to tweak, and type
 `roscompile`

There are also some other useful scripts described at the bottom of this documentation.

# `roscompile` Features
## Dependencies
 * Checks for dependencies by looking in the source code, message, service, action and launch files.
 * Inserts build/run/test dependencies into your `package.xml`
 * Inserts dependencies into your `CMakeLists.txt` (in both the `find_package` and `catkin_package` commands)
 * Sorts lists of dependencies (in both `package.xml`/`CMakeLists.txt`)

## package.xml
 * Remove the empty export tag
 * Remove boiler-plate comments
 * Enforce tag ordering and tabbing
 * Reads the &lt;author> and &lt;maintainer> tags and allows you to programmatically replace them. (i.e. 'dlu', 'Dave Lu', 'David Lu'', 'dlu@TODO' can all become 'David V. Lu!!')
 * Update your metapackage dependencies

## CMakeLists.txt
 * Automatically looks for `msg`/`srv`/`action`/`dynamic_reconfigure` definitions and ensures they are properly built in the `CMakeLists.txt`
 * Enforces the ordering of the commands
 * Removes boiler-plate comments
 * Modifies the style of commands
 * Ensure all of your files are installed

## C++
 * Examines the `add_library` and `add_executable` commands in the `CMakeLists.txt` and ensures that they properly depend on `${catkin_EXPORTED_TARGETS}`, `${PKG_NAME_EXPORTED_TARGETS}` and `${catkin_LIBRARIES}`
 * Sets up the `include_directories` command and ensures your libraries are exported into the `catkin_package` command
 * If you use pluginlib, will search your code for PLUGINLIB_EXPORT_CLASS macros, and update your plugin xml accordingly.

## Python
 * If you have python code, will automatically generate setup.py for you.

## Configuration
 Located at `~/.ros/roscompile.yaml`

# Other Scripts
 * `convert_to_format_2` Convert the `manifest.xml` from format 1 to format 2.
 * `add_tests` Add roslaunch and/or roslint tests to your package, updating both the `manifest.xml` and `CMakeLists.txt`.
 * `add_compile_options` Script to add C++ compile flags to your `CMakeLists.txt`
