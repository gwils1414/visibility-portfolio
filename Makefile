#precommit checks
#make ruff, make lint # make format
.PHONY: format lint check run install


test:
    uv run pytest


format:
	uv run ruff format .


lint:
	uv run ruff check .
