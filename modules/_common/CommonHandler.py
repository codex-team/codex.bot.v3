import logging

import redis as redis
from pymongo import MongoClient

from configuration.globalcfg import DB_SETTINGS


class CommonHandler:

    def __init__(self, web_app):
        self.WEB_APP = web_app
        self.module = None
        self.db_settings = DB_SETTINGS

        assert self.WEB_APP
        assert self.db_settings

        logging.debug("Module {} initialized".format(self))

    def set_routes(self):
        raise NotImplementedError("Please Implement set_routes method")

    def register_commands(self, global_commands):
        raise NotImplementedError("Please Implement register_commands method")

    @staticmethod
    def get_mongo(host, port, database):
        client = MongoClient(host, port)
        db = client[database]
        assert db
        return db

    @staticmethod
    def get_redis(host, port):
        rd = redis.StrictRedis(host=host, port=port, db=0, decode_responses=True)
        assert rd
        return rd

    def run_telegram(self, params):
        raise NotImplementedError("Please Implement run_telegram method")

    @staticmethod
    def run_web(params):
        raise NotImplementedError("Please Implement run_web staticmethod")
