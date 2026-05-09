#!/usr/bin/env bash
# Keel — one-line install
set -e
echo "🔮 Laying the keel..."
if ! command -v cargo &>/dev/null; then
    echo "Installing Rust first..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    . "$HOME/.cargo/env"
fi
cargo install keel
echo ""
echo "🔮 Keel installed!"
echo "   Try: keel init my-project"
echo "   Then: cd my-project && keel status"
echo ""
echo "\"Constraints breed clarity.\""
