#!/usr/bin/env python3
"""Simple test for FilterSegment class."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Import just the FilterSegment class directly
from stageflow.element import FilterSegment


def test_filter_segment():
    """Test FilterSegment functionality."""

    # Test parsing
    filter_seg = FilterSegment.parse('?id=="work_done"')
    print("Parsed filter:", filter_seg)

    if filter_seg:
        # Test matching
        match1 = filter_seg.matches({"id": "work_done", "name": "Task"})
        match2 = filter_seg.matches({"id": "other", "name": "Task"})
        print("Match work_done:", match1)
        print("Match other:", match2)

        # Test direct creation
        direct_filter = FilterSegment("status", "==", "active")
        match3 = direct_filter.matches({"status": "active"})
        match4 = direct_filter.matches({"status": "inactive"})
        print("Direct filter match active:", match3)
        print("Direct filter match inactive:", match4)

    # Test parsing different value types
    string_filter = FilterSegment.parse("?name=='test'")
    number_filter = FilterSegment.parse("?count==5")
    bool_filter = FilterSegment.parse("?active==true")
    null_filter = FilterSegment.parse("?value==null")

    print("String filter:", string_filter)
    print("Number filter:", number_filter)
    print("Bool filter:", bool_filter)
    print("Null filter:", null_filter)


if __name__ == "__main__":
    test_filter_segment()
