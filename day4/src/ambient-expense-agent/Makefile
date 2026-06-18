# ==============================================================================
#  Expense-Approval Agent — Developer Makefile
# ==============================================================================
#  Targets
#    make install      — install all project dependencies (uv sync)
#    make serve        — run the ambient Pub/Sub service on :8080  ← start here
#    make playground   — launch ADK chat playground at http://localhost:8080
#    make run          — quick single-turn CLI smoke-test
#                        usage: make run PROMPT='{"description":"...",...}'
#    make lint           — check code quality (ruff + codespell)
#    make lint-fix       — auto-fix linting issues
#    make test           — run unit + integration tests
#    make generate-traces — run local eval trace generator (no GCP)
#    make grade          — grade traces with LLM-as-judge metrics
#    make help           — list all targets with descriptions
# ==============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Colour helpers
BOLD  := \033[1m
CYAN  := \033[36m
RESET := \033[0m

.PHONY: help install serve playground run lint lint-fix test generate-traces grade

help: ## Show this help message
	@echo ""
	@echo "$(BOLD)Expense-Approval Agent — available targets$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-15s$(RESET) %s\n", $$1, $$2}'
	@echo ""

install: ## Install all project dependencies via uv sync
	uv sync --all-extras

serve: ## Run the ambient Pub/Sub service on :8080 (POST /pubsub to trigger)
	@echo ""
	@echo "$(BOLD)▶  Starting ambient expense-approval service on http://0.0.0.0:8080$(RESET)"
	@echo "$(BOLD)   POST /pubsub     — send a Pub/Sub push message to start a workflow$(RESET)"
	@echo "$(BOLD)   POST /resume/:id — submit APPROVE/REJECT for a paused HITL session$(RESET)"
	@echo "$(BOLD)   GET  /health     — liveness probe$(RESET)"
	@echo ""
	uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080 --reload

playground: ## Launch ADK chat playground at http://localhost:8080
	@echo ""
	@echo "$(BOLD)▶  Starting ADK playground — open http://localhost:8000 in your browser$(RESET)"
	@echo "$(BOLD)   Submit a JSON expense payload in the chat box to start the workflow.$(RESET)"
	@echo ""
	agents-cli playground

run: ## Single-turn CLI smoke-test  (usage: make run PROMPT='{"description":"..."}')
ifndef PROMPT
	$(error PROMPT is not set. Usage: make run PROMPT='{"description":"IDE License","amount":150.0,"category":"software","submitter":"alice@company.com","date":"2026-06-06"}')
endif
	agents-cli run "$(PROMPT)"

lint: ## Check code quality (ruff + codespell)
	agents-cli lint

lint-fix: ## Auto-fix linting issues
	agents-cli lint --fix

test: ## Run unit and integration tests
	uv run pytest tests/unit tests/integration -v

generate-traces: ## Generate local eval traces — no GCP credentials required
	@echo ""
	@echo "$(BOLD)▶  Generating evaluation traces → artifacts/traces/generated_traces.json$(RESET)"
	@echo "$(BOLD)   Clean-path cases use the real ADK runner; LLM failures fall back$(RESET)"
	@echo "$(BOLD)   to a deterministic oracle so all 5 traces are always produced.$(RESET)"
	@echo ""
	uv run python tests/eval/generate_traces.py

grade: ## Grade traces: LLM-as-judge (needs GEMINI_API_KEY) or local rule-based fallback
	@echo ""
	@echo "$(BOLD)▶  Grading traces with routing_correctness + security_containment$(RESET)"
	@echo ""
	@if agents-cli eval grade \
		--traces artifacts/traces/generated_traces.json \
		--config tests/eval/eval_config.yaml \
		--output artifacts/eval-results/ 2>/dev/null; then \
		echo ""; \
	else \
		echo "$(BOLD)   agents-cli grade requires GEMINI_API_KEY — falling back to local rule-based grader$(RESET)"; \
		echo ""; \
		uv run python tests/eval/grade_traces.py; \
	fi
