import logging

import pymongo
import redis as redis

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
        client = pymongo.MongoClient(host, port, serverSelectionTimeoutMS=10)
        db = client[database]

        try:
            client.server_info()
        except pymongo.errors.ServerSelectionTimeoutError as e:
            logging.error("Mongo server not found: {}".format(e))
            return False
            # raise ConnectionRefusedError("Mongo server not found: {}".format(e))

        return db

    @staticmethod
    def get_redis(host, port, password=None):
        rd = redis.StrictRedis(host=host, port=port, password=password, db=0, decode_responses=True)
        assert rd
        return rd

    def run_telegram(self, params):
        raise NotImplementedError("Please Implement run_telegram method")

    @staticmethod
    def run_web(params):
        raise NotImplementedError("Please Implement run_web staticmethod")

    @staticmethod
    def check_connection():
        mongo = CommonHandler.get_mongo(DB_SETTINGS['MONGO_HOST'], DB_SETTINGS['MONGO_PORT'], DB_SETTINGS['MONGO_DB_NAME'])
        rd = CommonHandler.get_redis(DB_SETTINGS['REDIS_HOST'], DB_SETTINGS['REDIS_PORT'])
        return True if mongo else False
