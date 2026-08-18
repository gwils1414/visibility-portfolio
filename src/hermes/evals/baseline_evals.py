#--The question is on these evals, are we going to measure them in realtime-##
#if this wasnt a CLI you could have an evals dashboard-
#in the case of the CLI, we would almost want them spitting out the basline evals as a progress bar
#out of 100 for lets say 5 eval pillars.
#custom evals could be created but it is tough with a CLI. Makes me want this to be a GUI of some sort.

#Evals in my case would come in handy for workflows , saved prompts or commands. If i call i saved prompt 10 times. I would expect a correct answer 8/10

"""/eval run "summarize_task" --runs 10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run 1/10  ✓  92/100
Run 2/10  ✓  88/100
Run 3/10  ✗  45/100
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pass rate:  8/10 (80%)  ·  Threshold: 80%  ✓"""

#TODO
#for this to work , I would need to be storing and logging sessions in a chat state database for short term memory and evals. I dont have that set up , but i will put that on my todo

import logging
logger = logging.getLogger(__name__)
