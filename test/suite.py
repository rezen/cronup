import os
import sys
sys.path.append("../..")

import unittest
from glob import glob
from operator import itemgetter

# @todo setup script
# mkdir -p /var/log/cronup
# mkdir -p /var/run/cronup
# touch /var/log/cronup.log
def module_name_to_class(module_name):
    class_name = module_name.replace('_', ' ')
    class_name = ''.join(x for x in class_name.title() if not x.isspace())
    return class_name

def get_test_cases(directory):

    # removing trailing slash
    if directory[-1:] is '/':
        directory = directory[0:-1]

    test_list = []

    # load any file with test prefix
    tests = glob(directory + '/test_*.py')

    for module_path in tests:
        module_name = os.path.basename(module_path).replace('.py', '')
        class_name  = module_name_to_class(module_name)

        mod = __import__(module_name, fromlist=[class_name])
        klass = getattr(mod, class_name)

        # add a default priotiy
        if not hasattr(klass, 'priority'):
            klass.priority = 1000
        
        test_list.append(klass)
    # lower priority number ... the sooner it gets loaded
    return sorted(test_list, key=lambda k: k.priority, reverse=False)

def run_tests():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    test_list = get_test_cases(dir_path)
    test_load = unittest.TestLoader()
    cases     = []

    for test in test_list:
        suite = test_load.loadTestsFromTestCase(test)
        cases.append(suite)
 
    test_suite = unittest.TestSuite(cases)

    unittest.TextTestRunner(verbosity=9).run(test_suite)

if __name__ == '__main__':
    run_tests()
    