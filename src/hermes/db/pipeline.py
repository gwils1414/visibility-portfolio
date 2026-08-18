#placeholder dlt pipeline
#orchestrated by prefect
#with infisical: infisical run -- uv run src/hermes/db/pipeline.py

import dlt
from dlt.destinations import postgres
from hermes.db.github_stats import GithubStatistics
from hermes.db.notion_stats import NotionApiCalls
from prefect import flow, task, get_run_logger
from hermes.db.obsidian_embeddings import ObsidianEmbeddings
from hermes.models.deps import Settings

import logging
logger = logging.getLogger(__name__)


deps = Settings()

gh_stats = GithubStatistics()
obsidian = ObsidianEmbeddings()

@dlt.source()
def github_source():

    @dlt.resource(write_disposition='replace',name = 'repos')
    def repo_names():
        data = gh_stats.get_repo_names()
        yield data

    @dlt.resource(write_disposition='replace',name = 'commits',primary_key = 'sha')
    def commits():
        data = gh_stats.get_commits_bulk()
        yield data.to_dict(orient="records")

    @dlt.resource(write_disposition='replace',name = 'commit_details',primary_key = 'sha')
    def commit_details():
        data = gh_stats.get_commits_details_bulk()
        yield data.to_dict(orient="records")


    @dlt.resource(write_disposition='replace',
                name = 'issues',
                columns = {"closed_at": {"data_type":"timestamp"}})
    def issues():
        data = gh_stats.get_issues_bulk()
        yield data.to_dict(orient="records")

    return repo_names, commits, commit_details, issues


github_pipeline = dlt.pipeline(
    pipeline_name = "github_stats",
    destination = postgres(deps.DB_URL),
    dataset_name= 'github'
)

#--Tasks--#
@task(retries=3, retry_delay_seconds=60)
def load_repos():
    logger = get_run_logger()
    logger.info("Loading repos..")
    github_pipeline.run(github_source().repo_names)
    logger.info("Repos loaded...")


@task(retries=3, retry_delay_seconds=60)
def load_commits():
    logger = get_run_logger()
    logger.info("Loading commits...")
    github_pipeline.run(github_source().commits)
    logger.info("Commits loaded...")


@task(retries=3, retry_delay_seconds=60)
def load_commit_details():
    logger = get_run_logger()
    logger.info("Loading commit details..")
    github_pipeline.run(github_source().commit_details)
    logger.info("Commit details loaded...")


@task(retries=3, retry_delay_seconds=60)
def load_issues():
    logger = get_run_logger()
    logger.info("Loading issues..")
    github_pipeline.run(github_source().issues)
    logger.info("Issues loaded...")


@flow(name="github-daily-pipeline")
def run_pipeline():
    load_repos()
    load_commits()
    load_commit_details()
    load_issues()


#--Notion Pipeline Start--#
notion = NotionApiCalls()

#TODO , integrate notion data into dlt run
@dlt.source()
def notion_source():

    @dlt.resource(name = "Get Tasks", table_name = 'notion_tasks', write_disposition='replace')
    def get_tasks():
        '''
        Pulls tasks from private tasks tracker
        '''
        data = notion.get_database_tasks()
        yield data.to_dict(orient='records')

    return get_tasks

notion_pipeline = dlt.pipeline(
    pipeline_name = "notion_tasks",
    destination = postgres(deps.DB_URL),
    dataset_name= 'notion'
)

@task(retries=3, retry_delay_seconds=60)
def get_notion_tasks():
    '''
    Add get notion tasks as a task in the pipeline for logging.
    '''
    logger = get_run_logger()
    logger.info("Loading notion tasks..")
    notion_pipeline.run(notion_source.get_tasks)
    logger.info("Notion tasks loaded..")


@flow(name='notion-daily-pipeline')
def run_notion_pipeline():
    get_notion_tasks()



#--Obsidian Embedding--#
#TODO , migrate `embedding` column from json to pgvector once postgres has the `vector` extension enabled.
#       requires: CREATE EXTENSION vector; in the hermes db, and switching the column hint to a vector(<dim>) type
#       so semantic search can use the `<=>` operator instead of loading every row + sklearn cosine_similarity.
@dlt.resource(
        name='obsidian_embeddings',
            write_disposition='replace',
            columns={
    "embedding": {"data_type": "json"},
})
def load_embeddings():
    data = obsidian.embed_descriptions()
    #yield records (not the DataFrame) so dlt uses JSONL, not Arrow→CSV.
    #the embedding column is list<float>, which can't be written to CSV but is fine in JSON.
    yield data.to_dict(orient="records")

obsidian_pipeline = dlt.pipeline(
    pipeline_name='obsidian',
    destination = postgres(deps.DB_URL),
    dataset_name= 'obsidian_embeddings'
)

@task(retries=3, retry_delay_seconds=60)
def load_embeddings_task():
    '''
    Add get notion tasks as a task in the pipeline for logging.
    '''
    logger = get_run_logger()
    logger.info("Loading embeddings..")
    obsidian_pipeline.run(load_embeddings)
    logger.info("Descriptions embedded..")

@flow(name='obsidian-daily-pipeline')
def run_obsidian_pipeline():
    load_embeddings_task()



if __name__ == "__main__":
    #implement this prefect run whenever we can spin it up in a docker container
    '''run_pipeline.serve(
        name="github-daily",
        cron = "0 7 * * 1-5" #7am mon-friday
    )'''
    #run without using prefect
    github_pipeline.run(github_source)
    #TODO , for some reason this pipeline is creating 4 tables. Should just be one
    notion_pipeline.run(notion_source)
    obsidian_pipeline.run(load_embeddings)








