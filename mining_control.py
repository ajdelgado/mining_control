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

class mining_control:

    def __init__(self, debug_level, log_file):
        ''' Initial function called when object is created '''
        self.config = dict()
        self.config['debug_level'] = debug_level
        if log_file is None:
            log_file = os.path.join(os.environ.get('HOME', os.environ.get('USERPROFILE', os.getcwd())), 'log', 'mining_control.log')
        self.config['log_file'] = log_file
        self._init_log()

        self.get_energy_prices()

    def _init_log(self):
        ''' Initialize log object '''
        self._log = logging.getLogger("mining_control")
        self._log.setLevel(logging.DEBUG)

        sysloghandler = SysLogHandler()
        sysloghandler.setLevel(logging.DEBUG)
        self._log.addHandler(sysloghandler)

        streamhandler = logging.StreamHandler(sys.stdout)
        streamhandler.setLevel(logging.getLevelName(self.config.get("debug_level", 'INFO')))
        self._log.addHandler(streamhandler)

        if 'log_file' in self.config:
            log_file = self.config['log_file']
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


@click.command()
@click.option("--debug-level", "-d", default="INFO",
    type=click.Choice(
        ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        case_sensitive=False,
    ), help='Set the debug level for the standard output.')
@click.option('--log-file', '-l', help="File to store all debug messages.")
#@click.option("--dummy","-n" is_flag=True, help="Don't do anything, just show what would be done.") # Don't forget to add dummy to parameters of main function
@click_config_file.configuration_option()
def __main__(debug_level, log_file):
    object = mining_control(debug_level, log_file)
    object._log.info('Initialized mining_control')

if __name__ == "__main__":
    __main__()

