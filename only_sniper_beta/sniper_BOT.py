####################
# Sniper BOT 
# @Copyright 2022
# DEV Hyp3r-3y3
# version BETA 0.1.2
# ENJOY !!!
####################

import pandas as pd
import pandas_ta as ta
import pybit
import sys
import datetime
import requests
import time
import calendar
import re
import numpy as np
from datetime import datetime, timedelta, timezone
from pybit import usdt_perpetual
from timeit import default_timer
from FUNCTIONS import (
    get_base_currency,
    get_price_scale,
    get_dig_number,
    get_min_price,
    round_up,
    roundDown,
    round_down_to_multiple,
    round_up_to_multiple,
)

##########################
qty_usd = 200
timeframe_inMinuti = 5
atr_coefficent = 1.4
##########################

# PART 1 | Get the data
coppia = input("Enter coin: ").upper()
coppia = str(coppia + "USDT")
base_currency = str(get_base_currency(coppia))
price_scale = get_price_scale(base_currency)
dig_number = get_dig_number(base_currency)
multiple = float(get_min_price(base_currency))
sl_safe = 0
start_timer = default_timer() - (15 * 60)


def main():
    try:
        while True:
            global sl_safe
            global start_timer
            duration = default_timer() - start_timer
            now = datetime.utcnow()
            unixtime = calendar.timegm(now.utctimetuple())
            since = unixtime
            start = str(since - 200 * 60 * int(timeframe_inMinuti))

            # Download DataFrame actual TimeFrame
            url = (
                "https://api.bybit.com/public/linear/kline?symbol="
                + coppia
                + "&interval="
                + str(timeframe_inMinuti)
                + "&from="
                + str(start)
            )

            data = requests.get(url).json()
            D = pd.DataFrame(data["result"])

            marketprice = "https://api.bybit.com/v2/public/tickers?symbol=" + coppia

            res = requests.get(marketprice)
            data = res.json()

            # Get ATR
            atr = D.ta.atr()
            last_atr = atr.iloc[-1]

            # Get Marketprice, Bidprice, Askprice and Lastprice
            try:
                lastprice = float(data["result"][0]["last_price"])
                markprice = float(data["result"][0]["mark_price"])
                ask_price = float(data["result"][0]["ask_price"])
                bid_price = float(data["result"][0]["bid_price"])
                qty_coin = round(qty_usd / lastprice, dig_number)
            except:
                main()

            # Get RSI
            rsi = D.ta.rsi()
            last_rsi = rsi.iloc[-1]

            # Get BB std dev 3
            bb_3 = D.ta.bbands(length=20, std=3)
            last_bb_3 = bb_3.iloc[-1]

            # Get BB std dev 2
            bb_2 = D.ta.bbands(length=20, std=2)
            last_bb_2 = bb_2.iloc[-1]

            # SHOW INFO
            print("Checking position for", coppia + "...")
            print("RSI is", round(last_rsi, 2))
            print(
                "BB 3 are",
                round(last_bb_3["BBU_20_3.0"], 4),
                "and",
                round(last_bb_3["BBL_20_3.0"], 4),
            )
            print(
                "BB 2 are",
                round(last_bb_2["BBU_20_2.0"], 4),
                "and",
                round(last_bb_2["BBL_20_2.0"], 4),
            )
            print("LastPrice is", round(lastprice, 4))
            print("duration is", round(duration, 2))
            print("============================")

            # PART 2 | Program
            session_auth = usdt_perpetual.HTTP(
                endpoint="https://api.bybit.com",
                api_key="",
                api_secret="",
            )

            # Get actual posizion size
            positionSize = session_auth.my_position(symbol=coppia)
            positionSize_buy = positionSize["result"][0]["size"]
            positionSize_sell = positionSize["result"][1]["size"]
            try:
                last_order = session_auth.get_active_order(symbol=coppia, limit=1)
                last_order_status = last_order["result"]["data"][0]["order_status"]
            except:
                last_order_status = "Null"

            ### SNIPER MODE ###

            # Check if there are any opened position or order
            if (
                positionSize_buy == 0
                and positionSize_sell == 0
                and last_order_status != "New"
                and duration > (timeframe_inMinuti * 3 * 60)
            ):
                # Check if price is lower than BB and RSI is oversold
                if lastprice <= last_bb_3["BBL_20_3.0"] and last_rsi <= 30:
                    # Calculate SL with ATR
                    stop_loss = round_down_to_multiple(
                        lastprice - (last_atr * atr_coefficent), multiple
                    )
                    # Open LONG position
                    session_auth.place_active_order(
                        symbol=coppia,
                        order_type="Limit",
                        price=ask_price,
                        side="Buy",
                        qty=qty_coin,
                        time_in_force="GoodTillCancel",
                        reduce_only=False,
                        close_on_trigger=False,
                        stop_loss=stop_loss,
                    )
                    entry = ask_price
                    atr_div = round_up((last_atr / 4), d=price_scale)
                    atr_div2 = round_up((last_atr * atr_coefficent), d=price_scale)
                    sl_safe = round_up_to_multiple((entry + atr_div), multiple)
                    sl_safe2 = round_up_to_multiple((entry + atr_div2), multiple)
                    start_timer = default_timer()
                    print(" ")
                    print("OPENED LONG POSITION!", coppia)
                    print("sl safe 2 is", sl_safe2)
                    print(" ")
                    time.sleep((timeframe_inMinuti * 60))

                # Check if price is higher than BB and RSI is overbought
                elif lastprice >= last_bb_3["BBU_20_3.0"] and last_rsi >= 70:
                    # Calculate SL with ATR
                    stop_loss = round_up_to_multiple(
                        lastprice + (last_atr * atr_coefficent), multiple
                    )
                    # Open SHORT position
                    session_auth.place_active_order(
                        symbol=coppia,
                        order_type="Limit",
                        price=bid_price,
                        side="Sell",
                        qty=qty_coin,
                        time_in_force="GoodTillCancel",
                        reduce_only=False,
                        close_on_trigger=False,
                        stop_loss=stop_loss,
                    )
                    entry = bid_price
                    atr_div = round_up((last_atr / 4), d=price_scale)
                    atr_div2 = round_up((last_atr * atr_coefficent), d=price_scale)
                    sl_safe = round_down_to_multiple((entry - atr_div), multiple)
                    sl_safe2 = round_down_to_multiple((entry - atr_div2), multiple)
                    start_timer = default_timer()
                    print(" ")
                    print("OPENED SHORT POSITION!", coppia)
                    print("sl safe 2 is", sl_safe2)
                    print(" ")
                    time.sleep((timeframe_inMinuti * 60))

            # Move SL near entry (LONG)
            elif positionSize_buy != 0 and sl_safe != 0 and lastprice > sl_safe2:
                try:
                    session_auth.set_trading_stop(
                        symbol=coppia, side="Buy", stop_loss=sl_safe
                    )
                    sl_safe = 0
                    print("STOP LOSS moved near Entry Price !", coppia)
                except:
                    time.sleep(2.5)
                    session_auth.set_trading_stop(
                        symbol=coppia, side="Buy", stop_loss=sl_safe
                    )
                    sl_safe = 0
                    print("STOP LOSS moved near Entry Price !", coppia)

            # Move SL near entry (SHORT)
            elif positionSize_sell != 0 and sl_safe != 0 and lastprice < sl_safe2:
                try:
                    session_auth.set_trading_stop(
                        symbol=coppia, side="Sell", stop_loss=sl_safe
                    )
                    sl_safe = 0
                    print("STOP LOSS moved near Entry Price !", coppia)
                except:
                    time.sleep(2.5)
                    session_auth.set_trading_stop(
                        symbol=coppia, side="Sell", stop_loss=sl_safe
                    )
                    sl_safe = 0
                    print("STOP LOSS moved near Entry Price !", coppia)

            # Check if the price hit BB 2 LONG
            elif positionSize_buy != 0 and lastprice >= last_bb_2["BBU_20_2.0"]:
                try:
                    session_auth.set_trading_stop(
                        symbol=coppia, side="Buy", stop_loss=bid_price
                    )
                    tp_price = bid_price
                    print("LONG position reach Profit!", coppia)
                    print("Moving Stop loss...")
                except:
                    try:
                        session_auth.set_trading_stop(
                            symbol=coppia, side="Buy", take_profit=tp_price
                        )
                        print("LONG position closed in Profit!", coppia)

                    except:
                        main()

            # Check if the price hit BB 2 SHORT
            elif positionSize_sell != 0 and lastprice <= last_bb_2["BBL_20_2.0"]:
                try:
                    session_auth.set_trading_stop(
                        symbol=coppia, side="Sell", stop_loss=ask_price
                    )
                    tp_price = ask_price
                    print("SHORT position reach Profit!", coppia)
                    print("Moving Stop loss...")
                except:
                    try:
                        session_auth.set_trading_stop(
                            symbol=coppia, side="Sell", take_profit=tp_price
                        )
                        print("SHORT position closed in Profit!", coppia)
                    except:
                        main()
    except KeyboardInterrupt:
        sys.exit()
    except:
        time.sleep(2.5)
        main()


main()
