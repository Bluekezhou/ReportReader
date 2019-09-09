#!/usr/bin/env python
# encoding: utf-8

import npyscreen
import report
import re
import os
import curses
import pyperclip

reports = report.load_report("./ipv6.report")
import sys
sys.path.append('/home/test/Worktool/pycharm/helpers/pydev')
try:
    import pydevd
except Exception as e:
    pass

KernelSource = '/home/test/Android/android-kernel/GOLDFISH/goldfish'


class ReportLines(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(ReportLines, self).__init__(*args, **keywords)
        self.add_handlers({
            "^N": self.next_report,
            "^P": self.previous_report,
            "^L": self.copy_to_clipboard
        })
        self.report_index = 0

    def handle_mouse_event(self, mouse_event):
        mouse_id, rel_x, rel_y, z, bstate = self.interpret_mouse_event(mouse_event)
        self.cursor_line = rel_y // self._contained_widget_height + self.start_display_at
        if self.cursor_line < len(self.values):
            self.update_source(self.values[self.cursor_line])
            self.display()

    def next_report(self, *args, **kwargs):
        self.report_index += 1
        if self.report_index >= len(reports):
            return

        self.values = reports[self.report_index].splitlines()
        self.display()

    def previous_report(self, *args, **kwargs):
        self.report_index -= 1
        if self.report_index >= len(reports):
            return

        self.values = reports[self.report_index].splitlines()
        self.display()

    def copy_to_clipboard(self, *args, **kwargs):
        pyperclip.copy(reports[self.report_index])
        npyscreen.notify_confirm("report has been copied into clipboard")

    def update_source(self, line):
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
        self.values = reports[index].splitlines()
        self.display()


class SourceLines(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(SourceLines, self).__init__(*args, **keywords)
        self.source = ''
        self.line = -1

    def update_source(self, source, line):
        source_file = os.path.join(KernelSource, source)
        if not os.path.exists(source_file):
            return

        with open(source_file) as f:
            data = f.readlines()
            height = self.max_height // 2
            self.values = data[max(0, line - height): min(len(data), line + height)]
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


class TestApp(npyscreen.NPSApp):

    def main(self):
        main_form = npyscreen.FormBaseNew(name="Welcome to Npyscreen", )

        main_form.wGoto = main_form.add(GotoEdit, name="Goto:")
        center = main_form.columns // 2
        main_form.wReport = main_form.add(ReportBox, name="Report:", max_height=None, max_width=center, relx=2, rely=3)
        main_form.wSource = main_form.add(SourceBox, name="Source:", max_height=None, max_width=center - 6, relx=center + 2, rely=3)

        main_form.wReport.values = reports[0].splitlines()

        main_form.edit()


if __name__ == "__main__":
    import pydevd
    # pydevd.settrace('localhost', port=4444, stdoutToServer=True, stderrToServer=True)
    App = TestApp()
    App.run()
