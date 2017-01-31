"""Calculate and plot statistics for ResourceSync sites."""

from resync.w3c_datetime import str_to_datetime, datetime_to_str

import logging
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.backends.backend_pdf import PdfPages
import math
import sys
import os
import os.path
import time
import datetime
from builtins import input  # py2 safe input() compatible with py3


def items_by_value(d, ascending=False):
    """Return list if tuples from dict sorted by value."""
    return(sorted(d.items(), key=lambda x: x[1], reverse=(not ascending)))


class Stats(object):
    """Class to collect stats from a set of data."""

    def __init__(self, bins=100):
        """Initialize empty Stats object."""
        self.resource_count = 0
        self.sizes = []
        self.sizes_unit = 'bytes'
        self.sizes_max = 0
        self.sizes_log = []
        self.extensions_count = {}
        self.extensions_size = {}
        self.no_size = 0
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
        """Return uri extension or '.none'.

        Extension returned included preceding period.
        """
        (base, ext) = os.path.splitext(uri)
        if (ext in ['.gz', '.bz', '.bz2']):
            # Look at next extension instead
            ext = os.path.splitext(uri)[1]
        return(ext.lower() if ext else '.none')

    def extension_to_media_type(self, ext):
        """Get broad media type from extension."""
        ext = ext.lower()[1:]  # lowercase & remove leading period
        if (ext in ['tif', 'tiff', 'jpg', 'jpeg', 'png', 'gif', 'psd',
                    'bmp', 'wmf', 'pst', 'eps', 'ps', 'xmp', 'bmap',
                    'img']):
            media_type = "Image"
        elif (ext in ['mov', 'avi', 'mpg', 'mp4', 'qt', 'vob', 'flv',
                      'f4v', 'wmv', 'mpeg', 'm4v', 'm2v']):
            media_type = "Video"
        elif (ext in ['mp3', 'wav', 'vob', 'wma', 'flac', 'm4a', 'cda',
                      'aif', 'aiff', 'aifc']):
            media_type = "Audio"
        elif (ext in ['txt', 'htm', 'html', 'doc', 'docx', 'pdf',
                      'xls', 'xlsx', 'csv', 'tsv', 'rtf', 'tex',
                      'md']):
            media_type = "Text"
        elif (ext in ['xml', 'rdf', 'md5', 'pk', 'pkf']):
            media_type = "Metadata"
        else:
            media_type = "Unknown"
            logging.info("Mapping %s -> %s media type" % (ext, media_type))
        return(media_type)

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
            size = 0
            if (r.length is not None):
                size = r.length
                self.sizes.append(size)
                if (size > 0):
                    self.sizes_log.append(math.log10(size))
                if (size > self.sizes_max):
                    self.sizes_max = size
            else:
                self.no_size += 1
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
            self.extensions_size[ext] = self.extensions_size.get(ext, 0) + size

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

    def sizes_factor(self, size, max_numeric=2.0):
        """Decide size scaling factor and best unit."""
        size *= 1024.0 / max_numeric
        if (size > 1099511627776):
            return(1099511627776.0, 'TB')
        elif (size > 1073741824):
            return(1073741824.0, 'GB')
        elif (size > 1048576):
            return(1048576.0, 'MB')
        elif (size > 1024):
            return(1024.0, 'kB')
        else:
            return(1, 'bytes')

    def rescale_sizes(self):
        """Decide whether kB / MB / GB are best measure of sizes."""
        (factor, unit) = self.sizes_factor(self.sizes_max)
        self.sizes_unit = unit
        if (factor != 1):
            # Rescale the data (should perhaps do in-place?)
            self.sizes = [x / factor for x in self.sizes]

    def human_size(self, size):
        """Human readable resource size string."""
        (factor, unit) = self.sizes_factor(size, 900.0)
        return("%.1f %s" % ((size / factor), unit))

    def pie(self, subplot, data_dict, title=None, color_dict=None):
        """Plot pie chart from dict of label->value.

        See: https://pythonspot.com/matplotlib-pie-chart/
        """
        s = items_by_value(data_dict, ascending=True)
        # Get float values, show labels only for >1%
        values = [float(x[1]) for x in s]
        label_cutoff = sum(values) / 100.0
        labels = [x[0] if x[1] > label_cutoff else '' for x in s]
        if (color_dict is None):
            color_dict = {}
        # Either use existing color_dict or build a new one for
        # possible re-use (to get same colors for same label in
        # a new plot)
        colors = []
        cmap = ['red', 'blue', 'green', 'purple',
                'gold', 'lightskyblue', 'lightcoral']
        cn = 0
        for label in labels:
            if (label not in color_dict):
                col = cmap[cn % len(cmap)]
                color_dict[label] = col
                cn += 1
            colors.append(color_dict[label])
        subplot.axis('equal')
        subplot.pie(values, labels=labels, colors=colors, autopct='%1.1f%%')
        if title is not None:
            subplot.set_title(title)
        return(color_dict)

    def text_plot(self, subplot, lines, rows=30):
        """Write test lines to subplot.

        Parameters:
          lines - list of lines of text
          rows - sets line spacing for this many lines by default
        """
        subplot.axis('off')
        line_height = 1.0 / rows
        if (len(lines) > rows):
            line_height = 1.0 / len(lines)
        y = 1.0
        for line in lines:
            y -= line_height
            subplot.text(0.1, y, line)

    def summary_page1(self):
        """Plot summary stats."""
        fig = plt.figure(figsize=(10, 8))
        fig.suptitle(self.title + " (page 1)")
        rows = 3
        cols = 2
        f1l = fig.add_subplot(rows, cols, 1)
        if (len(self.sizes) > 0):
            f1l.hist(self.sizes, bins=self.bins)
            f1l.set_title('Histogram of resource sizes')
            f1l.set_xlabel('Size (%s)' % (self.sizes_unit))
            f1l.set_ylabel('Number of resources')
        else:
            f1l.text(0.1, 0.5, 'No resources with size')
        f1r = fig.add_subplot(rows, cols, 2)
        lines = ['%d resources' % self.resource_count,
                 '%d resources with size' % len(self.sizes),
                 '%d resources with no size (omitted)' % self.no_size,
                 'max resource size = %s' % (self.human_size(self.sizes_max))]
        self.text_plot(f1r, lines, rows=6)
        f2l = fig.add_subplot(rows, cols, 3)
        if (len(self.sizes_log) > 0):
            f2l.hist(self.sizes_log, bins=self.bins)
            f2l.set_title('Histogram of log10(resource sizes)')
            f2l.set_xlabel('log10( Size (bytes) )')
            f2l.set_ylabel('Number of resources')
        else:
            f2l.text(0.1, 0.5, 'No resources with non-zero size')
        f2r = fig.add_subplot(rows, cols, 4)
        lines = ['%d resources with non-zero size' % len(self.sizes_log),
                 '%d resources with zero size (omitted)' %
                 (len(self.sizes) - len(self.sizes_log))]
        self.text_plot(f2r, lines, rows=6)
        f3l = fig.add_subplot(rows, cols, 5)
        if (len(self.updates) > 0):
            f3l.hist(self.updates, bins=self.bins)
            f3l.set_title('Histogram of resource update times)')
            f3l.set_xlabel('Update time (%s before now)' % (self.updates_unit))
            f3l.set_ylabel('Number of resources')
        else:
            f3l.text(0.1, 0.5, 'No resources with timestamp')
        f3r = fig.add_subplot(rows, cols, 6)
        lines = ['%d resources with timestamp' % len(self.updates),
                 'oldest: %s' % datetime_to_str(self.oldest),
                 'newest: %s' % datetime_to_str(self.newest),
                 '%d resources with no timestamp (omitted)' %
                 self.no_timestamp]
        self.text_plot(f3r, lines, rows=6)
        fig.subplots_adjust(left=None, bottom=None, right=None, top=None,
                            wspace=0.5, hspace=0.5)

    def summary_page2(self):
        """Plot summary stats by file extension."""
        fig = plt.figure(figsize=(10, 8))
        fig.suptitle(self.title + " (page 2)")
        rows = 2
        cols = 2
        f1l = fig.add_subplot(rows, cols, 1)
        color_dict = self.pie(f1l, self.extensions_size,
                              title='Aggregate size by file extension')
        agg_size = sum(self.extensions_size.values())
        lines = ["Aggregate size = %s" % (self.human_size(agg_size))]
        n = 0
        for (k, v) in items_by_value(self.extensions_size):
            n += 1
            if (n > 25):
                lines.append("(and %d other extsnsions)" %
                             (len(self.extensions_size) - n + 1))
                break
            lines.append("%s : %s (%d items)" %
                         (k, self.human_size(v), self.extensions_count[k]))
        f1r = plt.subplot2grid((rows, cols), (0, 1), rowspan=2)
        self.text_plot(f1r, lines)
        f2l = fig.add_subplot(rows, cols, 3)
        self.pie(f2l, self.extensions_count,
                 title='Counts by file extension',
                 color_dict=color_dict)
        fig.subplots_adjust(left=None, bottom=None, right=None, top=None,
                            wspace=0.5, hspace=0.5)

    def summary_page3(self):
        """Plot summary stats by rough media types."""
        media_count = {}
        media_size = {}
        for ext in self.extensions_count:
            mt = self.extension_to_media_type(ext)
            media_count[mt] = media_count.get(mt, 0) + self.extensions_count[ext]
            media_size[mt] = media_size.get(mt, 0) + self.extensions_size[ext]
        color_dict = {'Video': 'red', 'Audio': 'blue',
                      'Image': 'green', 'Text': 'gold',
                      'Metadata': 'purple', 'Unknown': 'gray'}
        fig = plt.figure(figsize=(10, 8))
        fig.suptitle(self.title + " (page 3)")
        rows = 2
        cols = 2
        f1l = fig.add_subplot(rows, cols, 1)
        self.pie(f1l, media_size,
                 title='Aggregate size by media type',
                 color_dict=color_dict)
        fig.subplots_adjust(left=None, bottom=None, right=None, top=None,
                            wspace=0.5, hspace=0.5)
        f1r = plt.subplot2grid((rows, cols), (0, 1), rowspan=2)
        agg_size = sum(media_size.values())
        lines = ["Aggregate size = %s" % (self.human_size(agg_size))]
        for (k, v) in items_by_value(media_size):
            lines.append("%s : %s (%d items)" %
                         (k, self.human_size(v), media_count[k]))
        self.text_plot(f1r, lines)
        f2l = fig.add_subplot(rows, cols, 3)
        color_dict = self.pie(f2l, media_count,
                              title='Counts by media type',
                              color_dict=color_dict)

    def summarize(self, opt):
        """Gerenate comple summary in requested format."""
        source = opt.title + ' summary' if opt.title else 'Summary'
        now_str = datetime_to_str(self.now, True)
        self.title = "%s at %s" % (source, now_str)
        # Write PDF or display in interactive viewer?
        if (opt.pdf):
            with PdfPages(opt.pdf) as pdf:
                self.summary_page1()
                pdf.savefig()
                plt.close()
                self.summary_page2()
                pdf.savefig()
                plt.close()
                self.summary_page3()
                pdf.savefig()
                plt.close()
                d = pdf.infodict()
                d['Title'] = self.title
                d['CreationDate'] = datetime.datetime.today()
                d['ModDate'] = datetime.datetime.today()
            print("Plot saved as %s" % (opt.pdf))
        else:
            plt.ion()
            print("Showing page1.")
            self.summary_page1()
            plt.show()
            _ = input("Press [enter] for page2.")  # wait for input from the user
            plt.close()
            self.summary_page2()
            plt.show()
            _ = input("Press [enter] for page3.")
            plt.close()
            self.summary_page3()
            plt.show()
            _ = input("Press [enter] to exit.")

    def analyze_and_summarize(self, opt):
        """Extract and summarize stats for ResourceList."""
        self.rescale_updates()
        self.rescale_sizes()
        self.summarize(opt)
