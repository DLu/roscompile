import re

from ros_introspection.resource_list import MESSAGES, SERVICES

from roscompile.util import convert_to_caps_notation, convert_to_underscore_notation

ROS2_INCLUDE_PATTERN = '#include <%s/%s/%s.hpp>'

LOGGERS = {
    'ROS_DEBUG': 'RCLCPP_DEBUG',
    'ROS_INFO': 'RCLCPP_INFO',
    'ROS_ERROR': 'RCLCPP_ERROR',
    'ROS_WARN': 'RCLCPP_WARN'
}


def make_include_pattern(s):
    return r'#include\s*[<\\"]' + s + '[>\\"]'


FIRST_PASS = {
    r'( *)ros::init\(argc, argv, "([^"]*)"\);(\s+)ros::NodeHandle (\w+);':
        '$0rclcpp::init(argc, argv);$2auto $3 = rclcpp::Node::make_shared("$1");'
}

CPP_CODE_REPLACEMENTS = {
    make_include_pattern('ros/ros.h'): '#include "rclcpp/rclcpp.hpp"',
    'ros::Time': 'rclcpp::Time',
    'std_msgs::Time': 'builtin_interfaces::msg::Time',
    'std_msgs/time.h': 'builtin_interfaces/msg/time.hpp',
    'ros::Rate': 'rclcpp::Rate',
    'ros::Duration': 'rclcpp::Duration',
    r'ros::ok\(\)': 'rclcpp::ok()',
    r'( *)ros::init\(argc, argv, "([^"]*)"\);':
        '$0rclcpp::init(argc, argv);\n$0auto node = rclcpp::Node::make_shared("$1");',
    r'ros::spinOnce\(\);': 'rclcpp::spin_some(node);',
    r'ros::spin\(\);': 'rclcpp::spin(node);',
    'ros::NodeHandle': 'rclcpp::Node',
    'ros::Publisher (.*) = (.*)advertise(.*);': 'auto $0 = $1advertise$2;',
    'ros::Subscriber (.*) = (.*)subscribe(.*);': 'auto $0 = $1subscribe$2;',

    # boost stuff
    make_include_pattern('boost/shared_ptr.hpp'): '#include <memory>',
    'boost::shared_ptr': 'std::shared_ptr',
    make_include_pattern('boost/weak_ptr.hpp'): '#include <memory>',
    'boost::weak_ptr': 'std::weak_ptr',
    make_include_pattern('boost/thread/mutex.hpp'): '#include <mutex>',
    'boost::mutex': 'std::mutex',
    'boost::mutex::scoped_lock': 'std::unique_lock<std::mutex>',
    make_include_pattern('boost/unordered_map.hpp'): '#include <unordered_map>',
    'boost::unordered_map': 'std::unordered_map',
    make_include_pattern('boost/function.hpp'): '#include <functional>',
    'boost::function': 'std::function',

    # tf stuff
    make_include_pattern('tf/transform_listener.h'):
        '#include "tf2_ros/buffer.h"\n#include "tf2_ros/transform_listener.h"',
    'tf::TransformListener': 'tf2_ros::TransformListener',
    'tf::Stamped': 'tf2::Stamped',
    'tf::Pose': 'tf2::Pose',
    'tf::get': 'tf2::get',
}


def get_full_msg_dependencies_from_source(package):
    messages = set()
    for gen_type, full_list in [('msg', MESSAGES), ('srv', SERVICES)]:
        for pkg, gen_name in full_list:
            gen_pattern = re.compile(pkg + '.*' + gen_name)
            if package.source_code.search_for_pattern(gen_pattern):
                messages.add((pkg, gen_name, gen_type))
    return messages


def get_generator_based_replacements(package):
    service_replacements = {}
    generator_replacements = {}
    for pkg, msg, gen_type in get_full_msg_dependencies_from_source(package):
        key = make_include_pattern('%s/%s.h' % (pkg, msg))
        value = ROS2_INCLUDE_PATTERN % (pkg, gen_type, convert_to_underscore_notation(msg))
        generator_replacements[key] = value

        two_colons = '%s::%s' % (pkg, msg)
        four_colons = '%s::%s::%s' % (pkg, gen_type, msg)
        generator_replacements[two_colons] = four_colons

        generator_replacements['(' + msg + ')ConstPtr'] = '$0::ConstSharedPtr'
        generator_replacements['(' + msg + ')::ConstPtr'] = '$0::ConstSharedPtr'

        if gen_type == 'srv':
            key = r'bool ([^\(]+)\(\s*' + two_colons + r'::Request\s+&\s+([^,]+),\s+'
            key += two_colons + r'::Response\s+&\s+([^\)]+)\)'
            value = 'void $1(const std::shared_ptr<' + four_colons + '::Request> $2, '
            value += 'std::shared_ptr<' + four_colons + '::Response> $3)'
            service_replacements[key] = value
    return generator_replacements, service_replacements


def get_logger_replacements(package):
    LOGGER_REPLACEMENTS = {}
    PackageName = convert_to_caps_notation(package.name)
    for old_logger, new_logger in LOGGERS.items():
        LOGGER_REPLACEMENTS[old_logger + r'\('] = new_logger + '(rclcpp::get_logger("' + PackageName + '"), '
        # old_pattern = old_logger + '([_A-Z]*)\('
        LOGGER_REPLACEMENTS[old_logger + r'_NAMED\(([^,]+),'] = new_logger + '(rclcpp::get_logger($0),'
    return LOGGER_REPLACEMENTS


def update_cplusplus(package):
    generator_replacements, service_replacements = get_generator_based_replacements(package)
    package.source_code.modify_with_patterns(service_replacements)
    package.source_code.modify_with_patterns(generator_replacements)
    package.source_code.modify_with_patterns(get_logger_replacements(package))
    package.source_code.modify_with_patterns(FIRST_PASS)
    package.source_code.modify_with_patterns(CPP_CODE_REPLACEMENTS)
