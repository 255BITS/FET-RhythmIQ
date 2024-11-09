// RhythmIQ - Custom JavaScript functions

// Global variables
let audioContext;
let currentSource;
let isPlaying = false;

// Function to initiate the continuous music stream
function startMusicStream() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    
    if (!isPlaying) {
        isPlaying = true;
        fetchAndPlayNextSong();
        updateUIForPlayback(true);
    }
}

// Function to pause the current music stream
function pauseMusicStream() {
    if (isPlaying && currentSource) {
        currentSource.stop();
        isPlaying = false;
        updateUIForPlayback(false);
    }
}

// Function to skip to the next generated song
function skipSong() {
    if (currentSource) {
        currentSource.stop();
    }
    fetchAndPlayNextSong();
}

// Helper function to fetch and play the next song
function fetchAndPlayNextSong() {
    fetch('/api/next-song')
        .then(response => response.json())
        .then(data => {
            playSong(data.audio_url);
            updateSongInfo(data);
        })
        .catch(error => console.error('Error fetching next song:', error));
}

// Helper function to play a song given its URL
function playSong(audioUrl) {
    fetch(audioUrl)
        .then(response => response.arrayBuffer())
        .then(arrayBuffer => audioContext.decodeAudioData(arrayBuffer))
        .then(audioBuffer => {
            if (currentSource) {
                currentSource.stop();
            }
            currentSource = audioContext.createBufferSource();
            currentSource.buffer = audioBuffer;
            currentSource.connect(audioContext.destination);
            currentSource.start();
            currentSource.onended = fetchAndPlayNextSong;
        })
        .catch(error => console.error('Error playing song:', error));
}

// Function to update the generation queue display
function updateQueue() {
    htmx.trigger('#queue-container', 'update-queue');
}

// Function to update UI elements based on playback state
function updateUIForPlayback(isPlaying) {
    const playButton = document.getElementById('play-button');
    const pauseButton = document.getElementById('pause-button');
    
    if (isPlaying) {
        playButton.classList.add('hidden');
        pauseButton.classList.remove('hidden');
    } else {
        playButton.classList.remove('hidden');
        pauseButton.classList.add('hidden');
    }
}

// Function to update song information display
function updateSongInfo(songData) {
    const songInfoContainer = document.getElementById('song-info');
    songInfoContainer.innerHTML = `
        <h2>${songData.name}</h2>
        <p>Created: ${new Date(songData.created_at).toLocaleString()}</p>
        <p>Tags: ${songData.tags.join(', ')}</p>
    `;
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners
    document.getElementById('play-button').addEventListener('click', startMusicStream);
    document.getElementById('pause-button').addEventListener('click', pauseMusicStream);
    document.getElementById('skip-button').addEventListener('click', skipSong);
    
    // Set up periodic queue updates
    setInterval(updateQueue, 5000);
});