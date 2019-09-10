#!/usr/bin/env python
# encoding: utf-8

import npyscreen
from report import load_report, filter_report
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


class Config:
    KernelSource = None
    Report = None
    Blacklist = None

    @staticmethod
    def check():
        if not Config.KernelSource:
            print("kernel source is required")
            os.exit(-1)

        if not Config.Report:
            print("ktsan report is required")
            os.exit(-1)


class Global:
    MODE_ALL = 0
    MODE_GOOD = 1
    MODE_BAD = 2
    Mode = MODE_ALL
    AllReport = None
    GoodReport = None    # index list
    BadReport = None     # index list
    CurrentIndex = None  # index list
    ModeName = {
        MODE_ALL: "All",
        MODE_GOOD: "Good",
        MODE_BAD: "Bad",
    }

    @staticmethod
    def check_index(index):
        if Global.Mode == Global.MODE_ALL:
            size = len(Global.AllReport)
        elif Global.Mode == Global.MODE_GOOD:
            size = len(Global.GoodReport)
        elif Global.Mode == Global.MODE_BAD:
            size = len(Global.BadReport)

        if 0 <= index <= size:
            return True

        return False

    @staticmethod
    def get_real_index(index):
        if not Global.check_index(index):
            return -1

        if Global.Mode == Global.MODE_ALL:
            return index
        elif Global.Mode == Global.MODE_GOOD:
            return Global.GoodReport[index]
        elif Global.Mode == Global.MODE_BAD:
            return Global.BadReport[index]

    @staticmethod
    def get_all_size():
        return len(Global.AllReport)

    @staticmethod
    def get_mode_size():
        if Global.Mode == Global.MODE_ALL:
            size = len(Global.AllReport)
        elif Global.Mode == Global.MODE_GOOD:
            size = len(Global.GoodReport)
        elif Global.Mode == Global.MODE_BAD:
            size = len(Global.BadReport)

        return size

    @staticmethod
    def get_report(index):
        if Global.Mode == Global.MODE_ALL:
            return Global.AllReport[index]
        elif Global.Mode == Global.MODE_GOOD:
            return Global.AllReport[Global.GoodReport[index]]
        elif Global.Mode == Global.MODE_BAD:
            return Global.AllReport[Global.BadReport[index]]

    @staticmethod
    def set_mode(mode):
        if mode not in [Global.MODE_ALL, Global.MODE_GOOD, Global.MODE_BAD]:
            return False

        Global.Mode = mode
        return True

    @staticmethod
    def get_mode_name():
        return Global.ModeName[Global.Mode]


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
        if not Global.check_index(self.report_index):
            return

        self.update_report(self.report_index)

    def previous_report(self, *args, **kwargs):
        self.report_index -= 1
        if not Global.check_index(self.report_index):
            return

        self.update_report(self.report_index)

    def copy_to_clipboard(self, *args, **kwargs):
        pyperclip.copy(Global.get_report(self.report_index))
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
        head = ["total: {}, mode: {}, mode size: {}, mode index {}, real index {}".format(
                    Global.get_all_size(), Global.get_mode_name(), Global.get_mode_size(),
                    self.report_index, Global.get_real_index(self.report_index)),
                " "]
        self.values = head
        self.values.extend(Global.get_report(index).splitlines())
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
        if not Global.check_index(report_index):
            size = Global.get_mode_size()
            npyscreen.notify_confirm("Only {} reports, from 0 to {}".format(size, size-1))
            return

        if report_index < 0:
            npyscreen.notify_confirm("Index must equal to or greater than zero")
            return

        self.parent.wReport.update_report(report_index)


class MainForm(npyscreen.FormBaseNew):

    def create(self):
        self.wGoto = self.add(GotoEdit, name="Goto:")
        center = self.columns // 2
        self.wReport = self.add(ReportBox, name="Report:", max_height=None, max_width=center,
                                          relx=2, rely=3)
        self.wSource = self.add(SourceBox, name="Source:", max_height=None, max_width=None,
                                          relx=center+2, rely=3)
        self.wReport.update_report(0)

        self.add_handlers({
            "^E": self.change_mode,
            "^G": self.goto_report,
        })

    def change_mode(self, *args, **kwargs):
        self.parentApp.switchForm("FORM_SELECT")

    def goto_report(self, *args, **kwargs):
        self.wGoto.edit()


class ModeSelectForm(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.modes = [Global.MODE_ALL, Global.MODE_GOOD, Global.MODE_BAD]
        self.wgSelect = self.add(npyscreen.TitleSelectOne, max_height=4, value=[0, ], name="Choose Mode",
                                        values=["All", "Good", "Bad"], scroll_exit=True)

    def on_ok(self):
        mode = self.modes[self.wgSelect.value[0]]
        Global.set_mode(mode)
        self.parentApp.main_form.wReport.update_report(0)
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class App(npyscreen.NPSAppManaged):

    def onStart(self):
        self.main_form = self.addForm("MAIN", MainForm)
        self.select_form = self.addForm("FORM_SELECT", ModeSelectForm)
        # mode_form = npyscreen.FormBaseNew(name="Select Mode")

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

        if "blacklist" in cfg:
            Config.Blacklist = cfg['blacklist']

    Config.check()


def main():
    parse_arguments()
    Global.AllReport = load_report(Config.Report)
    if not Global.AllReport:
        print("Warning!!! Empty report")
        return

    if Config.Blacklist:
        Global.GoodReport, Global.BadReport = filter_report(Global.AllReport, Config.Blacklist)

    app = App()
    Global._APP = app
    app.run()


if __name__ == "__main__":
    main()
