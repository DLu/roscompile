PYTHON_REPLACEMENTS = {
    r'\n(\s+)rospy.init_node\((.*)\)': '\n$0rclpy.init()\n$0node = rclpy.create_node($1)',
    r'rospy.Publisher\(([^\,]+), ([^\)]+)\)': 'node.create_publisher($1, $0)',
    r'rospy.Subscriber\(([^\,]+), ([^\,]+), ([^\)]+)\)': 'node.create_subscription($1, $0, $2)',
    r'rospy.Service\(([^\,]+), ([^\,]+), ([^\)]+)\)': 'node.create_service($1, $0, $2)',
}


def update_python(package):
    package.source_code.modify_with_patterns(PYTHON_REPLACEMENTS, language='python')
