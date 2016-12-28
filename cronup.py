#!/usr/bin/env python

import sys
import copy
import json
import time
import socket
import urllib
import urllib2
import getpass
import os.path
import logging
import traceback
from ConfigParser import ConfigParser
from subprocess import Popen, PIPE

__VERSION__ = '1.0'

"""
@links
https://pypi.python.org/pypi/cronwrap/1.4 <- most like
https://github.com/MatthiasKauer/croncoat
http://saltnlight5.blogspot.com/2014/06/a-simple-cron-wrapper-script-with.html
http://perfec.to/cronjobber/
http://habilis.net/cronic/
https://github.com/jobbyphp/jobby
http://steve-jansen.github.io/blog/2014/11/20/how-to-use-jenkins-to-monitor-cron-jobs/

@todo encrypt data?
@todo refactor pid methods into class
@todo have multiple notifiers
@todo timeout
@todo cleanup config
@todo config for adding plugins

@example 
./cronup.py -c /home/cats/backup.sh
./cronup.py -i backup -c /home/cats/backup.sh
./cronup.py -i cleaner -c 'ls /tmp/stale' -t "30s"
./cronup.py -i loud-cleaner -c 'ls /tmp/stale' -v

"""

root_dir = os.path.dirname(os.path.realpath(__file__))


def get_config():
  """ Get the config which includes details like log location & timeout."""
  conf_file = root_dir + '/cronup.conf'

  if 'CRONUP_CONF' in os.environ:
    conf_file =  os.environ['CRONUP_CONF']

  conf = ConfigParser()
  conf.read(conf_file)
  return {s:dict(conf.items(s)) for s in conf.sections()}

def cron_logger(config):
  """ Takes the config hash and sets up logger """
  logger = logging.getLogger('cron')
  logger.setLevel(logging.DEBUG)
  formatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', "%Y%m%d %H:%M:%S")

  if config['output'] == 'stdout':
    lh = logging.StreamHandler(sys.stdout)
  else:
    lh = logging.FileHandler(config['output'])
  
  lh.setLevel(logging.DEBUG)
  lh.setFormatter(formatter)

  logger.addHandler(lh)
  return logger

def slugifier(content):
  """ Takes string and converts to a slug """
  import re
  content = content.lower().strip()
  content = re.sub(r'^([^a-zA-Z0-9])+', '', content)
  content = re.sub(r'[^a-zA-Z0-9\-\_]+', '-', content)
  content = re.sub(r'([^a-zA-Z0-9])+$', '', content)
  return re.sub(r'\-{2,9}', '-', content)

def is_bad_idea(cmd):
  """ Checks commands for keywords of terrible things to do in a cron job """
  if type(cmd) == str:
    cmd = cmd.split(' ')
  
  bad = ['df', 'rm', 'dd', 'mkfs']
  return not set(bad).isdisjoint(cmd)

class CronProcess:

  def __init__(self, pid, conf, logger):
    self.pid = pid
    self.logger = logger
    self.id = conf['id']
    self.pidfile = '/var/run/cronup-' + conf['id'] + '.pid'
    conf['pidfile'] = self.pidfile
    self.conf = conf

  def was_stale(self):
    running_pid = self.get_pidfile_pid()
    return not self.is_pid_running(running_pid)

  def is_long_running(self):
    if 'long_running' in self.conf:
      return self.conf['long_running']

    running_pid = self.get_pidfile_pid()
    self.conf['long_running'] = (running_pid != self.pid and self.is_pid_running(running_pid))
    return self.conf['long_running']

  def is_pid_running(self, pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    else:
        return True

  def has_pidfile(self):
    return os.path.isfile(self.pidfile)

  def pidfile_create(self):
    self.logger.info('Creating pidfile for id:%s; pid:%s;' % (self.id, self.pid))
    with open(self.pidfile, 'w') as fh:
      fh.write(str(self.pid))

  def cleanup(self):
    os.remove(self.pidfile)
    self.logger.info('Cleaning up pidfile for id:%s; pidfile:%s;' % (self.id, self.pidfile))
    

  def age(self):
    now = time.time()
    past = os.path.getmtime(self.pidfile)
    return round(now - past, 3)

  def get_pidfile_pid(self):
    with open(self.pidfile, 'r') as fh:
      pid = fh.read()

      if pid != '':
        return pid
    return None

  def kill_pid(self, pid):
    try:
      os.kill(int(pid), 0)
    except:
      pass

  @staticmethod
  def create(run):
    """
    Create a pidfile with the provided configs
    identifier. Clean up pidfile is one already exists
    but there is no process running
    """
    pid = str(os.getpid())

    cron_process = CronProcess(pid, run, logger)
   
    if not cron_process.has_pidfile():
      cron_process.pidfile_create()

    if cron_process.is_long_running():
      message = 'Pidfile already exists and ps is running pid:%s;' % (cron_process.get_pidfile_pid())
  
      if run['verbose']:
        sys.stdout.write('[cronup] %s\n' % (message))

      logger.info(message)
      return cron_process

    if cron_process.was_stale():
      # Wasn't cleaned up last time
      logger.info('Stale pidfile:%s' % (cron_process.pidfile))
      cron_process.cleanup()
      cron_process.pidfile_create()

    return cron_process

def script_run(run):
  """
  Execute the provided script args and provides
  data which can be posted to a server or logged
  """
  start = time.time()

  data = {
    'hostname'  : socket.gethostname(),
    'user'      : getpass.getuser(),
    'cmd'       : run['cmd'],
    'exit_code' : 0,
    'out'       : '',
    'err'       : '',
    'time'      : 0,
    'date'      : time.strftime("%Y-%m-%d %H:%M:%S")
  }
  
  full_cmd =  ['/bin/bash', '-c', run['cmd']]
  
  p = Popen(full_cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
  data['out'], data['err'] = p.communicate()
  data['exit_code'] = p.returncode
  data['time'] = round(time.time() - start, 6)
  return data

def send_json(data, config):
  """
  Sends an http POST request with json with the script id
  exit_code, out, err, time, etc.
  """
  headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0',
    'Accept': 'application/json',
    'Accept-Charset': 'utf-8',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'X-Data-Source' : 'cronup'
  }

  req = urllib2.Request(config['url'], json.dumps(data), headers=headers)

  try:
    handle = urllib2.urlopen(req)
    res = handle.read()
  except urllib2.HTTPError, err:
    details = err.fp.read().replace('\n', '')
    logger.error('HTTP error sending json err:%s;' % (details))

def log_data(data, config):
  """ Log data to json """
  if config['nologs']:
    return

  d = copy.deepcopy(data)
  d['out'] = d['out'][0:600]

  logfile = config['logdir']  + 'job-' + config['id'] + '.log'
  logger.info('Logging job to id:%s; file:%s' % (config['id'], logfile))
  
  if not os.path.exists(logfile):
    with open(logfile, 'a'):
      os.utime(logfile, None)

  with open(logfile, 'a+0') as fh:
    fh.write("\n")
    fh.write(json.dumps(d))
    fh.close()

def main(run, handlers):
  """ Runs the command line """
  try:
    os.makedirs(run['logdir'])
  except OSError as err:
    pass

  if run['id'] is None:
    run['id'] = slugifier(run['cmd'])

  if is_bad_idea(run['cmd'].split(' ')):
    logger.warning('That looks like a bad idea rm:%s;' % (run['cmd']))
    return sys.exit(1)

  cron_process = CronProcess.create(run)

  try:
    if cron_process.is_long_running():
      age = cron_process.age()

      logger.info('Still running ... pidfile:%s; age:%s;' % (run['pidfile'], age))
      if age > run['timeout']:
        logger.warn('Passed timeout threshold pidfile:%s; age:%s;' % (run['pidfile'], age))

      return sys.exit(0)

    logger.info('Running script id:%s;' % (run['id']))

    data = script_run(run)

    if run['verbose']:
      sys.stderr.write(data['err'])
      sys.stdout.write('[cronup] Ran for ' + str(data['time']) + '\n\n')
      sys.stdout.write(data['out'])

    for handle in handlers:
      try:
        handle(data, run)
      except Exception as err:
        logger.error('Handler borked handle:%s; err:%s;' % (handle.__name__, err))

    logger.info('Ran id:%s; secs:%s; exit_code:%s;' % (run['id'], data['time'], data['exit_code']))
    
  except KeyboardInterrupt:
    logger.warning('Interupted')
  except Exception as err:
    logger.exception(err) 
    traceback.print_exc(file=sys.stderr)
  
  cron_process.cleanup()

  if run['verbose']:
    sys.exit(data['exit_code'])


if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser(description="A cron job wrapper that wraps jobs and enables better error reporting and command timeouts. Version %s" % __VERSION__)

  parser.add_argument('-c', '--cmd', help='Run a command | /cronup -c \'ls -la\'')
  parser.add_argument('-i', '--id', help='Give the script an identifier | /cronup -i db001-backups')
  parser.add_argument('-n', '--nologs', help='Disable logging script to fs | /cronup -n', action='store_true')
  parser.add_argument('-v', '--verbose', help='Print stdout/err and exit with code from command | /cronup -v', action='store_true')
  
  # @todo a timeout
  # parser.add_argument('-t', '--timeout', help='Set the maximum a script will run')
  args = parser.parse_args()

  # The cmd argument is required
  if args.cmd is None:
    parser.print_help()
    sys.exit(1)
  
  config = get_config()
  logger = cron_logger(config['settings'])

  # If it's empty fail
  if args.cmd.strip() is '':
    parser.print_help()
    sys.exit(1)

  run = copy.deepcopy(config['settings'])

  run['id'] = args.id
  run['cmd'] = '' + args.cmd
  run['verbose'] = args.verbose
  run['nologs'] = args.nologs
  run['logdir'] = os.path.join(run['logdir'], '')

  main(run, [
    send_json,
    log_data
  ])
