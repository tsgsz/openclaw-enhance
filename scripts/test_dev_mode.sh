#!/bin/bash
set -e

OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

echo "Development Mode Test"
echo "====================="

echo "1. Cleanup..."
python -m openclaw_enhance.cli uninstall --openclaw-home "$OPENCLAW_HOME" 2>/dev/null || true
pass "Cleaned"

echo ""
echo "2. Install dev mode..."
python -m openclaw_enhance.cli install --openclaw-home "$OPENCLAW_HOME" --dev || fail "Install failed"
pass "Installed"

echo ""
echo "3. Verify symlinks..."
MANAGED="$HOME/.openclaw/openclaw-enhance/workspaces"
COUNT=$(find "$MANAGED" -maxdepth 1 -type l 2>/dev/null | wc -l)
[ $COUNT -gt 0 ] || fail "No symlinks"
pass "Found $COUNT symlinks"

echo ""
echo "4. Test change reflection..."
TEST_WS="$MANAGED/oe-searcher"
if [ -L "$TEST_WS" ]; then
    SOURCE=$(readlink "$TEST_WS")
    echo "# TEST" >> "$SOURCE/AGENTS.md"
    grep -q "# TEST" "$TEST_WS/AGENTS.md" || fail "Change not reflected"
    sed -i.bak '/# TEST/d' "$SOURCE/AGENTS.md" && rm -f "$SOURCE/AGENTS.md.bak"
    pass "Changes reflect immediately"
fi

echo ""
echo "5. Uninstall..."
python -m openclaw_enhance.cli uninstall --openclaw-home "$OPENCLAW_HOME" || fail "Uninstall failed"
[ ! -d "$MANAGED" ] || fail "Not cleaned"
pass "Uninstalled cleanly"

echo ""
echo -e "${GREEN}All tests passed!${NC}"
