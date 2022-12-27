#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2021  IBM Corporation
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
import json

import rclpy
import roslaunch
from std_msgs.msg import String
from nav_msgs.msg import OccupancyGrid

import mf_localization.resource_utils as resource_utils


class CurrentMapTopicRemapper:
    def __init__(self, node, local_map_frame, global_map_frame, frame_id_list):
        self.node = node
        self.local_map_frame = local_map_frame
        self.global_map_frame = global_map_frame
        self.frame_id_list = frame_id_list

        self.current_frame_id = None

        self.map_pub = self.node.create_publisher(OccupancyGrid, "map", queue_size=10, latch=True)
        self.current_frame_sub = self.node.create_subscription(String, "current_frame", self.current_frame_callback)

    def current_frame_callback(self, msg):
        current_frame_id = msg.data
        if current_frame_id not in self.frame_id_list:
            self.logger.error(F"Unknown frame_id [{current_frame_id}] was passed to multi_floor_map_server.")
            return

        if self.current_frame_id == current_frame_id:
            return

        self.current_map_sub = self.node.create_subscription(OccupancyGrid, current_frame_id, self.current_map_callback)
        self.current_frame_id = current_frame_id

    def current_map_callback(self, msg):
        if self.local_map_frame != self.global_map_frame:
            # if local_map_frame is separated from global_map_frame and can be attached to current_frame, assign local_map_frame to frame_id of the published /map topic
            msg.header.frame_id = self.local_map_frame
        self.map_pub.publish(msg)


def main():
    rclpy.init()
    node = rclpy.create_node('multi_floor_map_server')

    uuid = roslaunch.rlutil.get_or_generate_uuid(None, False)
    roslaunch.configure_logging(uuid)
    launch = roslaunch.scriptapi.ROSLaunch()
    launch.start()

    map_list = node.declare_parameter("map_list").value  # todo
    local_map_frame = node.declare_parameter("local_map_frame", "map").value
    global_map_frame = node.declare_parameter("global_map_frame", "map").value
    publish_map_topic = node.declare_parameter("publish_map_topic", True).value

    frame_id_list = []
    for i, map_dict in enumerate(map_list):
        frame_id = map_dict["frame_id"]
        frame_id_list.append(frame_id)
        map_filename = resource_utils.get_filename(map_dict["map_filename"])

        package = "map_server"
        executable = "map_server"
        node_name = executable + "_" + frame_id

        # todo
        node = roslaunch.core.Node(package, executable,
                                   name=node_name,
                                   namespace="/",
                                   remap_args=[("map", frame_id)],
                                   output="log"
                                   )
        node.args = map_filename + " " + "_frame_id:="+frame_id
        script = launch.launch(node)

    # remap the grid map of current_frame to "map" frame for navigation and visualization
    if publish_map_topic:
        multi_floor_map_server = CurrentMapTopicRemapper(node, local_map_frame, global_map_frame, frame_id_list)

    rclpy.spin(node)


if __name__ == "__main__":
    main()
