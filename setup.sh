#!/bin/bash

# Avantis Trading Bot Setup Script
# This script sets up the repository with the SDK submodule

echo "🚀 Setting up Avantis Trading Bot..."
echo "=================================="

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "❌ Git is required but not installed. Please install git first."
    exit 1
fi

# Initialize and update submodules
echo "📦 Initializing Avantis SDK submodule..."
git submodule update --init --recursive

if [ $? -eq 0 ]; then
    echo "✅ SDK submodule initialized successfully"
else
    echo "❌ Failed to initialize SDK submodule"
    exit 1
fi

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Python dependencies installed successfully"
else
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

# Copy configuration template
echo "⚙️ Setting up configuration..."
if [ ! -f .env ]; then
    cp config.env.example .env
    echo "✅ Configuration template copied to .env"
    echo "⚠️  Please edit .env file with your private key and settings"
else
    echo "ℹ️  .env file already exists, skipping..."
fi

# Copy aggressive configuration template
if [ ! -f config_aggressive.env ]; then
    cp config_aggressive.env.example config_aggressive.env
    echo "✅ Aggressive configuration template copied to config_aggressive.env"
    echo "⚠️  Please edit config_aggressive.env file with your settings"
else
    echo "ℹ️  config_aggressive.env file already exists, skipping..."
fi

# Make run scripts executable
chmod +x run_aggressive_bot.py
chmod +x demo_compound_growth.py

echo ""
echo "🎉 Setup completed successfully!"
echo "================================"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your PRIVATE_KEY"
echo "2. Configure your trading parameters in config_aggressive.env"
echo "3. Test the bot: python run_aggressive_bot.py --dry-run"
echo "4. Check projections: python run_aggressive_bot.py --projections"
echo "5. Start trading: python run_aggressive_bot.py"
echo ""
echo "⚠️  IMPORTANT:"
echo "- Start with small amounts to test the bot"
echo "- Trading involves risk of loss"
echo "- Never risk more than you can afford to lose"
echo ""
echo "📚 Documentation: README.md"
echo "🐛 Issues: https://github.com/MeltedMindz/avantis-trading-bot/issues"
echo ""
echo "🚀 Happy trading!"
