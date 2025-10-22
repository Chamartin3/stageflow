#!/usr/bin/env bash
# Test script to verify installation components

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Testing StageFlow Installation Components${NC}"
echo ""

# Test 1: Check if install.sh exists and is executable
echo -n "Test 1: install.sh exists and executable... "
if [ -x "./install.sh" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test 2: Check if uninstall.sh exists and is executable
echo -n "Test 2: uninstall.sh exists and executable... "
if [ -x "./uninstall.sh" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test 3: Check if bin/stageflow exists
echo -n "Test 3: bin/stageflow exists... "
if [ -f "./bin/stageflow" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test 4: Check if stageflow supports completion
echo -n "Test 4: stageflow supports --show-completion... "
if ./bin/stageflow --help | grep -q "show-completion"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test 5: Try generating bash completion
echo -n "Test 5: Can generate bash completion... "
if ./bin/stageflow --show-completion bash > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test 6: Try generating zsh completion
echo -n "Test 6: Can generate zsh completion... "
if ./bin/stageflow --show-completion zsh > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test 7: Try generating fish completion
echo -n "Test 7: Can generate fish completion... "
if ./bin/stageflow --show-completion fish > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test 8: Check install.sh has proper shebang
echo -n "Test 8: install.sh has bash shebang... "
if head -1 install.sh | grep -q "^#!/usr/bin/env bash"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test 9: Check uninstall.sh has proper shebang
echo -n "Test 9: uninstall.sh has bash shebang... "
if head -1 uninstall.sh | grep -q "^#!/usr/bin/env bash"; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

# Test 10: Verify INSTALL.md exists
echo -n "Test 10: INSTALL.md exists... "
if [ -f "./INSTALL.md" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}All installation component tests passed!${NC}"
echo ""
echo "To test the actual installation, run:"
echo -e "  ${BLUE}./install.sh${NC}"
echo ""
echo "To test uninstallation, run:"
echo -e "  ${BLUE}./uninstall.sh${NC}"
