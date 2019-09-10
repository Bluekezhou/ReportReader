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


def filter_report(reports, blacklist):

    def check(report):
        total_count = 0
        for w in blacklist:
            count = report.count(w)
            total_count += count
            if count >= 3:
                return False

        if total_count >= 4:
            return False
        return True

    left = []
    filtered = []
    for index, rep in enumerate(reports):
        if not check(rep):
            filtered.append(index)
        else:
            left.append(index)

    return left, filtered


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
