#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
#
# This script is licensed under GNU GPL version 2.0 or above
# (c) 2021 Antonio J. Delgado
# Minig control based on enegy prices

import sys
import os
import logging
import click
import click_config_file
from logging.handlers import SysLogHandler
import requests
import json
from datetime import datetime
from time import mktime
import uuid
import hmac
from hashlib import sha256

class mining_control:

    def __init__(self, debug_level, log_file, price_limit, api_key, api_secret, organization_id, rig_id):
        ''' Initial function called when object is created '''
        self.debug_level = debug_level
        self.price_limit = price_limit
        self.api_key = api_key
        self.api_secret = api_secret
        self.organization_id = organization_id
        self.rig_id = rig_id
        if log_file is None:
            log_file = os.path.join(os.environ.get('HOME', os.environ.get('USERPROFILE', os.getcwd())), 'log', 'mining_control.log')
        self.log_file = log_file
        self._init_log()

        self.get_energy_prices()

        self.get_rig_statuses()

    def _init_log(self):
        ''' Initialize log object '''
        self._log = logging.getLogger("mining_control")
        self._log.setLevel(logging.DEBUG)

        sysloghandler = SysLogHandler()
        sysloghandler.setLevel(logging.DEBUG)
        self._log.addHandler(sysloghandler)

        streamhandler = logging.StreamHandler(sys.stdout)
        streamhandler.setLevel(logging.getLevelName(self.debug_level))
        self._log.addHandler(streamhandler)

        if self.log_file is not None:
            log_file = self.log_file
        else:
            home_folder = os.environ.get('HOME', os.environ.get('USERPROFILE', ''))
            log_folder = os.path.join(home_folder, "log")
            log_file = os.path.join(log_folder, "mining_control.log")

        if not os.path.exists(os.path.dirname(log_file)):
            os.mkdir(os.path.dirname(log_file))

        filehandler = logging.handlers.RotatingFileHandler(log_file, maxBytes=102400000)
        # create formatter
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
        filehandler.setFormatter(formatter)
        filehandler.setLevel(logging.DEBUG)
        self._log.addHandler(filehandler)
        return True

    def get_energy_prices(self):
        url="https://sahko.tk/api.php"
        self.session=requests.Session()
        result = self.session.post(url, data={'mode':'get_prices'})
        self.energy_prices = json.loads(result.text)
        self._log.debug("Prices: %s" % json.dumps(self.energy_prices))
        if float(self.energy_prices['now']) > self.price_limit:
            self._log.info(f"Current energy price ({self.energy_prices['now']} ¢/kWh) exceeds our limit of {self.price_limit}, setting desire state of the mining STOP.")
            self.desire_state = 'STOPPED'
            self.action = 'STOP'
        else:
            self._log.info(f"Current energy price ({self.energy_prices['now']} ¢/kWh) does not exceed our limit of {self.price_limit}, setting desire state of the mining START.")
            self.desire_state = 'MINING'
            self.action = 'START'
    
    def get_rig_statuses(self):
        if self.debug_level.lower() == 'debug':
            verbose = True
        else:
            verbose = False
        nh = nicehash_private_api(host='https://api2.nicehash.com', organisation_id=self.organization_id, key=self.api_key, secret=self.api_secret, verbose=verbose)
        rig_statuses = nh.get_rig_status(self.rig_id)
        print(json.dumps(rig_statuses, indent=2))
        for rig in rig_statuses['miningRigs']:
            print(f"Rig '{rig['rigId']}' status is '{rig['minerStatus']}'")
            if rig['minerStatus'] != self.desire_state:
                self._log.info(f"Switching state of the rig '{self.rig_id}' with the action '{self.action}'.")
                result=nh.set_rig_status(self.rig_id, self.action)
                if result['success']:
                    self._log.info(f"Switched successfully. {result}")
                else:
                    self._log.error(f"There was an error switching the mining state. {result}")


class nicehash_private_api:

    def __init__(self, host, organisation_id, key, secret, verbose=False):
        self.key = key
        self.secret = secret
        self.organisation_id = organisation_id
        self.host = host
        self.verbose = verbose

    def request(self, method, path, query, body):

        xtime = self.get_epoch_ms_from_now()
        xnonce = str(uuid.uuid4())

        message = bytearray(self.key, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(str(xtime), 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(xnonce, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(self.organisation_id, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(method, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(path, 'utf-8')
        message += bytearray('\x00', 'utf-8')
        message += bytearray(query, 'utf-8')

        if body:
            body_json = json.dumps(body)
            message += bytearray('\x00', 'utf-8')
            message += bytearray(body_json, 'utf-8')

        digest = hmac.new(bytearray(self.secret, 'utf-8'), message, sha256).hexdigest()
        xauth = self.key + ":" + digest

        headers = {
            'X-Time': str(xtime),
            'X-Nonce': xnonce,
            'X-Auth': xauth,
            'Content-Type': 'application/json',
            'X-Organization-Id': self.organisation_id,
            'X-Request-Id': str(uuid.uuid4())
        }

        s = requests.Session()
        s.headers = headers

        url = self.host + path
        if query:
            url += '?' + query

        if self.verbose:
            print(method, url)

        if body:
            response = s.request(method, url, data=body_json)
        else:
            response = s.request(method, url)

        if response.status_code == 200:
            return response.json()
        elif response.content:
            raise Exception(str(response.status_code) + ": " + response.reason + ": " + str(response.content))
        else:
            raise Exception(str(response.status_code) + ": " + response.reason)

    def get_epoch_ms_from_now(self):
        now = datetime.now()
        now_ec_since_epoch = mktime(now.timetuple()) + now.microsecond / 1000000.0
        return int(now_ec_since_epoch * 1000)

    def algo_settings_from_response(self, algorithm, algo_response):
        algo_setting = None
        for item in algo_response['miningAlgorithms']:
            if item['algorithm'] == algorithm:
                algo_setting = item

        if algo_setting is None:
            raise Exception('Settings for algorithm not found in algo_response parameter')

        return algo_setting

    def get_accounts(self):
        return self.request('GET', '/main/api/v2/accounting/accounts2/', '', None)

    def get_accounts_for_currency(self, currency):
        return self.request('GET', '/main/api/v2/accounting/account2/' + currency, '', None)

    def get_withdrawal_addresses(self, currency, size, page):

        params = "currency={}&size={}&page={}".format(currency, size, page)

        return self.request('GET', '/main/api/v2/accounting/withdrawalAddresses/', params, None)

    def get_withdrawal_types(self):
        return self.request('GET', '/main/api/v2/accounting/withdrawalAddresses/types/', '', None)

    def withdraw_request(self, address_id, amount, currency):
        withdraw_data = {
            "withdrawalAddressId": address_id,
            "amount": amount,
            "currency": currency
        }
        return self.request('POST', '/main/api/v2/accounting/withdrawal/', '', withdraw_data)

    def get_my_active_orders(self, algorithm, market, limit):

        ts = self.get_epoch_ms_from_now()
        params = "algorithm={}&market={}&ts={}&limit={}&op=LT".format(algorithm, market, ts, limit)

        return self.request('GET', '/main/api/v2/hashpower/myOrders', params, None)

    def create_pool(self, name, algorithm, pool_host, pool_port, username, password):
        pool_data = {
            "name": name,
            "algorithm": algorithm,
            "stratumHostname": pool_host,
            "stratumPort": pool_port,
            "username": username,
            "password": password
        }
        return self.request('POST', '/main/api/v2/pool/', '', pool_data)

    def delete_pool(self, pool_id):
        return self.request('DELETE', '/main/api/v2/pool/' + pool_id, '', None)

    def get_my_pools(self, page, size):
        return self.request('GET', '/main/api/v2/pools/', '', None)

    def get_hashpower_orderbook(self, algorithm):
        return self.request('GET', '/main/api/v2/hashpower/orderBook/', 'algorithm=' + algorithm, None )
    
    def create_hashpower_order(self, market, type, algorithm, price, limit, amount, pool_id, algo_response):

        algo_setting = self.algo_settings_from_response(algorithm, algo_response)

        order_data = {
            "market": market,
            "algorithm": algorithm,
            "amount": amount,
            "price": price,
            "limit": limit,
            "poolId": pool_id,
            "type": type,
            "marketFactor": algo_setting['marketFactor'],
            "displayMarketFactor": algo_setting['displayMarketFactor']
        }
        return self.request('POST', '/main/api/v2/hashpower/order/', '', order_data)

    def cancel_hashpower_order(self, order_id):
        return self.request('DELETE', '/main/api/v2/hashpower/order/' + order_id, '', None)

    def refill_hashpower_order(self, order_id, amount):
        refill_data = {
            "amount": amount
        }
        return self.request('POST', '/main/api/v2/hashpower/order/' + order_id + '/refill/', '', refill_data)

    def set_price_hashpower_order(self, order_id, price, algorithm, algo_response):

        algo_setting = self.algo_settings_from_response(algorithm, algo_response)

        price_data = {
            "price": price,
            "marketFactor": algo_setting['marketFactor'],
            "displayMarketFactor": algo_setting['displayMarketFactor']
        }
        return self.request('POST', '/main/api/v2/hashpower/order/' + order_id + '/updatePriceAndLimit/', '',
                            price_data)

    def set_limit_hashpower_order(self, order_id, limit, algorithm, algo_response):
        algo_setting = self.algo_settings_from_response(algorithm, algo_response)
        limit_data = {
            "limit": limit,
            "marketFactor": algo_setting['marketFactor'],
            "displayMarketFactor": algo_setting['displayMarketFactor']
        }
        return self.request('POST', '/main/api/v2/hashpower/order/' + order_id + '/updatePriceAndLimit/', '',
                            limit_data)

    def set_price_and_limit_hashpower_order(self, order_id, price, limit, algorithm, algo_response):
        algo_setting = self.algo_settings_from_response(algorithm, algo_response)

        price_data = {
            "price": price,
            "limit": limit,
            "marketFactor": algo_setting['marketFactor'],
            "displayMarketFactor": algo_setting['displayMarketFactor']
        }
        return self.request('POST', '/main/api/v2/hashpower/order/' + order_id + '/updatePriceAndLimit/', '',
                            price_data)

    def get_my_exchange_orders(self, market):
        return self.request('GET', '/exchange/api/v2/myOrders', 'market=' + market, None)

    def get_my_exchange_trades(self, market):
        return self.request('GET','/exchange/api/v2/myTrades', 'market=' + market, None)

    def create_exchange_limit_order(self, market, side, quantity, price):
        query = "market={}&side={}&type=limit&quantity={}&price={}".format(market, side, quantity, price)
        return self.request('POST', '/exchange/api/v2/order', query, None)

    def create_exchange_buy_market_order(self, market, quantity):
        query = "market={}&side=buy&type=market&secQuantity={}".format(market, quantity)
        return self.request('POST', '/exchange/api/v2/order', query, None)

    def create_exchange_sell_market_order(self, market, quantity):
        query = "market={}&side=sell&type=market&quantity={}".format(market, quantity)
        return self.request('POST', '/exchange/api/v2/order', query, None)

    def cancel_exchange_order(self, market, order_id):
        query = "market={}&orderId={}".format(market, order_id)
        return self.request('DELETE', '/exchange/api/v2/order', query, None)

    def set_rig_status(self, rig_id, status):
        status_change={"rigId":rig_id, "action":status}
        return self.request('POST', '/main/api/v2/mining/rigs/status2', '', status_change)

    def get_rig_status(self, rig_id):
        return self.request('GET', '/main/api/v2/mining/rigs2', '', None)



@click.command()
@click.option("--debug-level", "-d", default="INFO",
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        case_sensitive=False,
    ), help='Set the debug level for the standard output.')
@click.option('--log-file', '-l', help="File to store all debug messages.")
@click.option('--price-limit', '-p', default=6, help="Price limit of electricity before stopping rig from mining.")
@click.option('--api-key', '-k', help='Your NiceHash API key.')
@click.option('--api-secret', '-s', help='You NiceHash API secret. Preferebly use a configuration file for this option.')
@click.option('--organization-id', '-o', help='Your NiceHash organization ID.')
@click.option('--rig-id', '-i', help='Your NiceHash Righ ID.')
#@click.option("--dummy","-n" is_flag=True, help="Don't do anything, just show what would be done.") # Don't forget to add dummy to parameters of main function
@click_config_file.configuration_option()
def __main__(debug_level, log_file, price_limit, api_key, api_secret, organization_id, rig_id):
    object = mining_control(debug_level, log_file, price_limit, api_key, api_secret, organization_id, rig_id)

if __name__ == "__main__":
    __main__()

