#!/bin/bash
# Setup cron job để tự động refresh OneDrive cookies

echo "🔧 Setting up OneDrive Cookie Refresh Cron Job"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REFRESH_SCRIPT="$SCRIPT_DIR/refresh_onedrive_cookies.py"
LOG_FILE="/var/log/webreel_cookie_refresh.log"

# Check if script exists
if [ ! -f "$REFRESH_SCRIPT" ]; then
    echo "❌ Error: refresh_onedrive_cookies.py not found!"
    exit 1
fi

echo "✅ Found refresh script: $REFRESH_SCRIPT"
echo ""

# Create log directory if not exists
sudo mkdir -p /var/log
sudo touch "$LOG_FILE"
sudo chmod 666 "$LOG_FILE"

echo "✅ Log file: $LOG_FILE"
echo ""

# Cron job options
echo "Select refresh frequency:"
echo "1) Every month (day 1 at 00:00) - Recommended"
echo "2) Every week (Sunday at 02:00) - More frequent"
echo "3) Every 2 weeks (1st and 15th at 00:00)"
echo "4) Custom"
echo ""

read -p "Enter choice [1-4]: " choice

case $choice in
    1)
        CRON_SCHEDULE="0 0 1 * *"
        DESCRIPTION="Monthly (day 1 at 00:00)"
        ;;
    2)
        CRON_SCHEDULE="0 2 * * 0"
        DESCRIPTION="Weekly (Sunday at 02:00)"
        ;;
    3)
        CRON_SCHEDULE="0 0 1,15 * *"
        DESCRIPTION="Bi-weekly (1st and 15th at 00:00)"
        ;;
    4)
        echo ""
        echo "Enter cron schedule (e.g., '0 0 * * *' for daily at midnight):"
        read -p "Schedule: " CRON_SCHEDULE
        DESCRIPTION="Custom: $CRON_SCHEDULE"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "Selected schedule: $DESCRIPTION"
echo "Cron expression: $CRON_SCHEDULE"
echo ""

# Build cron command
CRON_COMMAND="cd $SCRIPT_DIR && python $REFRESH_SCRIPT >> $LOG_FILE 2>&1"

# Add to crontab
echo "Adding to crontab..."
(crontab -l 2>/dev/null | grep -v "refresh_onedrive_cookies.py"; echo "$CRON_SCHEDULE $CRON_COMMAND") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron job added successfully!"
    echo ""
    echo "Current crontab:"
    crontab -l | grep "refresh_onedrive_cookies.py"
    echo ""
    echo "📝 Notes:"
    echo "   - Logs will be written to: $LOG_FILE"
    echo "   - View logs: tail -f $LOG_FILE"
    echo "   - Remove cron: crontab -e (then delete the line)"
    echo ""
    echo "🧪 Test the script now:"
    echo "   python $REFRESH_SCRIPT"
else
    echo "❌ Failed to add cron job"
    exit 1
fi
