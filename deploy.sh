#!/usr/bin/env bash

# 1. Make any changes to the website

# Build new website files
hugo -d docs

# Add files and a commit message
git add .
git commit

# Push to Github and your changes will be deployed.
git push
