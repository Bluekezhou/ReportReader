#!/usr/bin/env python
# encoding: utf-8

import npyscreen
import report
import re
import os
import curses
import pyperclip
import string
import argparse
import json

parser = argparse.ArgumentParser(prog="ReportReader")
parser.add_argument("-r", "--report", help="report file")
parser.add_argument("-s", "--source", help="kernel source")
parser.add_argument("-cfg", "--config", help="configuration")


# import sys
# sys.path.append('/home/test/Worktool/pycharm/helpers/pydev')
# try:
#     import pydevd
# except Exception as e:
#     pass
# import pydevd
# pydevd.settrace('localhost', port=4444, stdoutToServer=True, stderrToServer=True)

reports = []


class Config:
    KernelSource = None
    Report = None

    @staticmethod
    def check():
        if not Config.KernelSource:
            print("kernel source is required")
            os.exit(-1)

        if not Config.Report:
            print("ktsan report is required")
            os.exit(-1)


class BetterMultiLine(npyscreen.MultiLine):
    def __init__(self, *args, **kwargs):
        super(BetterMultiLine, self).__init__(*args, **kwargs)

    def handle_mouse_event(self, mouse_event):
        _, rel_x, rel_y, _, mask = self.interpret_mouse_event(mouse_event)
        self.cursor_line = rel_y // self._contained_widget_height + self.start_display_at

        if self.cursor_line >= len(self.values):
            return

        target_line = self.values[self.cursor_line]
        if mask == curses.BUTTON1_CLICKED:
            pyperclip.copy(target_line)

        elif mask == curses.BUTTON1_DOUBLE_CLICKED:
            start = end = rel_x
            while start > 0 and target_line[start - 1] not in string.whitespace:
                start -= 1
            while end < len(target_line) - 1 and \
                    target_line[end + 1] not in string.whitespace:
                end += 1

            pyperclip.copy(target_line[start: end+1])

        elif mask == curses.BUTTON1_TRIPLE_CLICKED:
            start = end = rel_x
            space = string.ascii_letters + string.digits + "_"
            while start > 0 and target_line[start - 1] in space:
                start -= 1

            while end < len(target_line) - 1 and target_line[end + 1] in space:
                end += 1

            pyperclip.copy(target_line[start: end+1])


class ReportLines(BetterMultiLine):
    def __init__(self, *args, **keywords):
        super(ReportLines, self).__init__(*args, **keywords)
        self.add_handlers({
            curses.KEY_RIGHT:   self.next_report,
            curses.KEY_LEFT:    self.previous_report,
            curses.ascii.LF:    self.handle_enter,
            "^N":               self.copy_to_clipboard,
        })
        self.report_index = 0

    def handle_enter(self, *args, **kwargs):
        self.update_source()

    def handle_mouse_event(self, mouse_event):
        super(ReportLines, self).handle_mouse_event(mouse_event)
        _, rel_x, rel_y, _, _ = self.interpret_mouse_event(mouse_event)
        self.cursor_line = rel_y // self._contained_widget_height + self.start_display_at

        if self.cursor_line >= len(self.values):
            return

        target_line = self.values[self.cursor_line]
        self.update_source(target_line)
        self.display()

    def next_report(self, *args, **kwargs):
        self.report_index += 1
        if self.report_index >= len(reports):
            return

        self.update_report(self.report_index)

    def previous_report(self, *args, **kwargs):
        self.report_index -= 1
        if self.report_index >= len(reports):
            return

        self.update_report(self.report_index)

    def copy_to_clipboard(self, *args, **kwargs):
        pyperclip.copy(reports[self.report_index])
        npyscreen.notify_confirm("report has been copied into clipboard")

    def update_source(self, line=''):
        if line == '':
            line = self.values[self.cursor_line]

        if not re.match(r"\s+\[.*?\S+:\d+", line):
            return

        line = line.strip()
        parts = line.split(" ")
        parts2 = parts[-1].split(":")
        source = parts2[0]
        line = int(parts2[1])
        self.parent.wSource.update_source(source, line)

    def update_report(self, index):
        self.report_index = index
        head = ["total report {}, current is {}".format(len(reports), index), " "]
        self.values = head
        self.values.extend(reports[index].splitlines())
        self.display()


class SourceLines(BetterMultiLine):
    def __init__(self, *args, **keywords):
        super(SourceLines, self).__init__(*args, **keywords)
        self.source = ''
        self.line = -1
        self.highlight_lines = []

    def update_source(self, source, line):
        source_file = os.path.join(Config.KernelSource, source)
        if not os.path.exists(source_file):
            return

        self.source = source_file
        self.line = line
        self.highlight_lines = []
        with open(source_file) as f:
            data = f.readlines()
            height = self.max_height // 2
            out = []
            for i in range(len(data)):
                tmp_line = data[i].replace("\t", " " * 4)
                if line == i+1:
                    out.append("=> %4d: %s" % (i+1, tmp_line))
                    self.start_display_at = i - height
                    self.cursor_line = i
                else:
                    out.append("   %4d: %s" % (i, tmp_line))

            self.values = out
            self.display()


class ReportBox(npyscreen.BoxTitle):
    _contained_widget = ReportLines

    def __init__(self, *args, **keywords):
          super(ReportBox, self).__init__(*args, **keywords)

    def update_report(self, index):
        self.entry_widget.update_report(index)


class SourceBox(npyscreen.BoxTitle):
    _contained_widget = SourceLines

    def __init__(self, *args, **keywords):
        super(SourceBox, self).__init__(*args, **keywords)

    def update_source(self, source, line):
        self.entry_widget.update_source(source, line)


class GotoEdit(npyscreen.TitleText):

    def __init__(self, *args, **keywords):
        super(GotoEdit, self).__init__(*args, **keywords)
        self.add_handlers({
            # "^G": self.read_number,
            curses.ascii.LF: self.goto_report
        })

    def goto_report(self, *args, **kwargs):
        data = self.value
        if not re.match(r'\d+', data):
            npyscreen.notify_confirm("Invalid data")
            return

        report_index = int(data)
        if report_index >= len(reports):
            size = len(reports)
            npyscreen.notify_confirm("Only {} reports, from 0 to {}".format(size, size-1))
            return

        if report_index < 0:
            npyscreen.notify_confirm("Index must equal to or greater than zero")
            return

        self.parent.wReport.update_report(report_index)


class App(npyscreen.NPSAppManaged):

    def onStart(self):
        main_form = npyscreen.FormBaseNew(name="Ktsan Report Reader", )

        main_form.wGoto = main_form.add(GotoEdit, name="Goto:")
        center = main_form.columns // 2
        main_form.wReport = main_form.add(ReportBox, name="Report:", max_height=None, max_width=center,
                                          relx=2, rely=3)
        main_form.wSource = main_form.add(SourceBox, name="Source:", max_height=None, max_width=None,
                                          relx=center+2, rely=3)

        main_form.wReport.update_report(0)

        main_form.edit()

    def onCleanExit(self):
        npyscreen.notify_wait("Goodbye!")


def parse_arguments():
    args = parser.parse_args()
    if args.source:
        Config.KernelSource = args.source

    if args.report:
        Config.Report = args.report

    if args.config:
        if not os.path.exists(args.config):
            print("{} not existed, check it")
            os._exit(-1)

        with open(args.config, "r") as f:
            data = f.read()
            cfg = json.loads(data)

        if "source" in cfg:
            if Config.KernelSource:
                print("duplicated source argument")
                os._exit(-1)
            else:
                Config.KernelSource = cfg['source']

        if "report" in cfg:
            if Config.Report:
                print("duplicated report argument")
                os._exit(-1)
            else:
                Config.Report = cfg['report']

    Config.check()


def main():
    global reports
    parse_arguments()
    reports = report.load_report(Config.Report)

    if not reports or len(reports) == 0:
        print("Warning!!! Empty report")
        return

    app = App()
    app.run()


if __name__ == "__main__":
    main()
