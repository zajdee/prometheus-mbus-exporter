#!/usr/bin/env python3

import argparse
import logging
import lxml
import multiprocessing
import os
import subprocess
import time
import untangle
import yaml

from prometheus_client import start_http_server, Counter, Metric, REGISTRY
from prometheus_client.core import CounterMetricFamily

class ExporterProcess(multiprocessing.Process):

    def __init__(self, queue, location=None, port=None, address='::'):
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()
        self.location = location
        self.xml = ''
        self.queue = queue
        self.port = port
        self.address = address
        logging.info('ExporterProcess: init complete')
        return

    def run(self):
        logging.info('ExporterProcess: run')
        start_http_server(port=self.port, addr=self.address)
        REGISTRY.register(self)
        while not self.exit.is_set():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                return

    def shutdown(self):
        logging.info("ExporterProcess: Shutdown initiated")
        self.exit.set()

    def get_xml_for_device(self):
        # always retrieve the latest queue item
        logging.debug('get_xml_for_device called')
        while not self.queue.empty():
            self.xml = self.queue.get()
            logging.debug('Popped queue item: "%s"', self.xml)
        return self.xml

    def parseMeterDataRecord(self, r):
        """
        <DataRecord id="8">
            <Function>Minimum value</Function>
            <StorageNumber>0</StorageNumber>
            <Tariff>2</Tariff> -- not always present
            <Device>0</Device>
            <Unit>Energy (10 Wh)</Unit>
            <Value>0</Value>
            <Timestamp>2019-10-18T13:32:54Z</Timestamp>
        </DataRecord>
        """
        return {
            'Function': r.Function.cdata,
            'StorageNumber': r.StorageNumber.cdata,
            'Tariff': r.Tariff.cdata if hasattr(r, 'Tariff') else None,
            'Device': r.Device.cdata if hasattr(r, 'Device') else None,
            'Unit': r.Unit.cdata,
            'Value': r.Value.cdata,
        }


    def collect(self):
        c = CounterMetricFamily('power_consumption', 'Power consumption', labels=['tariff', 'location'])
        xml = self.get_xml_for_device()
        try:
            obj = untangle.parse(xml.decode('utf-8'))
        except:
            yield c
            return
        meterdata = []

        for data in obj.MBusData.DataRecord:
            meterdata.append(self.parseMeterDataRecord(data))

        for data in meterdata:
            if data['Function'] != 'Instantaneous value':
                continue
            if not data['Tariff']:
                continue
            if not data['Unit'] == 'Energy (10 Wh)':
                continue
            value = int(data['Value']) * 10
            tariff = str(data['Tariff'])
            c.add_metric([tariff, self.location], value)
        yield c


class CollectorProcess(multiprocessing.Process):

    def __init__(self, queue, device=None, meter_id=None, baud_rate=None):
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()
        self.baud_rate = baud_rate
        self.device = device
        self.meter_id = meter_id
        self.xml = ''
        self.queue = queue
        logging.info('CollectorProcess: init complete')

    def run(self):
        logging.info('CollectorProcess: run')
        while not self.exit.is_set():
            self.retrieve_xml_for_device()
            try:
                time.sleep(15)
            except KeyboardInterrupt:
                return

    def shutdown(self):
        logging.info("CollectorProcess: Shutdown initiated")
        self.exit.set()

    def retrieve_xml_for_device(self):
        try:
            self.xml = subprocess.Popen('mbus-serial-request-data -b {:d} {:s} {:d}'.
                format(self.baud_rate, self.device, self.meter_id),
                shell=True,
                stdout=subprocess.PIPE).stdout.read()
            logging.debug(self.xml)
            self.queue.put(self.xml)
        except Exception:
            pass

def read_yaml(config_file):
    config_name = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        config_file)
    if not os.path.isfile(config_name):
        logging.error('Config file %s not found.', config_name)
        return None
    with open(config_name, "r") as yaml_file:
        cfg = yaml.load(yaml_file, Loader=yaml.FullLoader)
    logging.debug('Read config file: %s', cfg)
    return cfg

def main():
    parser = argparse.ArgumentParser(
        description='M-Bus power meter Prometheus exporter.')

    parser.add_argument('-c', '--config', default='prometheus-mbus-exporter.yml', help='Exporter config file')
    parser.add_argument('-v', '--verbose',
                        dest='verbose', action='store_true', default=False,
                        help='Increase logging verbosity.')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.info('Starting up...')
    config = read_yaml(args.config)
    if not config:
        logging.error('Unable to load configuration, exitting.')
        return

    queue = multiprocessing.Queue()
    collector_process = CollectorProcess(
        queue,
        device=config['mbus']['device'],
        meter_id=config['mbus']['meter_id'],
        baud_rate=config['mbus']['baud_rate'])
    exporter_process = ExporterProcess(
        queue,
        location=config['exporter']['location'],
        port=config['exporter']['port'],
        address=config['exporter']['address'])
    collector_process.start()
    exporter_process.start()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            collector_process.shutdown()
            exporter_process.shutdown()
            return

if __name__ == "__main__":
    main()
