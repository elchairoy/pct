'''
You can run all three bots in one terminal instance by executing this file.

You can also run every bot separately for easier testing and logic visualization
'''

import multiprocessing
import trade_tailer as trader
import trade_monitor
from nice_funcs import extract_wallet_ids
import os

user_address = '0x3E9aaA70CCA15Af564993bD8e89086F712619385'

if __name__ == "__main__":
    trade_monitor.main()
