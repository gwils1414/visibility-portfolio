FROM python:3.12-slim

RUN useradd --create-home sandbox

RUN mkdir /sandbox && chown sandbox:sandbox /sandbox
RUN mkdir /output && chown sandbox:sandbox /output

WORKDIR /sandbox

RUN pip install pandas numpy plotly jinja2

USER sandbox

CMD ["python", "/sandbox/agent_script.py"]