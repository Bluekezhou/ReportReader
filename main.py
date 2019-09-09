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

parser = argparse.ArgumentParser(prog="ReportReader")
parser.add_argument("report", help="report file")


# import sys
# sys.path.append('/home/test/Worktool/pycharm/helpers/pydev')
# try:
#     import pydevd
# except Exception as e:
#     pass
# import pydevd
# pydevd.settrace('localhost', port=4444, stdoutToServer=True, stderrToServer=True)

reports = []
KernelSource = '/home/test/Android/android-kernel/GOLDFISH/goldfish'


class ReportLines(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(ReportLines, self).__init__(*args, **keywords)
        self.add_handlers({
            curses.KEY_RIGHT:   self.next_report,
            curses.KEY_LEFT:    self.previous_report,
            "^N":               self.copy_to_clipboard,
            curses.ascii.LF:    self.handle_enter
        })
        self.report_index = 0

    # def set_up_handlers(self):
    #     super(ReportLines, self).set_up_handlers()
    #     self.handlers.update({
    #                 curses.KEY_DOWN:    self.h_act_on_highlighted,
    #                 curses.KEY_UP:      self.h_act_on_highlighted,
    #             })

    def handle_enter(self, *args, **kwargs):
        self.update_source()

    def handle_mouse_event(self, mouse_event):
        mouse_id, rel_x, rel_y, z, bstate = self.interpret_mouse_event(mouse_event)
        self.cursor_line = rel_y // self._contained_widget_height + self.start_display_at

        if self.cursor_line < len(self.values):
            target_line = self.values[self.cursor_line]
            if bstate == curses.BUTTON1_CLICKED:
                pyperclip.copy(target_line)

            elif bstate == curses.BUTTON1_DOUBLE_CLICKED:
                start = end = rel_x
                while start > 0 and target_line[start - 1] not in string.whitespace:
                    start -= 1
                while end < len(target_line) - 1 and \
                        target_line[end + 1] not in string.whitespace:
                    end += 1

                pyperclip.copy(target_line[start: end])
                # npyscreen.notify_confirm(str(rel_x) + " " + target_line[start: end])

            self.update_source(target_line)
            self.display()

    # def actionHighlighted(self, act_on_this, key_press):
    #     self.update_source(act_on_this)

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
        head = [
            "total report {}, current is {}".format(len(reports), index),
            " "
            " "
        ]
        self.values = head
        self.values.extend(reports[index].splitlines())
        self.display()


class SourceLines(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(SourceLines, self).__init__(*args, **keywords)
        self.source = ''
        self.line = -1
        self.highlight_lines = []

    def update_source(self, source, line):
        source_file = os.path.join(KernelSource, source)
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

    # def update(self, clear=True):
    #     super(SourceLines, self).update(clear)
    #     line_attr = curses.A_NORMAL
    #     line_attr |= self.parent.theme_manager.findPair(self, 'CAUTION')
    #     for line_index in self.highlight_lines:
    #         line = self.values[line_index]
    #         attr_list =  self.make_attributes_list(line, line_attr)
    #         self.add_line(line_index, 0, line, attr_list, self.width-8)


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

    # def update(self, clear=True):


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
        main_form.wReport = main_form.add(ReportBox, name="Report:", max_height=None, max_width=center, relx=2, rely=3)
        main_form.wSource = main_form.add(SourceBox, name="Source:", max_height=None, max_width=center - 6, relx=center + 2, rely=3)

        main_form.wReport.update_report(0)

        main_form.edit()

    def onCleanExit(self):
        npyscreen.notify_wait("Goodbye!")


if __name__ == "__main__":
    args = parser.parse_args()
    reports = report.load_report(args.report)
    App = App()
    App.run()
