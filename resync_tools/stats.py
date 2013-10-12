"""Calculate and plot statistics for ResourceSync sites
"""

from resync.w3c_datetime import str_to_datetime,datetime_to_str

import matplotlib.pyplot as plt
import math
import sys
import os
import time

class Stats(object):

    def __init__(self, bins=100):
        self.lengths = []
        self.no_length = 0
        self.no_timestamp = 0
        self.oldest = 0
        self.newest = 0
        self.now = time.time()
        self.bins = bins 

    def testdata(self):
        """Return file name of test data set ResourceList
        """
        return( os.path.join(os.path.dirname(__file__), "testdata/resourcelist2.xml") )

    def extract(self,rl):
        lengths = []
        lengths_no_zero = []
        self.no_length = 0
        updates = []
        self.oldest = 0
        self.newest = 0
        self.no_timestamp = 0
        if (rl.md_at):
            ref_datetime = str_to_datetime(rl.md_at)
        else:
            ref_datetime = time.time()
        self.oldest = ref_datetime
        self.newest = ref_datetime
        for r in rl:
            if (r.length is not None):
                l = r.length / 1000.0
                lengths.append(l)
                if (l>0):
                    lengths_no_zero.append(math.log10(l))
            else:
                self.no_length+=1
            if (r.timestamp is not None):
                updated = (r.timestamp - ref_datetime) #seconds
                updates.append(updated)
                if (r.timestamp<self.oldest):
                    self.oldest=r.timestamp
                if (r.timestamp>self.newest):
                    self.newest=r.timestamp
            else:
                self.no_timestamp+=1
        # decide whether hours or days are better measure of updates
        range = self.newest - self.oldest # secods
        if (range > 160000):
            # >2 days -> use days
            updates_unit = 'days'
            factor = 86400
        elif (range > 7200):
            # >2 hours -> use hours
            updates_unit = 'hours'
            factor = 3600
        else:
            updates_unit = 'seconds'
            factor = 1
        if (factor != 1):
            for update in updates:
                update/=factor
        #
        return(lengths, lengths_no_zero, updates, updates_unit)
                
                
    def analyze(self,resourcelist,opt):

        (d,dnz,updates,updates_unit) = self.extract(resourcelist)
        fig = plt.figure(figsize=(10,8))
        title = "Statistics from %s at %s" %\
            (opt.resourcelist,datetime_to_str(self.now))
        fig.suptitle(title)
        f1l = fig.add_subplot(3,2,1)
        if (len(d)>0):
            f1l.hist(d, bins=self.bins)
            f1l.set_title('Histogram of resource sizes')
            f1l.set_xlabel('Size (kB)')
            f1l.set_ylabel('Number of resources')
        else:
            f1l.text(0.1,0.5,'No resources with length')
        f1r = fig.add_subplot(3,2,2)
        f1r.text(0.1,0.8,'%d resources' % len(resourcelist))
        f1r.text(0.1,0.6,"%d resources with length" % len(d))
        f1r.text(0.1,0.4,"%d resources with no length" % self.no_length)
        f2l = fig.add_subplot(3,2,3)
        if (len(dnz)>0):
            f2l.hist(dnz, bins=self.bins)
            f2l.set_title('Histogram of log10(resource sizes)')
            f2l.set_xlabel('log10( Size (kB) )')
            f2l.set_ylabel('Number of resources')
        else:
            f2l.text(0.1,0.5,'No resources with non-zero length')
        f2r = fig.add_subplot(3,2,4)
        f2r.text(0.1,0.8,'%d resources with non-zero length' % len(dnz))
        f3l = fig.add_subplot(3,2,5)
        if (len(updates)>0):
            f3l.hist(updates, bins=self.bins)
            f3l.set_title('Histogram of resource update times)')
            f3l.set_xlabel('Update time (%s)' % (updates_unit))
            f3l.set_ylabel('Number of resources')
        else:
            f3l.text(0.1,0.5,'No resources with timestamp')
        f3r = fig.add_subplot(3,2,6)
        f3r.text(0.1,0.8,"%d resources with timestamp" % len(updates))
        f3r.text(0.1,0.6,"oldest: %s" % datetime_to_str(self.oldest))
        f3r.text(0.1,0.4,"newest: %s" % datetime_to_str(self.newest))
        f3r.text(0.1,0.2,"%d resources with no timestamp" % self.no_timestamp)

        fig.subplots_adjust(left=None, bottom=None, right=None, top=None,
                            wspace=0.2, hspace=0.5)
        #
        # Write PDF or display in interactive viewer?
        if (opt.pdf):
            plt.savefig(opt.pdf, format='pdf', orientation='landscape')
            print "Plot saved as %s" % (opt.pdf)
        else:
            plt.show()
