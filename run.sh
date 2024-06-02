#!/bin/bash
# git push origin --delete docs  # Delete remote branch
dt=$(date '+%d/%m/%Y %H:%M:%S %Z %z')

echo -e '\n\n***************************************************************************************************'
echo "                               $dt"
echo -e '***************************************************************************************************\n'

echo -e "Checking out and updating docs branch"

# Check if the branch exists remotely
if git show-ref --verify --quiet refs/heads/docs; then
  git checkout docs
else
  git checkout -b docs
fi

git pull origin docs

# Check if virtual environment exists and activate it
if [[ -f "venv/bin/activate" ]]; then
  echo 'Activating virtual env'
  source venv/bin/activate
else
  echo 'Virtual environment not found. Skipping activation.'
fi

# Check if main.py exists and run it
if [[ -f "main.py" ]]; then
  echo -e "Running monitor script"
  python main.py
else
  echo 'Python script main.py not found. Exiting.'
  exit 1
fi

# Check for changes, add, commit, and push
if [[ -n $(git status -s) ]]; then
  echo -e "Adding all changes to stage"
  git add --all

  echo -e "Running git commit"
  git commit -m "Updated as of $dt"

  echo -e "\nPushing changes to origin"
  if git push origin docs; then
    echo -e "Task completed."
  else
    echo -e "Failed to push changes. Please check your git configuration."
  fi
else
  echo -e "No changes detected. Task completed."
fi
