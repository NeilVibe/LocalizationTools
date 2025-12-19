#!/bin/bash
# Poll for CDP and run tests when ready

echo "Polling for CDP on port 9222..."
echo "Launch LocaNext.exe --remote-debugging-port=9222 from Windows"
echo ""

for i in {1..60}; do
  result=$(curl -s http://127.0.0.1:9222/json 2>/dev/null)
  if [ -n "$result" ]; then
    echo ""
    echo "=========================================="
    echo "CDP READY! App is running."
    echo "=========================================="
    echo ""
    echo "Page info:"
    echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'URL: {d[0].get(\"url\",\"?\")}'); print(f'Title: {d[0].get(\"title\",\"?\")}')" 2>/dev/null
    echo ""
    echo "Running Node.js tests..."
    echo ""

    cd /home/neil1988/LocalizationTools/testing_toolkit/cdp

    echo "=== quick_check.js ==="
    node quick_check.js
    echo ""

    echo "=== test_server_status.js ==="
    node test_server_status.js
    echo ""

    echo "Tests complete!"
    exit 0
  fi
  echo -n "."
  sleep 5
done

echo ""
echo "Timeout after 5 minutes - app not launched"
exit 1
