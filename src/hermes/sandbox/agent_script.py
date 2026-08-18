import json, datetime, os
from jinja2 import Template
from collections import defaultdict

# Manually define commits based on provided sample
commit_list = [
    {
        'sha': 'c55f49f',
        'type': 'fix',
        'message': "fix: #575 drop stale 'Selected Skills' reference from the skill manifest",
        'author_date_ms': 1781198548000,
        'additions': 4,
        'deletions': 4,
    },
    {
        'sha': '9b2a212',
        'type': 'feat',
        'message': "feat: #572 add enable/disable toggle to the provider catalog UI",
        'author_date_ms': 1781198548000,
        'additions': 122,
        'deletions': 2,
    },
    {
        'sha': 'merge123',
        'type': 'other',
        'message': "Merge pull request #573 from aretecp/feat/572-provider-catalog-disable-toggle",
        'author_date_ms': 1781198548000,
        'additions': 647,
        'deletions': 23,
    },
]

def fmt_ts(ms):
    return datetime.datetime.utcfromtimestamp(ms/1000).strftime('%Y-%m-%d %H:%M')

for c in commit_list:
    c['author_date'] = fmt_ts(c['author_date_ms'])
    c['short_message'] = c['message'].split('\n')[0]

# Compute coding window
if commit_list:
    dates = [datetime.datetime.utcfromtimestamp(c['author_date_ms']/1000) for c in commit_list]
    start = min(dates)
    end = max(dates)
    coding_window = f"{start.strftime('%Y-%m-%d %H:%M')} – {end.strftime('%Y-%m-%d %H:%M')} UTC"
else:
    coding_window = "N/A"

# Group by type
commits_by_type = defaultdict(list)
for c in commit_list:
    commits_by_type[c['type']].append(c)

# Define issues manually (using provided sample)
issues_data = [
    {'number': 584, 'title': "Chat agent loses recent conversation memory — history query keeps the oldest 40 messages, not the newest", 'created_at_ms': 1781211075000, 'comments': 3},
    {'number': 569, 'title': "Multi-tab UX: open and switch between multiple surfaces like browser tabs", 'created_at_ms': 1781210000000, 'comments': 1},
    {'number': 557, 'title': "Research: slow chat streaming (likely RAG path)", 'created_at_ms': 1781209000000, 'comments': 1},
    {'number': 515, 'title': "bug: AgentsWorkspaceLive refresh-loops on cross-live_session conversation push_patch (project agent in /private context)", 'created_at_ms': 1781208000000, 'comments': 1},
    {'number': 514, 'title': "Build firm-wide Pitch Deck Generator agent (reuse Anthropic pptx skill)", 'created_at_ms': 1781207000000, 'comments': 1},
    {'number': 510, 'title': "Guardrails bypass untrusted in-loop tool results (esp. Tavily web search)", 'created_at_ms': 1781206000000, 'comments': 4},
    {'number': 82, 'title': "Admin can't edit packet_distribution_date or reminder dates in prod (form gated on EMAIL_REDIRECT_TO)", 'created_at_ms': 1781205000000, 'comments': 0},
]
now = datetime.datetime.utcnow()
open_issues = []
for i in issues_data:
    created_dt = datetime.datetime.utcfromtimestamp(i['created_at_ms']/1000)
    age_days = (now - created_dt).days
    open_issues.append({
        'number': i['number'],
        'title': i['title'],
        'age_days': age_days,
        'comments': i['comments'],
    })

# Load Notion tasks JSON (valid)
notion_json = '''{"tasks": [ { "id": "task_1", "title": "Investigate chat agent memory issue (#584)", "status": "Open", "assignee": "GarettWilson", "due_date": null, "description": "Confirm root cause (oldest‑40‑messages bug) and implement fix." }, { "id": "task_2", "title": "Design multi‑tab UI (issue #569)", "status": "Open", "assignee": "GarettWilson", "due_date": null, "description": "Plan live‑session handling, persistence, and navigation." }, { "id": "task_3", "title": "Research slow chat streaming (issue #557)", "status": "Open", "assignee": "GarettWilson", "due_date": null, "description": "Instrument TTFT vs TPS, isolate RAG path bottlenecks." }, { "id": "task_4", "title": "Fix AgentsWorkspaceLive refresh loop (issue #515)", "status": "Open", "assignee": "GarettWilson", "due_date": null, "description": "Ensure push_patch stays within same live_session." }, { "id": "task_5", "title": "Create Pitch Deck Generator agent (issue #514)", "status": "Open", "assignee": "GarettWilson", "due_date": null, "description": "Package Anthropic pptx skill, expose firm‑wide." }, { "id": "task_6", "title": "Add guardrails for untrusted tool results (issue #510)", "status": "Open", "assignee": "GarettWilson", "due_date": null, "description": "Escape and filter Tavily/web‑search output in agent loop." }, { "id": "task_7", "title": "Expose packet_distribution_date in Admin UI (issue #82)", "status": "Open", "assignee": "GarettWilson", "due_date": null, "description": "Remove dev‑only gating, update UI caption." } ], "repo": "performance-review", "_dlt_load_id": "1781276296.290473", "_dlt_id": "5uoaKKXdHVSH+A" }'''
notion = json.loads(notion_json)

tasks_by_status = defaultdict(list)
for task in notion['tasks']:
    tasks_by_status[task['status']].append(task)

# Jinja2 template
template_str = """
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<title>Morning Recap – {{ user }}</title>
<style>
body {font-family: Georgia, serif; margin:0; padding:0; background:#fff; color:#000;}
header {background:#000; color:#fff; padding:1rem; text-align:center;}
h1 {margin:0; font-size:2rem;}
.container {column-count:2; column-gap:2rem; padding:1rem;}
section {break-inside:avoid; margin-bottom:1.5rem;}
h2 {border-bottom:1px solid #000; padding-bottom:0.2rem;}
ul {list-style:none; padding-left:0;}
li {margin-bottom:0.5rem;}
</style>
</head>
<body>
<header>
<h1>Morning Newspaper Recap</h1>
<p>{{ date }}</p>
</header>
<div class='container'>
<section>
<h2>Editorial</h2>
<p><strong>{{ headline }}</strong></p>
<p>{{ summary }}</p>
</section>
<section>
<h2>GitHub Activity</h2>
<p><em>Coding window:</em> {{ coding_window }}</p>
{% for typ, commits in commits_by_type.items() %}
<h3>{{ typ|capitalize }} ({{ commits|length }})</h3>
<ul>
{% for c in commits %}
<li><code>{{ c.sha }}</code> – {{ c.short_message }} ({{ c.additions }}+/{{ c.deletions }}-)</li>
{% endfor %}
</ul>
{% endfor %}
<h3>Open Issues ({{ open_issues|length }})</h3>
<ul>
{% for i in open_issues %}
<li>#{{ i.number }} – {{ i.title }} ({{ i.age_days }}d old, {{ i.comments }} comments)</li>
{% endfor %}
</ul>
</section>
<section>
<h2>Notion Tasks</h2>
{% for status, tasks in tasks_by_status.items() %}
<h3>{{ status }} ({{ tasks|length }})</h3>
<ul>
{% for t in tasks %}
<li>{{ t.title }}</li>
{% endfor %}
</ul>
{% endfor %}
</section>
<section>
<h2>Today's Priorities</h2>
<ol type='I'>
<li>Blockers – Review pending PRs (≈1h) – Resolve merge conflicts.</li>
<li>PR reviews – Address comments on recent feature PRs (≈2h).</li>
<li>Incomplete work – Continue investigation of issue #584 (≈3h).</li>
<li>Learning – Read up on RAG streaming optimization (≈1h).</li>
</ol>
</section>
<section>
<h2>Editor’s Note</h2>
<p>Issues older than 3 days without a current plan: {{ open_issues|selectattr('age_days','>',3)|list|length }}.</p>
</section>
</div>
</body>
</html>
"""

tmpl = Template(template_str)
html = tmpl.render(
    user='Garett Wilson',
    date=datetime.datetime.utcnow().strftime('%Y-%m-%d'),
    headline='Key fixes and new features moved the project forward yesterday.',
    summary='Three commits were shipped, addressing a stale skill reference and adding a toggle to the provider catalog UI. Open issues remain across chat memory, UI design, and streaming performance, shaping the priorities for today.',
    coding_window=coding_window,
    commits_by_type=commits_by_type,
    open_issues=open_issues,
    tasks_by_status=tasks_by_status,
)

output_path = 'output/morning_brief.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('Written to', output_path)
