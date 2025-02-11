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
os.environ['WPK'] = "0x03e6f9e8c358b0bdffc247fbf0958e8d334302bbc32e43a3eb92a482935e4cf0"
os.environ['WPK_CLOB_API_KEY'] = "cfb7a70c-f436-37af-e03e-3d9857f5a632"
os.environ['WPK_CLOB_SECRET'] = "Riz46sGqX1EJpw0FjTjGT1gP0LRPg59MUjYF4LeVAvU="
os.environ['WPK_CLOB_PASS_PHRASE'] = "aa85c119d29108b2c96108946958f95c98c149f043f0f2e9205cf7eae01107c4"

def run_trade_monitor():
    trade_monitor.main()

def run_trader():
    trader.run_trade_tailer()

if __name__ == "__main__":
    # Create separate processes for each function
    processes = [
        multiprocessing.Process(target=run_trade_monitor),
        multiprocessing.Process(target=run_trader)
    ]

    # Start each process
    for process in processes:
        process.start()
