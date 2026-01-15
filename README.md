# Smart Queue Management System

A comprehensive Django-based virtual queue management system for hospitals, banks, ration shops, and government offices.

## Features

### 🏥🏦🏢 Multi-Service Platform
- Hospital queues
- Bank services
- Ration shop management
- Government office services

### 🔑 Universal Queue ID (UQID)
- Unique identifier for each user (e.g., UQID2026-000123)
- Valid across all services
- One-time registration

### 📱 User Features
- Online queue joining
- Real-time queue status
- Estimated waiting time
- Queue history tracking

### 🎤 Voice Assistant
- Voice commands for queue status
- Text-to-speech responses
- Speech-to-text input
- Local language support ready

### 👨‍💼 Admin Dashboard
- Manage multiple service queues
- Call next token
- Mark services complete
- Real-time queue monitoring

## Technology Stack

- **Backend**: Django 6.0.1
- **Database**: SQLite (development) / MySQL (production)
- **Frontend**: HTML, CSS, JavaScript
- **Voice**: SpeechRecognition, pyttsx3

## Installation

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv myvenv
   myvenv\Scripts\activate  # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
5. Create superuser:
   ```bash
   python manage.py createsuperuser
   ```
6. Run server:
   ```bash
   python manage.py runserver
   ```

## Project Structure

```
smart_queue/
├── accounts/          # User management
├── services/          # Service definitions
├── queue_system/      # Queue logic
├── admin_panel/       # Admin interface
├── voice_assistant/   # Voice features
└── smart_queue/       # Main settings
```

## Database Models

### User Model
- UQID (Universal Queue ID)
- Phone number
- Standard Django user fields

### Service Model
- Service type (Hospital, Bank, etc.)
- Location
- Number of counters
- Average service time

### Queue Model
- User reference
- Service reference
- Token number
- Status (Waiting/Serving/Completed)
- Timestamps

## Usage

1. **Registration**: Users register once and get UQID
2. **Join Queue**: Select service and join queue
3. **Track Status**: View real-time queue position
4. **Voice Commands**: Use voice assistant for status
5. **Admin Management**: Staff manage queues via dashboard

## Voice Assistant Commands

- "What is my queue number?"
- "How much time remaining?"
- "Which counter is serving now?"

## Future Enhancements

- QR code integration
- SMS notifications
- Local language voice support
- Emergency priority queues
- Analytics dashboard

## License

This project is for educational purposes.