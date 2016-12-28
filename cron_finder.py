#!/usr/bin/env python

from __future__ import print_function
import os
import glob

__VERSION__ = '1.0'

def locate_crons():
  crons = ['/etc/crontab']
  crons = crons + glob.glob('/etc/cron.**/*')
  crons = crons + glob.glob('/var/cron/tabs/*')
  crons = crons + glob.glob('/var/spool/cron/*')
  crons = crons + glob.glob('/usr/lib/cron/tabs/*')
  crons = crons + glob.glob('/var/spool/crontabs/*')
  crons = crons + glob.glob('/var/spool/cron/crontabs/*')
  return crons

def main():
  crons = locate_crons()
  crons.sort()
  for cron in crons:
     print(cron)

if __name__ == '__main__':
  main()
