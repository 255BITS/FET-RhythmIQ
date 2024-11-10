# RhythmIQ

## Introduction

RhythmIQ is an automated AI music generator that allows users to stream unlimited music. This web application leverages AI technology to create unique musical compositions on-the-fly, providing users with a continuous stream of fresh and original tunes.

## Usage

To use RhythmIQ, simply navigate to the home page and start the song stream. The application will automatically generate new songs using AI agents, which you can monitor in the Create Song queue.

## Files

- `main.py`: The main application file containing the Quart server setup and route handlers.
- `models.py`: Defines the Song model and database interactions using asyncpg.
- `templates/base.html`: The base HTML template for the application.
- `templates/home.html`: The template for the home page.
- `templates/create_song.html`: The template for the Create Song page.
- `static/css/custom.css`: Custom CSS styles for the application.
- `static/js/app.js`: Custom JavaScript functions for the application.

## Methods

- `generate_song()`: Asynchronous function to generate a new song using AI agents.
- `update_queue()`: Function to update the generation queue display.
- `stream_music()`: Function to handle the continuous streaming of generated music.

## Models

### Song

- `id`: Auto-incrementing primary key
- `name`: String, the name of the song
- `created_at`: DateTime, when the song was created
- `status`: String, the current status of the song (e.g., "generating", "complete")
- `details`: JSON, additional details about the song

## Available CSS styles

The project uses Tailwind CSS for styling. Custom styles can be added in `static/css/custom.css`.

## Available JS functions

The project uses Alpine.js for JavaScript functionality. Custom functions can be added in `static/js/app.js`.

- `startMusicStream()`: Initiates the continuous music stream.
- `pauseMusicStream()`: Pauses the current music stream.
- `skipSong()`: Skips to the next generated song.

## Additional notes

- This project uses HTMX for dynamic content updates without full page reloads.
- The backend is built with Quart, an asynchronous Python web framework.
- Database interactions are handled using asyncpg for PostgreSQL.
- The Git repository for this project is located at `git@github.com:255BITS/FET-RhythmIQ.git`.

To set up the project:

1. Clone the repository: `git clone git@github.com:255BITS/FET-RhythmIQ.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up the PostgreSQL database and update the connection details in the configuration.
4. Run the application: `python main.py`

Make sure to have Python 3.7+ and PostgreSQL installed on your system before running the application.

## Credits

This project was created with [appcannon](https://github.com/255BITS/appcannon), a tool from 255labs.
