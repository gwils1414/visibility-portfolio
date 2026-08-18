#--Placeholder for storing user feedback to postgres--#
#--this will go into our prefect update instructions loop--#

#takes a similar structure, add a select feedback option (should be optional)
#store feedback to a postgres table
#above is the simple piece
#2. this is part of a prefect job
    #call agent to review the feedback results in the table
    #based on the feedback , make any tweaks to agent instructions to improve.
    #if positive feedback is provided, we want the agent to do more of that.
    #if negative feddback , we want the agent to do less.


#it really should just be this, one function storing structured feedback 
#im not sure how we make this optional in the cli


from hermes.models.deps import Settings
import psycopg
import uuid

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)

deps = Settings()


class Feedback():
    def __init__(self):
        self.conn = psycopg.connect(deps.DB_URL, autocommit=True)

    @log
    def create_feedback_table(self):
        '''
        Create feedback table if doesn't already exist on cli start up

        status:
            - initalize as pending review
            - once it is reviewed by evaluator, switch to reviewed
            - get removed from self improvment loop
        '''
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    session_id uuid,
                    response text,
                    reason text,
                    status text,
                    created_at  TIMESTAMP DEFAULT NOW()
                )
                """
            )
            return "Table created"
        except Exception as e:
            print(f"Failed to create table {e}")


    @log
    def store_feedback(self,
                       session_id: uuid,
                       response: str,
                       reason: str,
                       status: str):
        '''
        Store user feedback

        Do we want this just to be simple like or dislike or do we need an explanation.

        Explanation provides more value , however it make the experience less seemless.
            - just like or dislike, agent has to figure out what was good or what was bad

        Maybe we could create a command the stores explicit feedback to make it less in the way.
        '''

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO feedback (
                    session_id,
                    response,
                    reason,
                    status
                ) VALUES (%s,%s,%s,%s)
                """,
                (session_id,response, reason, status)
            )
        except Exception as e:
            print(f"Failed to create table {e}")

#!!!! For long term memory
#join this table to short term memory table to join in prompt/response for evaluation of feedback.
#self improvement cycle then has everything it needs.
#i am not sure these local models have enough context for this task #RESEARCH. Evaluation model needs to be a frontier model evaling and updating
#import store user
#A minimum feedback threshold before any instruction changes (e.g. 10+ dislikes on the same pattern)
#A human review gate on instruction changes, at least initially
#read and upadate current insructions
#mark feedback as processed once it is used so it isnt reused.

