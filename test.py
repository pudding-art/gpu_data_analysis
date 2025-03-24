import unittest
import random
import logging
from gpu_analysis_v4 import main

class TestMainFunction(unittest.TestCase):
    def setUp(self):
        self.start_range = 4399234663920.413
        self.end_range = 4399245493255.027

    def test_main_with_random_times(self):

        start_time = random.uniform(self.start_range, self.end_range)  # 先生成 start_time

        # end_time = random.uniform(start_time, self.end_range)  # 确保 end_time > start_time

        base_time = 1735632360000000000
        start_time = start_time * 1e3 + base_time
        end_time = self.end_range * 1e3 + base_time

        trace_file = "trace.json"
        time_unit = "ns"

        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        main(trace_file, start_time, end_time, time_unit)

        self.assertTrue(True)

    # def test_main_with_invalid_times(self):
    #
    #     start_time = self.end_range + 1
    #     end_time = self.start_range - 1
    #     trace_file = "trace.json"
    #     time_unit = "ns"
    #
    #     with self.assertRaises(SystemExit):
    #         main(trace_file, start_time, end_time, time_unit) # exit

    def test_main_with_no_user_times(self):
        trace_file = "trace.json"
        time_unit = "ns"

        main(trace_file, None, None, time_unit)

        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()