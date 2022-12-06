dt=$(date '+%d/%m/%Y %H:%M:%S %Z %z');
source venv/bin/activate && python main.py
git add "docs/index.html"
git commit -m "Updated as of $dt"
git push -f origin main
