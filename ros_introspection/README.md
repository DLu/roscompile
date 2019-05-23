# ros_introspection

 `ros_introspection` is a library for looking at the files within a ROS package in a structured way.

You can specify the path directly.

```
from ros_introspection.package import Package
pkg = Package('/full/path/geometry_msgs')
```
or you can use the built-in crawler

```
from ros_introspection.util import get_packages

for package in get_packages('/home/dlu/catkin_work/src'):
    print(package)
```

If you want to look in the current folder, you don't need to specify a folder to `get_packages`.


## Package Structure

A package is path (where the `$PATH/package.xml` exists) and collection of sets of files.
 * **Key Metadata Files** `package.xml` (a.k.a. the manifest), `CMakeLists.txt` and sometimes `setup.py`.
 * **Source Code** Typical extensions: `.py`, `.cpp`, `.h`, `.hpp`, `.c`. Also things with a python hashbang.
 * **Generator Files** Messages, services, and actions
 * **Launch Files**
 * **Dynamic Reconfigure Configs** `cfg/*.cfg`
 * **Plugin Configurations** Usually a single xml file in the root.
 * **All Other Files** Including robot models, data files, configuration files.


## PackageXML
The manifest is
 * a parsed XML dom
 * a saved xml header/declaration
 * an optional version number
 * our guess of the standard tab size

## CMakeLists.txt
This file is parsed into a series of Commands, CommandGroups and whitespace/comment strings. CommandGroups are mini CMake objects (groups of commands) surrounded by a pair of matching tags, like `if/endif` or `foreach/endforeach`.

Commands have the form `command_name(sections*)`. Commands track their initial string representation to avoid needless formatting changes. Each Section is an optional initial section_name, followed by some number of tokens. Each Section also has a defined SectionStyle.

## Source Code
The source code is a collection of individual source code files. Each file has a language variable as well as a set of tags. Right now, possible tags include
 * `library` - C++ library file
 * `executable` - C++ executable file
 * `test` - Used only in tests

`setup.py` is not considered a source file.

## Generator Files (Messages, services and actions)
These files are parsed to determine their package dependencies.

## Launch Files
Launch files are parsed XML and are read-only. There is a flag for determining whether the launch file is for tests.

## Dynamic Reconfigure Configs
These files are not parsed, and only their filename is stored.

## Plugin Configurations
This XML configuration can be read and written depending on the needs of the `pluginlib` macro invocations.
