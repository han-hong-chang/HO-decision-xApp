# ==================================================================================
#       Copyright (c) 2020 AT&T Intellectual Property.
#       Copyright (c) 2020 HCL Technologies Limited.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#          http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
# ==================================================================================
import time
import pandas as pd
from influxdb import DataFrameClient
from configparser import ConfigParser
from mdclogpy import Logger
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from requests.exceptions import RequestException, ConnectionError
import json
import os
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import InfluxDBClient, Point, WriteOptions

logger = Logger(name=__name__)


class DATABASE(object):

    def __init__(self, dbname='Timeseries', user='root', password='root', host="r4-influxdb.ricplt", port='8086', path='', ssl=False):
        self.data = None
        self.host = "r4-influxdb-influxdb2.ricplt"
        self.port = '80'
        self.user = 'admin'
        self.password = '7jQCNdujbSKju7cL32IzOOwAx7rEjEGJ'
        self.path = path
        self.ssl = ssl
        self.dbname = dbname
        self.client = None
        self.token = 'BmHaJ9tkG7RSDZO2nsTeHyMPNT4MESZD' 
        self.address = 'http://r4-influxdb-influxdb2.ricplt:80'
        self.org = 'my-org'
        self.bucket = 'kpimon'
        self.config()

    def connect(self):
        if self.client is not None:
            self.client.close()

        try:
            self.client = influxdb_client.InfluxDBClient(url=self.address, token=self.token, org=self.org)
            version = self.client.version()
            logger.info("Conected to Influx Database, InfluxDB version : {}".format(version))
            return True

        except (RequestException, InfluxDBClientError, InfluxDBServerError, ConnectionError):
            logger.error("Failed to establish a new connection with InflulxDB, Please check your url/hostname")
            time.sleep(120)

    def read_data(self, meas='ueMeasReport', limit=10000, cellid=False, ueid=False, nbdecision=False):
        query = None
        if cellid:
            meas = 'UeMetrics'
            param = 'Viavi_Cell_id'
            Id = cellid
            query = """from(bucket:"{}") |> range(start: -5s) |> filter(fn: (r) => """.format(self.bucket)
            query += """r._measurement == "UeMetrics" and """
            query += """r.Viavi_Cell_id == "{}") """.format(Id)
            query += """|> limit(n: 1)"""
            query += """|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")"""

        if ueid:
            meas = 'UeMetrics'
            param = 'Viavi_UE_id'
            limit = 1
            Id = ueid
            query = """from(bucket:"{}") |> range(start: -10m) |> filter(fn: (r) => """.format(self.bucket)
            query += """r._measurement == "{}" and """.format(meas)
            query += """r.{} == "{}" ) """.format(param,Id)
            query += """|> group() """
            query += """|> sort(columns: ["_time"], desc: true) |> limit(n: {})""".format(limit)

        if nbdecision:
            meas = 'UeMetrics'
            param = 'Viavi_UE_id'
            limit = 1
            Id = nbdecision
            query = """from(bucket:"{}") |> range(start: -5s) |> filter(fn: (r) => """.format(self.bucket)
            query += """r._measurement == "UeMetrics" and """
            query += """r.Viavi_UE_id == "{}" ) """.format(Id)
            query += """|> filter(fn: (r) => r["_field"] == "Viavi_Nb1_id" or r["_field"] == "Viavi_Nb1_Rsrp" or r["_field"] == "Viavi_Nb2_id" or r["_field"] == "Viavi_Nb2_Rsrp")"""
            query += """|> limit(n: 1) """
            query += """|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")"""
        
        logger.info("Query Command: {}".format(query))
        result = self.query(query)
        return result

    def query(self, query):
        try:
            query_api = self.client.query_api()
            result = query_api.query_data_frame(org=self.org, query=query)
        except (RequestException, InfluxDBClientError, InfluxDBServerError, ConnectionError) as e:
            logger.error('Failed to connect to influxdb: {}'.format(e))
            result = False
        return result

    def cells(self, meas='CellReports', limit=100):
        meas = self.cellmeas
        query = """select * from {}""".format(meas)
        query += " ORDER BY DESC LIMIT {}".format(limit)
        self.query(query, meas)
        if self.data is not None:
            return self.data[self.cid].unique()

    def write_prediction(self, df, meas_name='QP'):
        try:
            self.client.write_points(df, meas_name)
        except (RequestException, InfluxDBClientError, InfluxDBServerError):
            logger.error("Failed to send metrics to influxdb")

    def config(self):
        cfg = ConfigParser()
        cfg.read('src/qp_config.ini')
        for section in cfg.sections():
            if section == 'influxdb':
                self.influxDBAdres = cfg.get(section, "influxDBAdres")
                self.host = cfg.get(section, "host")
                self.port = cfg.get(section, "port")
                self.user = cfg.get(section, "user")
                self.password = cfg.get(section, "password")
                self.path = cfg.get(section, "path")
                self.ssl = cfg.get(section, "ssl")
                self.dbname = cfg.get(section, "database")
                self.meas = cfg.get(section, "measurement")
                self.token = cfg.get(section, "token")
                self.org = cfg.get(section, "org")
                self.bucket = cfg.get(section, "bucket")


class DUMMY(DATABASE):

    def __init__(self):
        super().__init__()
        self.ue_data = pd.DataFrame([[1002, "c2/B13", 8, 69, 65, 113, 0.1, 0.1, "Car-1", -882, -959, pd.to_datetime("2021-05-12T07:43:51.652")]], columns=["du-id", "RF.serving.Id", "prb_usage", "rsrp", "rsrq", "rssinr", "throughput", "targetTput", "ue-id", "x", "y", "measTimeStampRf"])

        self.cell = pd.read_csv('src/cells.csv')

    def read_data(self, meas='ueMeasReport', limit=100000, cellid=False, ueid=False):
        if ueid:
            self.data = self.ue_data.head(limit)
        if cellid:
            self.data = self.cell.head(limit)

    def cells(self):
        return self.cell[self.cid].unique()

    def write_prediction(self, df, meas_name='QP'):
        pass

    def query(self, query=None):
        return {'UEReports': self.ue_data.head(1)}