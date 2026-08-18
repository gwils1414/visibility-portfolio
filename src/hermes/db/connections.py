#--Connect to hermes db once here, import function elsewhere--#
import psycopg
import logging
import psycopg

#TODO , turn this into a CLI commands --verbose to display logging if needed
#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
#logging.getLogger("psycopg").setLevel(logging.DEBUG)
from hermes.models.deps import Settings
from hermes.logs.logging_helper import log

logger = logging.getLogger(__name__)


deps = Settings()

@log
def get_write_connection():
    conn = psycopg.connect(deps.DB_URL)
    return conn

@log
def get_read_connection():
    #postgres has no read-only connection mode; use a read-only role if you need that
    conn = psycopg.connect(deps.DB_URL)
    return conn
