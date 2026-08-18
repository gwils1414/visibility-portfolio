#--create workflows table
#update workflows table
#pull from workflows table




#create table/schema

import logging
logger = logging.getLogger(__name__)
from hermes.models.deps import Settings
import psycopg
from config.paths import 


deps = Settings()
DB_URL = deps.DB_URL


def create_workflows_schema():
    '''
    Store .py file paths for workflow steps

    Dagster will pick these up
    '''
    conn = psycopg.connect(conninfo=DB_URL, autocommit=True)
    cursor = conn.cursor()

    cursor.executemany(
        query= """
        CREATE TABLE IF NOT EXISTS workflows (
        id UUID PRIMARY_KEY,
        workflow_name TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        last_updated TIMESTAMP);

        CREATE TABLE IF NOT EXISTS workflow_steps (
        id FORIEGN KEY,
        step_ids,
        steps TEXT,
        status TEXT DEFAULT 'pending'
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP,
        last_ran TIMESTAMP);
        """,
    )
    pass

#in the debate of how this make sense to do safely, the agent could write the code
#to the db and write it to a file and point from one to the other.
#or we can use DAG/AIRFLOW, which seems a bit more complext