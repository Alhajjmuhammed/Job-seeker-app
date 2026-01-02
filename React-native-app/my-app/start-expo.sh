#!/bin/bash
# Auto-start Expo without login prompts

cd /home/easyfix/Documents/JobSeeker/Job-seeker-app/React-native-app/my-app

# Set environment variables to disable all prompts
export EXPO_NO_TELEMETRY=1
export EXPO_NO_DOCTOR=1
export CI=0

# Start Expo and auto-answer login prompt
echo "" | npx expo start --clear 2>&1 | while IFS= read -r line; do
    echo "$line"
    # If we see the login prompt, just continue without login
    if [[ "$line" == *"Log in"* ]]; then
        echo "Skipping login prompt..."
        sleep 1
    fi
done
