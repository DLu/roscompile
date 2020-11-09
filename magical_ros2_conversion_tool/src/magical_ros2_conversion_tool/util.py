import re

REPLACE_PACKAGES = {
    'tf': 'tf2_ros',
    'roscpp': 'rclcpp',
    'rostest': 'ament_cmake_gtest',
}

def convert_to_underscore_notation(name):
    # https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def convert_to_caps_notation(name):
    return ''.join([x.title() for x in name.split('_')])
