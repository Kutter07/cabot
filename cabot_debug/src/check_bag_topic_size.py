#!/usr/bin/env python3

###############################################################################
# Copyright (c) 2019, 2022  Carnegie Mellon University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
###############################################################################

import os
import sys
import re
import numpy
import traceback
import multiprocessing
import yaml

from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
import rosbag2_py

from optparse import OptionParser
from matplotlib import pyplot as plt
from bisect import bisect

parser = OptionParser(usage="""
Example
{0} -f <bag file>                       # bagfile
{0} -f <bag file> -v                    # output all topics
""".format(sys.argv[0]))

parser.add_option('-f', '--file', type=str, help='bag file to be processed')
parser.add_option('-v', '--verbose', action='store_true', help='output all topics')
parser.add_option('-c', '--count', action='store_true', help='sort by count')


def get_rosbag_options(path, serialization_format='cdr'):
    data = yaml.safe_load(open(path+"/metadata.yaml"))
    storage_options = rosbag2_py.StorageOptions(
        uri=path,
        storage_id=data['rosbag2_bagfile_information']['storage_identifier'])

    converter_options = rosbag2_py.ConverterOptions(
        input_serialization_format=serialization_format,
        output_serialization_format=serialization_format)

    return storage_options, converter_options

(options, args) = parser.parse_args()

if not options.file:
    parser.print_help()
    sys.exit(0)

bagfilename = options.file
filename=os.path.splitext(os.path.split(bagfilename)[-1])[0]
storage_options, converter_options = get_rosbag_options(bagfilename)
reader = rosbag2_py.SequentialReader()
reader.open(storage_options, converter_options)

topic_types = reader.get_all_topics_and_types()
type_map = {topic_types[i].name: topic_types[i].type for i in range(len(topic_types))}

total = 0
sizes = {}
counts = {}
start = None
end = None

while reader.has_next():
    (topic, msg_data, t) = reader.read_next()
    if start is None:
        start = t
    end = t
    if topic not in sizes:
        sizes[topic] = 0
        counts[topic] = 0
    sizes[topic] += len(msg_data)
    counts[topic] += 1
    total += len(msg_data)

if options.count:
    sorted_dict = sorted(counts.items(), key=lambda item: item[1], reverse=True)
else:
    sorted_dict = sorted(sizes.items(), key=lambda item: item[1], reverse=True)

total = total/1024/1024
duration = (end-start)/1e9
rate = total/duration
print(F"{total:10.2f} MB in {duration:.2f} secs, {rate:10.2f} MB/s")
for (k, v) in sorted_dict:
    v = sizes[k]
    c = counts[k]
    if v < 1024:
        if options.verbose:
            print(F"{v:10.2f} B \t{c/duration:8.2f}Hz\t{k}")
    elif v < 1024*1024:
        if options.verbose:
            print(F"{v/1024:10.2f} KB\t{c/duration:8.2f}Hz\t{k}")
    else:
        print(F"{v/1024/1024:10.2f} MB\t{c/duration:8.2f}Hz\t{k}")


