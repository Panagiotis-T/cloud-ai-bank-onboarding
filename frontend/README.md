# Cloud AI Bank Onboarding - Frontend

React + Vite + Tailwind CSS frontend for the banking onboarding chatbot.

## Prerequisites

- Node.js >= 18.x
- npm >= 9.x
- Backend API running on `http://localhost:8000`

## Setup Instructions

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### 3. Build for Production

```bash
npm run build
```

## Project Structure

```
frontend/
├── src/
│   ├── App.jsx          # Main chat interface component
│   ├── main.jsx         # React entry point
│   └── index.css        # Tailwind CSS styles
├── index.html           # HTML template that is initialy loaded by the browser
├── package.json         # Dependencies
├── tailwind.config.js   # Tailwind configuration
├── postcss.config.js    # PostCSS configuration
└── vite.config.js       # Vite configuration
```

## Usage

1. Ensure backend is running: `uvicorn src.main:app --reload --port 8000` (from backend folder)
2. Start frontend: `npm run dev` (from frontend folder)
3. Open browser to `http://localhost:5173`
4. Start chatting with the onboarding agent!

## Features

- ✅ Real-time chat interface
- ✅ Session management
- ✅ Message history
- ✅ Loading indicators
- ✅ Responsive design
- ✅ Clean Tailwind CSS styling

## API Configuration

The API URL is configured in `src/App.jsx`:

```javascript
const API_URL = 'http://localhost:8000';
```

Change this if your backend runs on a different port.

## Troubleshooting

**CORS errors?**
- Ensure backend CORS is configured to allow `http://localhost:5173`
- Check backend is running on port 8000

**Connection refused?**
- Verify backend is running: `curl http://localhost:8000/health`
- Check API_URL in App.jsx matches your backend

**Styling not working?**
- Run `npm install` again
- Clear browser cache
- Check `index.css` has Tailwind directives