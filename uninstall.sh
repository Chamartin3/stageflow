#!/usr/bin/env bash
# StageFlow Uninstallation Script
# Removes bin/ from PATH and uninstalls shell completions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get project root directory
SCRIPT_DIR="$(builtin cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$SCRIPT_DIR/bin"

# Detect current shell
detect_shell() {
    if [ -n "$BASH_VERSION" ]; then
        echo "bash"
    elif [ -n "$ZSH_VERSION" ]; then
        echo "zsh"
    elif [ -n "$FISH_VERSION" ]; then
        echo "fish"
    else
        ps -p $$ -o comm= | sed 's/-//'
    fi
}

CURRENT_SHELL=$(detect_shell)

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       StageFlow Uninstallation Script                   ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Detected shell:${NC} $CURRENT_SHELL"
echo ""

# Function to remove PATH from shell config
remove_from_path() {
    local shell_config=$1

    if [ ! -f "$shell_config" ]; then
        echo -e "${YELLOW}⚠${NC} Config file not found: $shell_config"
        return 0
    fi

    # Create backup
    cp "$shell_config" "${shell_config}.backup-$(date +%Y%m%d-%H%M%S)"

    # Remove StageFlow PATH entries
    sed -i.tmp '/# StageFlow - Added by install.sh/d' "$shell_config"
    sed -i.tmp "\|$BIN_DIR|d" "$shell_config"
    rm -f "${shell_config}.tmp"

    echo -e "${GREEN}✓${NC} Removed PATH configuration from $shell_config"
    return 0
}

# Function to remove completions
remove_completions() {
    local shell=$1

    echo ""
    echo -e "${BLUE}Removing shell completions for $shell...${NC}"

    case $shell in
        bash)
            local completion_file="$HOME/.bash_completion.d/stageflow.bash"
            local bashrc="$HOME/.bashrc"

            # Remove completion file
            if [ -f "$completion_file" ]; then
                rm -f "$completion_file"
                echo -e "${GREEN}✓${NC} Removed bash completion file"
            fi

            # Remove sourcing from .bashrc
            if [ -f "$bashrc" ]; then
                sed -i.tmp '/# StageFlow completion - Added by install.sh/d' "$bashrc"
                sed -i.tmp '\|bash_completion.d/stageflow.bash|d' "$bashrc"
                rm -f "${bashrc}.tmp"
            fi
            ;;

        zsh)
            local completion_file="$HOME/.zsh/completions/_stageflow"
            local zshrc="$HOME/.zshrc"

            # Remove completion file
            if [ -f "$completion_file" ]; then
                rm -f "$completion_file"
                echo -e "${GREEN}✓${NC} Removed zsh completion file"
            fi

            # Remove from .zshrc (be careful not to break other completions)
            if [ -f "$zshrc" ]; then
                sed -i.tmp '/# StageFlow completion - Added by install.sh/d' "$zshrc"
                # Only remove StageFlow-specific fpath/compinit lines
                sed -i.tmp '\|.zsh/completions|d' "$zshrc"
                rm -f "${zshrc}.tmp"
            fi
            ;;

        fish)
            local completion_file="$HOME/.config/fish/completions/stageflow.fish"

            if [ -f "$completion_file" ]; then
                rm -f "$completion_file"
                echo -e "${GREEN}✓${NC} Removed fish completion file"
            fi
            ;;

        *)
            echo -e "${YELLOW}⚠${NC} Shell '$shell' - no completions to remove"
            ;;
    esac

    return 0
}

# Confirmation prompt
echo -e "${RED}This will remove:${NC}"
echo -e "  • StageFlow from your PATH"
echo -e "  • Shell completion files"
echo -e "  • Configuration entries in shell config files"
echo ""
read -p "$(echo -e ${YELLOW}Continue with uninstallation? [y/N]:${NC} )" -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Uninstallation cancelled.${NC}"
    exit 0
fi

# Main uninstallation process
echo ""
echo -e "${BLUE}[1/2] Removing StageFlow from PATH...${NC}"

case $CURRENT_SHELL in
    bash)
        remove_from_path "$HOME/.bashrc"
        ;;
    zsh)
        remove_from_path "$HOME/.zshrc"
        ;;
    fish)
        local fish_config="$HOME/.config/fish/config.fish"
        if [ -f "$fish_config" ]; then
            cp "$fish_config" "${fish_config}.backup-$(date +%Y%m%d-%H%M%S)"
            sed -i.tmp '/# StageFlow - Added by install.sh/d' "$fish_config"
            sed -i.tmp "\|$BIN_DIR|d" "$fish_config"
            rm -f "${fish_config}.tmp"
            echo -e "${GREEN}✓${NC} Removed PATH configuration from $fish_config"
        fi
        ;;
    *)
        echo -e "${YELLOW}⚠${NC} Could not automatically remove from PATH"
        echo -e "   Please manually remove ${BLUE}$BIN_DIR${NC} from your PATH"
        ;;
esac

echo ""
echo -e "${BLUE}[2/2] Removing shell completions...${NC}"
remove_completions "$CURRENT_SHELL"

# Summary
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║             Uninstallation Complete!                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓${NC} StageFlow has been removed from your system"
echo ""
echo -e "${YELLOW}Note:${NC}"
echo -e "  • Backup files have been created for modified configs"
echo -e "  • You may need to restart your terminal for changes to take effect"
echo -e "  • The StageFlow source code in ${BLUE}$SCRIPT_DIR${NC} remains intact"
echo ""
