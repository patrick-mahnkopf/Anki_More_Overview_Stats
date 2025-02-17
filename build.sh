#!/bin/bash

temp_dir=$(mktemp -d)
cp *.py config.json LICENSE "$temp_dir"
(cd "$temp_dir" && zip -r "$OLDPWD/MoreOverviewStats.ankiaddon" .)
rm -rf "$temp_dir"
