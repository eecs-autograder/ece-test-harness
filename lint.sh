#!/usr/bin/env bash
set -xeuo pipefail

ruff check .
ruff format --check .
pyright src/ tests/
