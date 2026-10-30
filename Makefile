#precommit checks
#make ruff, make lint # make format
.PHONY: test format lint


test:
	uv run pytest


format:
	uv run ruff format .


lint:
	uv run ruff check .
