# Copyright (c) 2022  Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import tempfile
import traceback
import xml.dom.minidom
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription, Substitution
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription
from launch.actions import RegisterEventHandler
from launch.actions import LogInfo
from launch.actions import TimerAction
from launch.event_handlers import OnExecutionComplete
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, Command
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions


class AddStatePlugin(Substitution):
    def __init__(self, source_file):
        super().__init__()
        self.source_file = normalize_to_list_of_substitutions(source_file)

    def describe(self):
        return ""

    def perform(self, context):
        xml_filename = perform_substitutions(context, self.source_file)
        rewritten_xml = tempfile.NamedTemporaryFile(mode='w', delete=False,
                                                    prefix='sdf', suffix='.xml')
        try:
            sdf = xml.dom.minidom.parse(xml_filename)
            plugin = xml.dom.minidom.parseString("""
<plugin name="gazebo_ros_state" filename="libgazebo_ros_state.so">
  <ros>
    <namespace>/gazebo</namespace>
  </ros>
  <update_rate>1.0</update_rate>
</plugin>
            """)
            worlds = sdf.getElementsByTagName("world")
            if len(worlds) != 1:
                return xml_filename
            worlds[0].appendChild(plugin.firstChild)
            sdf.writexml(rewritten_xml)
            return rewritten_xml.name
        except:
            traceback.print_exc()
        return xml_filename


def generate_launch_description():
    gui = LaunchConfiguration('gui', default='true')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    urdf_file = LaunchConfiguration('urdf_file')
    world_file = LaunchConfiguration('world_file')
    wireless_config_file = LaunchConfiguration('wireless_config_file')

    rviz_conf = os.path.join(
        get_package_share_directory('cabot_gazebo'),
        "launch/test.rviz")

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', '/robot_description', '-entity', 'my_robot']
    )

    modified_world = AddStatePlugin(world_file)

    return LaunchDescription([
        DeclareLaunchArgument(
            'gui',
            default_value='false',
            description='Show Gazebo client and rviz2 if true'
        ),

        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'),

        DeclareLaunchArgument(
            'urdf_file',
            description='Robot URDF xacro file'
        ),

        DeclareLaunchArgument(
            'world_file',
            description='Gazebo world file to be open'
        ),

        DeclareLaunchArgument(
            'wireless_config_file',
            description='wireless config file'
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([get_package_share_directory('cabot_gazebo'), 
                                          '/launch/gazebo_wireless_helper.launch.py']),
            launch_arguments={
                'verbose': 'true',
                'wireless_config_file': wireless_config_file
            }.items()
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([get_package_share_directory('gazebo_ros'), 
                                          '/launch/gzserver.launch.py']),
            launch_arguments={
                'verbose': 'true',
                'world': modified_world
            }.items()
        ),

        LogInfo(
            msg=modified_world
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([get_package_share_directory('gazebo_ros'), 
                                          '/launch/gzclient.launch.py']),
            condition=IfCondition(gui),
            launch_arguments={
                'verbose': 'true'
            }.items()
        ),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time, 
                'robot_description': ParameterValue(
                    Command(['xacro ', urdf_file]), value_type=str
                )
            }]
        ),

        RegisterEventHandler(            
            OnExecutionComplete(
                target_action=spawn_entity,
                on_completion=[
                    LogInfo(msg='Spawn finished'),
                    Node(
                        condition=IfCondition(gui),              
                        package='rviz2',
                        executable='rviz2',
                        output='screen',
                        arguments=['-d', str(rviz_conf)]
                    )
                ]
            )
        ),

        TimerAction(
            period=5.0,
            actions=[spawn_entity],
        )

    ])