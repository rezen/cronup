import os
import sys
import signal
import unittest
from subprocess import Popen, PIPE
import multiprocessing as mp
from time import sleep
import random

# http://jtushman.github.io/blog/2014/01/14/python-%7C-multiprocessing-and-interrupts/
dir_path = os.path.dirname(os.path.realpath(__file__))

def test_exec(args):
  (name, asleep) = args
  signal.signal(signal.SIGINT, signal.SIG_IGN)

  data = {}
  test_env = os.environ.copy()
  test_env['CRONUP_CONF'] = dir_path + '/test.conf'
  full_cmd = ['python', dir_path + '/../cronup.py', '-c', 'sleep ' + asleep + ' && echo meow', '-i', name, '-v']
  p = Popen(full_cmd,  env=test_env, stdin=PIPE, stdout=PIPE, stderr=PIPE)
  data['out'], data['err'] = p.communicate()
  data['exit_code'] = p.returncode
  return data

counter = 0

def handle_delay(args, asleep):
  sleep(asleep)
  return test_exec(args)

# We want the second exec to be delayed
def with_delay(args, asleep=0):
  return lambda: handle_delay(args, asleep)

class TestCronupIntegration(unittest.TestCase):

  """
  def test_still_running(self):
    pool = mp.Pool(2)

    try:
      results = pool.map(lambda fn: fn(), [with_delay(('zing', '4')), with_delay(('zing', '1'), 1)])
      self.assertEqual(results[0]['exit_code'], 0)
      self.assertTrue('already exists' in results[1]['out'], msg="Expected exists, not: %s" % results[1]['out'])
    except KeyboardInterrupt:
      pool.terminate()
      pool.join()

  """
  def test_lots_running(self):
    os.remove('./tmp/cronup.log')

    # You should never have that many crons going at the same time, but just in case
    max_processes = 200
    numbers = list(range(1, max_processes))
    ids = [('zing-' + str(i), '1') for i in numbers]

    pool = mp.Pool(max_processes)
   
    try:
      results = pool.map(test_exec, ids)
    except KeyboardInterrupt:
      pool.terminate()
      pool.join()
   

    # Confirming log files were created
    self.assertTrue(os.path.isfile('./tmp/cronup/job-zing-15.log'))
    self.assertTrue(os.path.isfile('./tmp/cronup/job-zing-26.log'))
    self.assertTrue(os.path.isfile('./tmp/cronup/job-zing-42.log'))
    self.assertTrue(os.path.isfile('./tmp/cronup/job-zing-79.log'))
    self.assertTrue(os.path.isfile('./tmp/cronup.log'))

    # Confirm the log has message indicating start of process
    with open('./tmp/cronup.log') as fh:
      content = fh.read()
      for (id, _) in ids:
        line = 'Running script id:%s' % id
        self.assertTrue(line in content, msg="Could not find log start for id %s" % id)

if __name__ == '__main__':
  unittest.main()

# ps a | grep cronup | grep -v grep | cut -d' ' -f1 | xargs -I{} kill -KILL {}
