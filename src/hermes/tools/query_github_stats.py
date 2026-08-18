from hermes.db.connections import get_read_connection
import pandas as pd
import json
from datetime import datetime, timezone

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)


#TODO build out query for needed data
@log
def query_commit_details()-> json:
    '''
    This function is here to pull commit details

    Currently set up to pull only those created in the last week
    '''
    conn = get_read_connection()
    today = (datetime.now(timezone.utc)).date() #we want todays date to filter for just yesterdays commits if any

    try:
        data = pd.read_sql(
            sql = """
            select * from github.commit_details cd
            where cd.commit_committer_date > CURRENT_DATE - 7""",
            con = conn
        )
    except Exception as e:
        print(f"Failed to query github stats. {e}")

    #pass json
    data = data.to_json()
    return data

@log
def query_issues()-> json:
    '''
    This function is here to pull github issues

    Currently set up to pull only those created in the last week
    '''
    conn = get_read_connection()
    today = (datetime.now(timezone.utc)).date() #we want todays date to filter for just yesterdays commits if any

    try:
        data = pd.read_sql(
            sql = """
            select * from github.issues
            where created_at > CURRENT_DATE - 7""",
            con = conn
        )
    except Exception as e:
        print(f"Failed to query github stats. {e}")

    #pass json
    data = data.to_json()
    return data
