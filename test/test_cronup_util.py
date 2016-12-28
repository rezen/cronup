import sys
import unittest

sys.path.append("..")

from cronup import slugifier, is_bad_idea

class TestCronupUtil(unittest.TestCase):
    priority = 1

    def test_slugifier(self):
        self.assertEquals(slugifier('A adfd '), 'a-adfd')
        self.assertEquals(slugifier('ls -lah /var/log'), 'ls-lah-var-log')
        self.assertEquals(slugifier('~/home/bob/mysqldump --name=cats'), 'home-bob-mysqldump-name-cats')
        self.assertEquals(slugifier('./bin/cleanup --date=$(date)'), 'bin-cleanup-date-date')
    
    def test_is_bad_idea(self):
      self.assertTrue(is_bad_idea('rm -rf'))
      self.assertTrue(is_bad_idea('mkfs -t ext2 /dev/fd0'))
      self.assertTrue(is_bad_idea(['mkfs', '-t', 'ext2', '/dev/fd0']))
      self.assertTrue(is_bad_idea(['dd', '/var/www/html']))
      self.assertTrue(is_bad_idea(['df', '/dev/sbd1']))
      self.assertFalse(is_bad_idea('ls /var/log'))
      self.assertFalse(is_bad_idea('rmrf'))
      self.assertFalse(is_bad_idea('~/cmds/rm -rf'))

if __name__ == '__main__':
    unittest.main()