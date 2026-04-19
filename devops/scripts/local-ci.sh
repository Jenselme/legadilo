#!/usr/bin/env bash

#
# SPDX-FileCopyrightText: 2026 Legadilo contributors
#
# SPDX-License-Identifier: AGPL-3.0-or-later
#

set -e
set -u
set -o pipefail

cd /
git clone /app /ci
cd /ci

env --ignore-environment "PATH=$PATH" just setup-ci

# Define colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================================================${NC}"
echo -e "${GREEN}                          Starting Local CI Process                            ${NC}"
echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}Environment:${NC} Containerized Production-like"
echo -e "${BLUE}Step:       ${NC} Running 'just check'"
echo -e "${BLUE}Timestamp:  ${NC} $(date)"
echo -e "${BLUE}================================================================================${NC}"

env --ignore-environment "PATH=$PATH" just check
# Remove support for sqlite
sed --in-place '/^DATABASE_URL/d' ./devops/envs/local/django
# Run test with PG
env --ignore-environment "PATH=$PATH" "DATABASE_URL=postgres://django:django_passwd@postgres:5432/legadilo" just test-coverage

echo -e "${GREEN} Local CI check passed successfully!${NC}"
