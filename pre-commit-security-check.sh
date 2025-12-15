#!/bin/bash

# Pre-commit hook to prevent committing sensitive data
# Install: cp pre-commit-security-check.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

echo "🔒 Running security pre-commit checks..."

# Check for .env file being committed
if git diff --cached --name-only | grep -q "^\.env$"; then
    echo "❌ ERROR: Attempting to commit .env file!"
    echo "   .env contains sensitive data and should never be committed."
    echo "   Remove it from staging: git reset HEAD .env"
    exit 1
fi

# Check for potential secrets in staged files
SECRETS_FOUND=0

# Check for potential API keys, tokens, passwords
if git diff --cached | grep -iE "(api[_-]?key|secret[_-]?key|password|token|auth[_-]?token)" | grep -vE "(test|example|dummy|fake)" | grep -q "="; then
    echo "⚠️  WARNING: Possible secrets detected in staged files!"
    echo "   Review the following lines:"
    git diff --cached | grep -iE "(api[_-]?key|secret[_-]?key|password|token|auth[_-]?token)" | grep -vE "(test|example|dummy|fake)" | head -5
    SECRETS_FOUND=1
fi

# Check for hardcoded SECRET_KEY
if git diff --cached | grep -q "SECRET_KEY.*=.*['\"].*['\"]"; then
    if ! git diff --cached | grep "SECRET_KEY" | grep -q "config("; then
        echo "❌ ERROR: Hardcoded SECRET_KEY detected!"
        echo "   SECRET_KEY should be loaded from environment variables."
        echo "   Use: SECRET_KEY = config('SECRET_KEY', default='...')"
        exit 1
    fi
fi

# Check for DEBUG = True in Python files
if git diff --cached | grep -E "^[^#]*DEBUG\s*=\s*True" | grep -q ".py$"; then
    echo "⚠️  WARNING: DEBUG = True found in staged Python files"
    echo "   Make sure this is not in production code!"
fi

# Check for print statements that might log sensitive data
if git diff --cached -- "*.py" | grep -iE "^\+.*print.*\(.*password|^\+.*print.*\(.*secret|^\+.*print.*\(.*token"; then
    echo "⚠️  WARNING: Print statements with potential secrets detected"
    echo "   Remove debug print statements before committing"
    SECRETS_FOUND=1
fi

# Check for database credentials
if git diff --cached | grep -iE "(db_password|database_password|postgres_password)" | grep -vE "(test|example|dummy)"; then
    echo "⚠️  WARNING: Database credentials detected!"
    SECRETS_FOUND=1
fi

# Check for AWS credentials
if git diff --cached | grep -iE "(aws_access_key|aws_secret_key)" | grep -vE "(test|example|dummy)"; then
    echo "⚠️  WARNING: AWS credentials detected!"
    SECRETS_FOUND=1
fi

# Final message
if [ $SECRETS_FOUND -eq 1 ]; then
    echo ""
    echo "🔍 Review the warnings above carefully."
    echo "   If these are false positives, you can proceed."
    echo "   Otherwise, remove sensitive data before committing."
    echo ""
    read -p "Continue with commit? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Commit aborted"
        exit 1
    fi
fi

echo "✅ Security checks passed"
exit 0
