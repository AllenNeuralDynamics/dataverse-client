lint:
	uvx ruff check

lint-fix:
	uvx ruff check --fix

test:
	uv run pytest
	