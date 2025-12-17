# AWARE Keyboard Viewer - Flask Edition

A web application to view, segment, and clean keyboard keystroke logs from AWARE Framework. Built with Flask and Bootstrap for a responsive, mobile-friendly experience.

## Features

- 📂 **Database Upload**: Upload SQLite database files from AWARE
- 🔍 **Smart Segmentation**: Automatically segments keystrokes into meaningful text messages
- 🔎 **Text Search**: Filter segments by text content
- 🗑️ **Segment Management**: Mark segments for deletion and export cleaned database
- ⚙️ **Customizable Settings**: Configure column mapping, segmentation rules, and display options
- 📱 **Mobile Responsive**: Works seamlessly on desktop, tablet, and mobile devices
- 📊 **Detailed View**: Expand segments to view individual keystrokes with metadata

## Segmentation Logic

The app intelligently segments keystrokes using multiple heuristics:

- **Enter Key Detection**: Segments text when Enter/Return is pressed (keycode 66)
- **IME Actions**: Recognizes Submit/Send/Done actions (GO=2, SEARCH=3, SEND=4, DONE=6)
- **Context Changes**: Segments when switching apps or input fields
- **Idle Gaps**: Creates new segments after configurable idle periods (default: 10 seconds)
- **Text Snapshots**: Uses captured text field content when available
- **Backspace Handling**: Accurately reconstructs typed text with backspace support

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone or download this repository**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```
   
   Or using Flask CLI:
   ```bash
   flask run
   ```

4. **Open in browser**:
   Navigate to `http://localhost:5000`

## Usage

### 1. Upload Database

- Click "Upload Database" on the home page
- Select your AWARE keyboard .db file (SQLite format)
- The app will automatically detect the keyboard table and columns

### 2. Configure Settings (Sidebar)

**Column Mapping:**
- Map database columns to standard fields (timestamp, key_code, text, etc.)
- The app auto-detects common column names but you can override them

**Segmentation Rules:**
- **Idle Gap**: Time in seconds after which a new segment starts (default: 10)
- **Enter Keycodes**: Key codes that trigger segment finalization (default: 66 for Android Enter)
- **IME Actions**: Submit actions that end segments (GO, SEARCH, SEND, DONE)
- **Context Change**: Finalize segments when app or input field changes

**Display Options:**
- **Load Rows**: Limit number of rows to load (0 = all rows)
- **Segments Per Page**: Number of segments to display per page

### 3. View and Filter Segments

- Use the search box to filter segments by text content
- Navigate between pages using pagination controls
- Expand segments to view detailed keystroke data

### 4. Delete Sensitive Data

- Click "🗑️ Delete" on individual segments to mark them for deletion
- Or use "Mark ALL for Deletion" to mark all visible segments
- Marked segments are highlighted in red
- Click "↩️ Unmark" to remove deletion mark

### 5. Export Cleaned Database

- Click "Save Filtered DB" to create a new database without marked segments
- Download the filtered database using "Download Filtered DB"
- The filtered database preserves all schema and other tables

## Project Structure

```
msc_data_viewer2/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── templates/
│   ├── base.html              # Base HTML template
│   └── index.html             # Main viewer page
├── static/
│   ├── css/
│   │   └── style.css          # Custom styles
│   └── js/
│       └── app.js             # Client-side functionality
└── data/
    ├── uploads/               # Uploaded databases (auto-created)
    └── filtered/              # Filtered databases (auto-created)
```

## Configuration

### Environment Variables

- `SECRET_KEY`: Flask secret key for session management (default: 'dev-secret-key-change-in-production')
- Set in production: `export SECRET_KEY='your-secure-random-key'`

### File Limits

- Maximum upload size: 500MB (configurable in `app.py`)

## Database Schema Requirements

The app works with AWARE Framework keyboard plugin databases. Expected columns (auto-detected):

- `timestamp` or `time`: Unix timestamp in milliseconds
- `key_code` or `code`: Android key code
- `key_character` or `char`: Character typed
- `text` or `current_text`: Current text field content
- `package_name` or `package`: App package name
- `label` or `field`: Input field label/hint
- `key_action` or `action`: IME action code

## Mobile Support

The app is fully responsive and optimized for mobile devices:

- Touch-friendly buttons and controls
- Optimized font sizes (16px minimum to prevent iOS zoom)
- Collapsible sidebar on mobile
- Responsive tables with horizontal scrolling
- Mobile-optimized pagination

## Keyboard Shortcuts

- `Ctrl/Cmd + K`: Focus search box
- `Escape`: Clear search

## Tips

- Use the text filter to find sensitive information (passwords, personal data)
- Mark segments in bulk using search + "Mark ALL for Deletion"
- Review expanded keystrokes to verify segment accuracy
- Always download the filtered database before clearing deletion marks
- The original uploaded database is never modified

## Troubleshooting

### Database not loading

- Ensure the file is a valid SQLite database
- Check that it contains keyboard data from AWARE
- Try uploading a smaller database first to test

### Segments not appearing correctly

- Adjust column mapping in settings
- Try different segmentation rules (IME actions, idle gap)
- Check if timestamp column is correctly mapped

### Performance issues

- Limit the number of rows loaded using "Load rows" setting
- Reduce segments per page
- Filter segments to reduce visible items

## Technology Stack

- **Backend**: Flask 3.0 (Python web framework)
- **Frontend**: Bootstrap 5.3 (CSS framework)
- **Data Processing**: Pandas, NumPy
- **Database**: SQLite3
- **Icons**: Bootstrap Icons

## Comparison with Streamlit Version

This Flask version provides the same functionality as the original Streamlit version with these advantages:

- ✅ More control over UI/UX
- ✅ Better performance with AJAX for keystroke loading
- ✅ Standard web framework (easier to deploy)
- ✅ More customizable styling
- ✅ Session-based state management

## License

This project is provided as-is for research and data cleaning purposes.

## Contributing

Feel free to submit issues, feature requests, or pull requests.

## Support

For issues or questions, please refer to the AWARE Framework documentation or create an issue in this repository.

---

**Note**: This tool is designed for research purposes. Always handle keyboard data responsibly and ensure compliance with privacy regulations and ethical guidelines.
