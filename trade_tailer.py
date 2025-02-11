'''
Script for handling further filtering of trades that are living in the tail_trades JSON
    - During a run of process_trades, if a trade does not meet certain requirements, the 'bot_executed'
        flag will be flipped to True, and on the next loop, the trade will be passed over

    - There is also a setable parameter 'too_long_ago_hours', which will drop trades
        that have a timestamp further out than your hours set

Trades that pass filtering will be used as arguments for a create_order function which will sign
    and trade the order out of the User's Proxy Wallet

All open positions will then be monitored and handled by the Risk Manager
'''

import os
import json
import time
import nice_funcs as n
from datetime import datetime, timedelta
from py_clob_client.exceptions import PolyApiException
from py_clob_client.clob_types import OrderArgs, OrderType
import math


# Function to execute trade using create_order
def create_order(client, price, size, side, asset):
    if size * price < 1:
        size = math.ceil(1 / price)
    order_args = OrderArgs(
        price=price,
        # make 1 for now
        size=size,
        side=side,
        token_id=asset
    )
    try:
        signed_order = client.create_order(order_args)
        resp = client.post_order(signed_order, OrderType.FOK)
        print(resp)
    except PolyApiException as e:
        print(f"Error creating order: {e}")

def kill_switch():
    pass

# Function to process trades
def process_trades(json_file_path, client, sleep_duration=60, too_long_ago_minutes=2):
    while not os.path.exists(json_file_path):
        print(f"File {json_file_path} not found. Waiting for {sleep_duration} seconds...")
        time.sleep(sleep_duration)

    # Load trades from JSON file
    with open(json_file_path, 'r') as file:
        trades = json.load(file)

    # Calculate the cutoff timestamp
    cutoff_time = datetime.now() - timedelta(minutes=too_long_ago_minutes)
    cutoff_timestamp = int(cutoff_time.timestamp())

    # Iterate over each trade in the JSON data
    for trade in reversed(trades):
        # print(trade)
        # Check if the bot_executed flag is False
                # Check if the trade is recent enough and bot_executed flag is False and trade type is 'TRADE'
        if (
            trade['timestamp'] >= cutoff_timestamp and
            'bot_executed' in trade and
            trade['bot_executed'] is False and 
            trade['type'] == 'TRADE'
        ):
        # if 'bot_executed' in trade and trade['bot_executed'] is False and trade['type'] == 'TRADE':
        # if not trade.get('bot_executed', False):  # Default to True if key is missing

            my_balance = n.get_wallet_balance('0x40C3aB7B90438ebD80bf313F4B0d9C31410Df4E9')
            price = trade['price'] + 0.01
            print(f"Market Title: {trade['title']}")
            print(f"current market price is {price}")
            # price = trade['price']
            size = trade['size']
            if size * price > 100:
                size = size / 1000
            else:
                trade['bot_executed'] = True
                with open(json_file_path, 'w') as file:
                    json.dump(trades, file, indent=4)
                continue

            side = trade['side']
            asset = trade['asset']

            user_address='0x40C3aB7B90438ebD80bf313F4B0d9C31410Df4E9'
            active_positions = n.fetch_user_positions(user_address, limit = 500)
            print(active_positions.empty)
            # active_positions = n.get_active_positions(n.fetch_user_positions(user_address, limit = 500))

            try:
                if price >= 0.90 or price <= 0.05:
                    print('Not enough movement range to validate position, passing on trade')
                    # Update the trade status to prevent re-execution
                    trade['bot_executed'] = True
                    # Save the immediate update back to JSON file
                    with open(json_file_path, 'w') as file:
                        json.dump(trades, file, indent=4)
                    # Move to the next trade by using 'continue' or exiting this iteration
                    continue  # or continue if this is inside a loop

                # Check if active_positions DataFrame is not empty and has the 'asset' column
                elif not active_positions.empty and 'asset' in active_positions.columns:
                    # Check if the asset is already in active positions and the value is grater than 5$
                    if active_positions['asset'].eq(trade['asset']).any() and active_positions.loc[active_positions['asset'] == trade['asset'], 'initialValue'].values[0] > 5:
                        print('Already in position, skipping trade')
                        # Update the trade status to prevent re-execution
                        trade['bot_executed'] = True
                        # Save the immediate update back to JSON file
                        with open(json_file_path, 'w') as file:
                            json.dump(trades, file, indent=4)
                    else:
                        # Attempt to execute the trade
                        # check if we already have the opposite position (same conditionId and diff asset)
                        conditionId = trade['conditionId']
                        asset = trade['asset']
                        if active_positions['conditionId'].eq(conditionId).any():
                            if active_positions.loc[active_positions['conditionId'] == conditionId, 'asset'].values[0] != asset:
                                # sell the opposite position
                                create_order(client, 1 - price, size, 'SELL', active_positions.loc[active_positions['conditionId'] == conditionId, 'asset'].values[0])
                        else:
                            create_order(client, price, size, side, asset)
                            # Update the trade status to prevent re-execution
                            trade['bot_executed'] = True
                            # Save the immediate update back to JSON file
                            with open(json_file_path, 'w') as file:
                                json.dump(trades, file, indent=4)

                else:
                    print('No active position, creating trade...')
                    create_order(client, price, size, side, asset)
                    trade['bot_executed'] = True

                    # Save the immediate update back to JSON file
                    with open(json_file_path, 'w') as file:
                        json.dump(trades, file, indent=4)

            except PolyApiException as e:
                
                error_message = str(e)

                # Check if the error message matches the specific insufficient balance/allowance error
                if "not enough balance / allowance" in error_message:
                    print(f"Error: {e}. Sleeping for {sleep_duration} seconds.")
                    time.sleep(sleep_duration)
                    # Continue to monitor trades without stopping the function
                    continue
                
                # Check if the error message matches the minimum size requirement error
                elif "lower than the minimum" in error_message: 
                    print("Current risk parameters do not allow you to make this trade.")
                    trade['bot_executed'] = True

                    # Save the immediate update back to JSON file
                    with open(json_file_path, 'w') as file:
                        json.dump(trades, file, indent=4)
                    # Continue to the next trade without executing
                    continue

                else:
                    # Re-raise the exception if it's not an error we're handling
                    raise

        # Save the JSON file if bot_executed is already True or trade type is not 'TRADE'
        else:
            with open(json_file_path, 'w') as file:
                json.dump(trades, file, indent=4)

    print("All trades scanned, and updated or passed. Sleeping for 30 seconds.")
    print('----------------------------------------------------------------------')
    time.sleep(30)  # Pause before the next iteration


def run_trade_tailer():
    json_file_path = 'tail_trades.json'
    client = n.create_clob_client('0x40C3aB7B90438ebD80bf313F4B0d9C31410Df4E9')
    # Run the process_trades function continuously in a loop
    while True:
        process_trades(json_file_path, client)
        
# Example usage
if __name__ == "__main__":

    # Replace with the path to your JSON file
    json_file_path = 'tail_trades.json'
    
    client = n.create_clob_client('0x40C3aB7B90438ebD80bf313F4B0d9C31410Df4E9')
    # Run the process_trades function continuously in a loop
    while True:
        process_trades(json_file_path, client)


