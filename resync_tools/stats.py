"""Calculate and plot statistics for ResourceSync sites."""

from resync.w3c_datetime import str_to_datetime, datetime_to_str

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import math
import sys
import os
import os.path
import time
import datetime
from builtins import input  # py2 safe input() compatible with py3


class Stats(object):
    """Class to collect stats from a set of data."""

    def __init__(self, bins=100):
        """Initialize empty Stats object."""
        self.resource_count = 0
        self.lengths = []
        self.lengths_log = []
        self.extensions_count = {}
        self.extensions_size = {}
        self.no_length = 0
        self.no_timestamp = 0
        self.oldest = 0
        self.newest = 0
        self.now = time.time()
        self.updates = []
        self.updates_unit = 'seconds'
        self.bins = bins
        self.title = ""

    def testdata(self):
        """Return file name of test data set ResourceList."""
        return(os.path.join(os.path.dirname(__file__), "testdata/resourcelist2.xml"))

    def extension(self, uri):
        """Return uri extension or 'none'."""
        ext = os.path.splitext(uri)[1]
        return(ext if ext else 'none')

    def extract(self, rl):
        """Extract stats from ResourceList.

        Will append data to collection for this object so we
        get aggegate stats if extract() is called on multiple
        ResourceLists.
        """
        if (rl.md_at):
            ref_datetime = str_to_datetime(rl.md_at)
        else:
            ref_datetime = time.time()
        self.resource_count += len(rl)
        for r in rl:
            l = 0
            if (r.length is not None):
                l = r.length / 1000.0
                self.lengths.append(l)
                if (l > 0):
                    self.lengths_log.append(math.log10(l))
            else:
                self.no_length += 1
            if (r.timestamp is not None):
                updated = (r.timestamp - ref_datetime)  # seconds
                self.updates.append(updated)
                if (self.oldest == 0 or r.timestamp < self.oldest):
                    self.oldest = r.timestamp
                if (self.newest == 0 or r.timestamp > self.newest):
                    self.newest = r.timestamp
            else:
                self.no_timestamp += 1
            # URI/file extensions as surrograte for media type
            ext = self.extension(r.uri)
            self.extensions_count[ext] = self.extensions_count.get(ext, 0) + 1
            self.extensions_size[ext] = self.extensions_size.get(ext, 0) + l

    def rescale_updates(self):
        """Decide whether hours or days are better measure of updates."""
        range = self.newest - self.oldest  # seconds
        if (range > 408800000):
            # >2 years -> use years
            self.updates_unit = 'years'
            factor = 86400 * 7 * 365
        elif (range > 33600000):
            # >2 months -> use months
            self.updates_unit = 'months'
            factor = 86400 * 7 * 365 / 12.0
        elif (range > 1120000):
            # >2 weeks -> use weeks
            self.updates_unit = 'weeks'
            factor = 86400 * 7
        elif (range > 160000):
            # >2 days -> use days
            self.updates_unit = 'days'
            factor = 86400
        elif (range > 7200):
            # >2 hours -> use hours
            self.updates_unit = 'hours'
            factor = 3600
        else:
            # updates_unit = 'seconds'
            return
        # Rescale the data (should perhaps do in-place?)
        self.updates = [x / factor for x in self.updates]

    def pie(self, subplot, data_dict, title=None):
        """Plot pie chart from dict of label->value.

        See: https://pythonspot.com/matplotlib-pie-chart/
        """
        s = sorted(data_dict.items(), key=lambda x: x[1])
        # FIXME - should have some limit on number of types to show
        values = [float(x[1]) for x in s]
        labels = [x[0] for x in s]
        subplot.axis('equal')
        subplot.pie(values, labels=labels, autopct='%1.1f%%')
        if title is not None:
            subplot.set_title(title)

    def summary_page1(self):
        """Plot summary stats."""
        fig = plt.figure(figsize=(10, 8))
        fig.suptitle(self.title + " (page 1)")
        rows = 3
        cols = 2
        f1l = fig.add_subplot(rows, cols, 1)
        if (len(self.lengths) > 0):
            f1l.hist(self.lengths, bins=self.bins)
            f1l.set_title('Histogram of resource sizes')
            f1l.set_xlabel('Size (kB)')
            f1l.set_ylabel('Number of resources')
        else:
            f1l.text(0.1, 0.5, 'No resources with length')
        f1r = fig.add_subplot(rows, cols, 2)
        f1r.axis('off')
        f1r.text(0.1, 0.8, '%d resources' % self.resource_count)
        f1r.text(0.1, 0.6, "%d resources with length" % len(self.lengths))
        f1r.text(0.1, 0.4, "%d resources with no length (omitted)" %
                 self.no_length)
        f2l = fig.add_subplot(rows, cols, 3)
        if (len(self.lengths_log) > 0):
            f2l.hist(self.lengths_log, bins=self.bins)
            f2l.set_title('Histogram of log10(resource sizes)')
            f2l.set_xlabel('log10( Size (kB) )')
            f2l.set_ylabel('Number of resources')
        else:
            f2l.text(0.1, 0.5, 'No resources with non-zero length')
        f2r = fig.add_subplot(rows, cols, 4)
        f2r.axis('off')
        f2r.text(0.1, 0.8, '%d resources with non-zero length' % len(self.lengths_log))
        f2r.text(0.1, 0.6, '%d resources with zero length (omitted)' %
                 (len(self.lengths) - len(self.lengths_log)))
        f3l = fig.add_subplot(rows, cols, 5)
        if (len(self.updates) > 0):
            f3l.hist(self.updates, bins=self.bins)
            f3l.set_title('Histogram of resource update times)')
            f3l.set_xlabel('Update time (%s before now)' % (self.updates_unit))
            f3l.set_ylabel('Number of resources')
        else:
            f3l.text(0.1, 0.5, 'No resources with timestamp')
        f3r = fig.add_subplot(rows, cols, 6)
        f3r.axis('off')
        f3r.text(0.1, 0.8, "%d resources with timestamp" % len(self.updates))
        f3r.text(0.1, 0.6, "oldest: %s" % datetime_to_str(self.oldest))
        f3r.text(0.1, 0.4, "newest: %s" % datetime_to_str(self.newest))
        f3r.text(0.1, 0.2, "%d resources with no timestamp (omitted)" %
                 self.no_timestamp)
        fig.subplots_adjust(left=None, bottom=None, right=None, top=None,
                            wspace=0.5, hspace=0.5)

    def summary_page2(self):
        """Plot summary stats by extension."""
        fig = plt.figure(figsize=(10, 8))
        fig.suptitle(self.title + " (page 2)")
        rows = 2
        cols = 2
        f1l = fig.add_subplot(rows, cols, 1)
        self.pie(f1l, self.extensions_count, 'Counts by extension')
        f2l = fig.add_subplot(rows, cols, 3)
        self.pie(f2l, self.extensions_size, 'Aggregate size by extension')
        fig.subplots_adjust(left=None, bottom=None, right=None, top=None,
                            wspace=0.5, hspace=0.5)

    def summarize(self, opt):
        """Gerenate comple summary in requested format."""
        source = opt.resourcelist
        now_str = datetime_to_str(self.now, True)
        self.title = "Summary for %s at %s" % (source, now_str)
        # Write PDF or display in interactive viewer?
        if (opt.pdf):
            with PdfPages(opt.pdf) as pdf:
                self.summary_page1()
                pdf.savefig()
                plt.close()
                self.summary_page2()
                pdf.savefig()
                plt.close()
                d = pdf.infodict()
                d['Title'] = title
                d['CreationDate'] = datetime.datetime.today()
                d['ModDate'] = datetime.datetime.today()
            print("Plot saved as %s" % (opt.pdf))
        else:
            plt.ion()
            self.summary_page1()
            plt.show()
            _ = input("Press [enter] to continue.")  # wait for input from the user
            plt.close()
            self.summary_page2()
            plt.show()
            _ = input("Press [enter] to continue.")

    def analyze_and_summarize(self, resourcelist, opt):
        """Extract and summarize stats for ResourceList."""
        self.extract(resourcelist)
        self.rescale_updates()
        self.summarize(opt)
