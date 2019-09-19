#!/usr/bin/env python3
# coding=utf-8

import re


class ReportManager:

    def __init__(self):
        self.reports = None
        self.categories = {}
        self.mode = 'All'
        self.supported_mode = ["All"]
    
    def add_reports(self, reports):
        self.reports = reports
    
    def add_category(self, name, index):
        self.categories[name] = index
        self.supported_mode.append(name)

    def add_category_with_filter(self, chooser, args, select_name, unselect_name):
        select, unselect = chooser(*args)
        if select:
            self.add_category(select_name, select)

        if unselect:
            self.add_category(unselect_name, unselect)

        return select, unselect

    def check_index(self, index):
        size = self.get_mode_size()

        if 0 <= index < size:
            return True
        else:
            return False

    def get_real_index(self, index):
        if self.mode == "All":
            return index
        else:
            return self.categories[self.mode][index]

    def get_all_size(self):
        return len(self.reports)

    def get_mode_size(self):
        if self.mode == "All":
            size = len(self.reports)
        else:
            size = len(self.categories[self.mode])

        return size

    def get_report(self, index):
        real_index = self.get_real_index(index)
        if real_index == -1:
            return ''

        return self.reports[real_index]

    def set_mode(self, mode):
        if mode != "All" and mode not in self.categories:
            return False

        self.mode = mode
        return True
    
    def get_mode(self):
        return self.mode

    def get_supported_modes(self):
        return self.supported_mode


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
        if 'get new report' not in lines[index]:
            index += 1
            continue

        report = ""
        index += 1
        while index < len(lines) - 1:
            if 'get new report' in lines[index]:
                break

            report += lines[index]
            index += 1

        reports.append(report)

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


def filter_with_index(reports, index_list, checker):
    left = []
    filtered = []
    for index in index_list:
        if not checker(reports[index]):
            filtered.append(index)
        else:
            left.append(index)
    
    return left, filtered


def filter_without_index(reports, checker):
    left = []
    filtered = []
    for index, rep in enumerate(reports):
        if not checker(rep):
            filtered.append(index)
        else:
            left.append(index)

    return left, filtered


def find_related_thread(reports, index_list=None):
    """
    Report may show two unrelated threads, like thread 1 and thread 2000.
    From some point, it's unlikely to be two racy threads (just guess ~~).
    """
    def check(report):
        rep = parse_report(report)
        if 'tid' in rep:
            if abs(rep['tid'][0] - rep['tid'][1]) > 50:
                return False

        return True
    
    if index_list:
        return filter_with_index(reports, index_list, check)
    else:
        return filter_without_index(reports, check)


def find_race_write(reports, index_list=None):
    def check(report):
        out = re.findall("[Ww]rite at ", report)
        if len(out) >= 2:
            return True

        return False

    if index_list:
        return filter_with_index(reports, index_list, check)
    else:
        return filter_without_index(reports, check)


def parse_report(report):
    """
    Args:
        report -- a report string

    Return:
        a dict,
    """
    result = {}
    
    tids = re.findall(r'(?<=thread )\d+', report)
    if len(tids) >= 2:
        tids = [int(x) for x in tids]
        result['tid'] = tids
    
    return result


if __name__ == '__main__':
    reports = load_report("/home/test/Android/android-kernel/GOLDFISH/goldfish/report/ipv6.report")
    find_race_write(reports)
