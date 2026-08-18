# visibility
This project is a placeholder for visibility into the ARI teams daily / weekly monthly contributions.

The goal is to scrape data from various places such as bd pulse activity , github commmits, PRs, lines changed, , issues closed, repos created and so on.

The final deliverable will be a operating dlt/dbt pipeline , normalizing the activity and presenting is as an executive level dashboard to track work.

Motivation:
	- The motivation for this is not to build in the dark, and advice from 'the lean startup' to make sure in the early stages all of the contributions you are making are visible and transparent to those funding/ supporiting you

 
--Edit

This may build into something else while keep the same original goal.

The stack:
	- pydantic ai agent and typing
	- bash tool
	- resend tool
	- python code execution in sandbox with docker for html generation
	- notion mcp
	- github statistics tool
	- scheduling any deployment ?
		- cron / side car / prefect
	- can deploy to spare laptop
	-duckdb for persistent storage
	- *slack* for messaging
	- *MODEL*:
		- Options:
			- personal gpt token without sharing data (mini models)
			- may try a local model through ollama cloud such as openai-120b. 
				- already have api keys for both of these

The idea is:
	- pull github statistics from each of our repos every morning from the previous day
		- issues @me / file changes / lines of code / PRs assigned to me
	- pull tasks from notion via mcp / anything assigned to me
		- ari tasks / personal tasks / AI ideas

Once the agent has the information build a '5 am newspaper in the driveway' as an HTML.
	- For this i envision it laid out exxactly as the front page of a newspaper.

1. what happened yesterday
2. what is outstanding 
3. where to start today based on priority.
4. it should pull ari tasks



Will probably end up loading Notion and Github into sqlite daily , purging records once a month maybe.
This could run into a dlt/dbt workflow

Meaning this will move from an agent tool to a cron job to load.
Same for notion API.
Agent will just do querying / summarizing and generating HTML

### Leaning toward prefect for scheduling.


NExt steps:
- start with github api pulls -> dlt. Get that all working
- move to notion
- Could end up just putting all the tools here into an mcp , and connecting via claude desktop.
- Add slack or resend notifications for pipeline observability
- deploy via docker locally. Everything will go into the container.


Wants:
2. Workflow building
	- morning brief will just become a workflow (made this a saved prompt/command)
	- finance workflows: 13 week cash flow
	- stock analysis pulling from APIs (vantage and so on)
		- dbt pipeline ?
	- PE research pipeline (market industry research , where companies are failing)
		- specifially restructuring
4. Local model github triage bot (replace current claude set up)
	- !! see src/hermes/docs/active/claude_traige_bot.md
5. Long Term Memory
	- short term memory is there
	- long term memory updates are there to be updated with /memory
	- i think there is another level to this
		- Long term memory is self updating
		- prefect job for instruction updates
6. Feedback Loop
	- feedback is there and stored
	- no current method set up for self improvement
	- add pipeline for this
7. How to incorporate network graphs
	- agent can create / add nodes edges to a graph
	- probably can just create a neo4j db and link the mcp
10. Schedule workflows from the cli.(brainstorm this)
	- /schedule-workflows
	-cron jobs
11. **Build Phx-Live View UI**
	- launch with hermes -ui or dashboard
	- view agents / workflows / analytics / audit trails
	- how would the two link ?
		- FastAPI into hermes
		- Most everything else will be CRUD from postgres
		- workflows will be realtime
	- store them as seperate Repos ? or build phx liveview out in the UI folder here ?
	- It is not as easy as just setting up a react front ned
12. Set up full logging UI with logging.info to file / postgres
	- use that datatable to show a logging UI
	- logging file is set up , need to push to postgres
14. Fine tune my own guardrail models on asus
	- host on thinkcentre or locally.
	- Practice hosting on AWS
15. When we embed the skill descriptions , should also store name from the front matter. If not included in front matter it should be added for best practice.
16. Create agents on demand from the cli
	- could be via bash / filesystem to build it internally
	- or we can move to a system where agent attributes are stored in postgres and we built them dynamically.
17. Eventually fully move off of pydantic
	- build from scratch
	- API calls / Tool calls / returned results
	- This is a lot of work
		- we just want to remove dependencies





#How can we avoid:
High barrier to entry for non-technical users
Discovery is poor — you have to know what commands exist
Error messages can be cryptic
No visual feedback for complex state


#full TUI:
Terminal User Interface (TUI) that lives in your shell — it's not just a chat window bolted onto your editor


goal of this is to do everything from the terminal , I dont want to switch between 200 apps a day.