@echo off
echo Starting Meet Conclusion...
cd /d "%~dp0"
uv run python -m meet_conclusion
pause
