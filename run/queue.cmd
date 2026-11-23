@echo off
"C:\Program Files\Git\bin\bash.exe" -lc "cd \"$(cygpath -u '%~dp0..')\" && bash run/queue.sh %1"
