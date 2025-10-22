#!/usr/bin/env bash
# StageFlow Installation Script
# Adds bin/ to PATH and installs shell completions

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
        # Fallback to parent process
        ps -p $$ -o comm= | sed 's/-//'
    fi
}

CURRENT_SHELL=$(detect_shell)

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         StageFlow Installation Script                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Detected shell:${NC} $CURRENT_SHELL"
echo -e "${YELLOW}Project root:${NC} $SCRIPT_DIR"
echo -e "${YELLOW}Bin directory:${NC} $BIN_DIR"
echo ""

# Function to add PATH to shell config
add_to_path() {
    local shell_config=$1
    local path_line="export PATH=\"$BIN_DIR:\$PATH\""

    # Check if already in config
    if grep -Fq "$BIN_DIR" "$shell_config" 2>/dev/null; then
        echo -e "${YELLOW}✓${NC} PATH already configured in $shell_config"
        return 0
    fi

    # Create config if it doesn't exist
    if [ ! -f "$shell_config" ]; then
        touch "$shell_config"
    fi

    # Add PATH configuration
    echo "" >> "$shell_config"
    echo "# StageFlow - Added by install.sh" >> "$shell_config"
    echo "$path_line" >> "$shell_config"
    echo -e "${GREEN}✓${NC} Added to PATH in $shell_config"
    return 0
}

# Function to install completions
install_completions() {
    local shell=$1

    echo ""
    echo -e "${BLUE}Installing shell completions for $shell...${NC}"

    # Generate completion script
    case $shell in
        bash)
            local completion_dir="$HOME/.bash_completion.d"
            mkdir -p "$completion_dir"
            local completion_file="$completion_dir/stageflow.bash"

            # Generate completion using stageflow itself
            "$BIN_DIR/stageflow" --show-completion bash > "$completion_file" 2>/dev/null || {
                echo -e "${RED}✗${NC} Failed to generate bash completions"
                return 1
            }

            # Add sourcing to .bashrc if not present
            local bashrc="$HOME/.bashrc"
            if ! grep -q "bash_completion.d/stageflow.bash" "$bashrc" 2>/dev/null; then
                echo "" >> "$bashrc"
                echo "# StageFlow completion - Added by install.sh" >> "$bashrc"
                echo "[ -f $completion_file ] && source $completion_file" >> "$bashrc"
            fi

            echo -e "${GREEN}✓${NC} Installed bash completions to $completion_file"
            ;;

        zsh)
            local completion_dir="$HOME/.zsh/completions"
            mkdir -p "$completion_dir"
            local completion_file="$completion_dir/_stageflow"

            # Generate completion using stageflow itself
            "$BIN_DIR/stageflow" --show-completion zsh > "$completion_file" 2>/dev/null || {
                echo -e "${RED}✗${NC} Failed to generate zsh completions"
                return 1
            }

            # Add to fpath in .zshrc if not present
            local zshrc="$HOME/.zshrc"
            if ! grep -q ".zsh/completions" "$zshrc" 2>/dev/null; then
                echo "" >> "$zshrc"
                echo "# StageFlow completion - Added by install.sh" >> "$zshrc"
                echo "fpath=($completion_dir \$fpath)" >> "$zshrc"
                echo "autoload -Uz compinit && compinit" >> "$zshrc"
            fi

            echo -e "${GREEN}✓${NC} Installed zsh completions to $completion_file"
            ;;

        fish)
            local completion_dir="$HOME/.config/fish/completions"
            mkdir -p "$completion_dir"
            local completion_file="$completion_dir/stageflow.fish"

            # Generate completion using stageflow itself
            "$BIN_DIR/stageflow" --show-completion fish > "$completion_file" 2>/dev/null || {
                echo -e "${RED}✗${NC} Failed to generate fish completions"
                return 1
            }

            echo -e "${GREEN}✓${NC} Installed fish completions to $completion_file"
            ;;

        *)
            echo -e "${YELLOW}⚠${NC} Shell '$shell' not fully supported for auto-completion"
            echo -e "   You can manually run: ${BLUE}stageflow --install-completion${NC}"
            return 1
            ;;
    esac

    return 0
}

# Main installation process
echo -e "${BLUE}[1/2] Adding StageFlow to PATH...${NC}"

case $CURRENT_SHELL in
    bash)
        add_to_path "$HOME/.bashrc"
        ;;
    zsh)
        add_to_path "$HOME/.zshrc"
        ;;
    fish)
        # Fish uses different syntax
        set -l fish_config "$HOME/.config/fish/config.fish"
        mkdir -p "$(dirname "$fish_config")"
        if ! grep -Fq "$BIN_DIR" "$fish_config" 2>/dev/null; then
            echo "" >> "$fish_config"
            echo "# StageFlow - Added by install.sh" >> "$fish_config"
            echo "set -gx PATH $BIN_DIR \$PATH" >> "$fish_config"
            echo -e "${GREEN}✓${NC} Added to PATH in $fish_config"
        else
            echo -e "${YELLOW}✓${NC} PATH already configured in $fish_config"
        fi
        ;;
    *)
        echo -e "${YELLOW}⚠${NC} Unsupported shell: $CURRENT_SHELL"
        echo -e "   Please manually add ${BLUE}$BIN_DIR${NC} to your PATH"
        ;;
esac

echo ""
echo -e "${BLUE}[2/2] Installing shell completions...${NC}"

if install_completions "$CURRENT_SHELL"; then
    COMPLETIONS_INSTALLED=true
else
    COMPLETIONS_INSTALLED=false
fi

# Summary
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                Installation Complete!                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$COMPLETIONS_INSTALLED" = true ]; then
    echo -e "${GREEN}✓${NC} StageFlow has been added to your PATH"
    echo -e "${GREEN}✓${NC} Shell completions have been installed"
else
    echo -e "${GREEN}✓${NC} StageFlow has been added to your PATH"
    echo -e "${YELLOW}⚠${NC} Shell completions not fully configured"
fi

echo ""
echo -e "${YELLOW}To apply changes, either:${NC}"
echo -e "  1. Restart your terminal"
echo -e "  2. Run: ${BLUE}source ~/.$CURRENT_SHELL""rc${NC} (or appropriate config file)"
echo ""
echo -e "${YELLOW}To verify installation:${NC}"
echo -e "  ${BLUE}stageflow --help${NC}"
echo ""
echo -e "${YELLOW}To test completions (after sourcing):${NC}"
echo -e "  Type ${BLUE}stageflow ${NC}and press TAB"
echo ""
