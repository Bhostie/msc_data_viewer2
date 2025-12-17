# Quick Start Guide

## Getting Started in 3 Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or use the automated script:

```bash
./run.sh
```

### 2. Run the Application

**Option A - Using Python directly:**
```bash
python app.py
```

**Option B - Using Flask CLI:**
```bash
flask run
```

**Option C - Using the run script (recommended):**
```bash
./run.sh
```

### 3. Open in Browser

Navigate to: **http://localhost:5000**

## First Time Setup

1. **Upload Database**: Click "Upload Database" and select your AWARE keyboard `.db` file
2. **Check Settings**: Review the auto-detected column mapping in the sidebar
3. **View Segments**: Browse through the segmented keystroke data
4. **Clean Data**: Mark sensitive segments for deletion
5. **Export**: Save the cleaned database

## Quick Tips

- **Search**: Use the filter box to find specific text
- **Keyboard Shortcut**: Press `Ctrl/Cmd + K` to focus the search box
- **Batch Delete**: Use search + "Mark ALL for Deletion" to quickly remove unwanted segments
- **Mobile Friendly**: Works great on phones and tablets too!

## Troubleshooting

**Port already in use?**
```bash
flask run --port 5001
```

**Database upload fails?**
- Check file size (max 500MB by default)
- Ensure it's a valid SQLite database

**No segments showing?**
- Verify column mapping in settings
- Check if timestamp column is correct

## Development Mode

To enable debug mode with auto-reload:

```bash
export FLASK_ENV=development
flask run --debug
```

## Need Help?

See the full [README.md](README.md) for detailed documentation.
