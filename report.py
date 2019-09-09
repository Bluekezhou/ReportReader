#!/usr/bin/env python3
# coding=utf-8

import re


def load_report(filepath):
    """
    Args:
        filepath -- report path

    Return:
        a report list, every element is a string
    """

    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except IOError:
        return

    reports = []
    index = 0
    while index < len(lines) - 1:
        if re.match(r"={30,50}", lines[index]):
            report = lines[index]
            index += 1
            while index < len(lines) - 1:
                report += lines[index]
                index += 1
                if re.match(r"=+", lines[index-1]):
                    reports.append(report)
                    break
        else:
            index += 1

    return reports


def parse_report(report):
    """
    Args:
        report -- a report string

    Return:
        a dict,
    """
    # result = {}
    #
    # lines = report.splitlines()
    # for line in lines:
    #     if 'data-race in' in line:
    #         func = line[line.indexOf()]
    pass


if __name__ == '__main__':
    load_report("./ipv6.report")
