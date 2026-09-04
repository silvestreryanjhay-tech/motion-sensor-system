// API Configuration
const API_URL = 'http://localhost:5000/api';

// Chart instance
let motionChart = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    initializeChart();
    loadDashboardData();
    startAutoRefresh();
    setupEventListeners();
});

function initializeChart() {
    const ctx = document.getElementById('motionChart').getContext('2d');
    motionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Array.from({length: 24}, (_, i) => `${i}:00`),
            datasets: [{
                label: 'Motion Events',
                data: Array(24).fill(0),
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

async function loadDashboardData() {
    try {
        const [statusResponse, statsResponse, eventsResponse] = await Promise.all([
            fetch(`${API_URL}/status`),
            fetch(`${API_URL}/stats`),
            fetch(`${API_URL}/events`)
        ]);

        const status = await statusResponse.json();
        const stats = await statsResponse.json();
        const events = await eventsResponse.json();

        updateUI(status, stats, events);
        updateChart(stats);
        updateEventsList(events);
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showError('Failed to load dashboard data');
    }
}

function updateUI(status, stats, events) {
    // Update system status
    const statusElement = document.getElementById('systemStatus');
    if (status.status === 'active') {
        statusElement.textContent = '● System Active';
        statusElement.className = 'status-active';
    } else {
        statusElement.textContent = '● System Inactive';
        statusElement.className = 'status-inactive';
    }

    // Update motion status
    const motionStatus = document.getElementById('motionStatus');
    const motionIndicator = document.getElementById('motionIndicator');
    if (status.motion_detected) {
        motionStatus.textContent = 'Motion Detected!';
        motionStatus.style.color = '#ff1744';
        motionIndicator.className = 'indicator-red';
    } else {
        motionStatus.textContent = 'No Motion';
        motionStatus.style.color = '#333';
        motionIndicator.className = 'indicator-green';
    }

    // Update buzzer status
    const buzzerStatus = document.getElementById('buzzerStatus');
    const buzzerIndicator = document.getElementById('buzzerIndicator');
    if (status.buzzer_active) {
        buzzerStatus.textContent = 'Active';
        buzzerStatus.style.color = '#ff1744';
        buzzerIndicator.className = 'indicator-red';
    } else {
        buzzerStatus.textContent = 'Inactive';
        buzzerStatus.style.color = '#333';
        buzzerIndicator.className = 'indicator-green';
    }

    // Update stats
    document.getElementById('totalEvents').textContent = stats.total_events || 0;
    document.getElementById('lastDetection').textContent = status.last_detection || 'Never';
    
    // Update camera status
    document.getElementById('cameraStatus').textContent = 
        status.camera_active ? 'Recording' : 'Standby';
    document.getElementById('sensorStatus').textContent = 
        status.motion_detected ? 'Motion Detected' : 'Active';
}

function updateChart(stats) {
    if (stats.hourly_distribution) {
        motionChart.data.datasets[0].data = stats.hourly_distribution;
        motionChart.update();
    }
}

function updateEventsList(events) {
    const eventsList = document.getElementById('eventsList');
    if (events.length === 0) {
        eventsList.innerHTML = '<p style="text-align: center; color: #666;">No events recorded</p>';
        return;
    }

    eventsList.innerHTML = events.map(event => `
        <div class="event-item">
            <div>
                <strong>Motion Detected</strong>
                <div class="timestamp">${formatTimestamp(event.timestamp)}</div>
            </div>
            <div>
                ${event.image_path ? `<span class="badge badge-image">📸 Image</span>` : ''}
                ${event.video_path ? `<span class="badge badge-video">🎥 Video</span>` : ''}
                <span class="badge badge-motion">Motion</span>
            </div>
        </div>
    `).join('');
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function setupEventListeners() {
    // Toggle system
    document.getElementById('toggleSystem').addEventListener('click', async function() {
        const statusElement = document.getElementById('systemStatus');
        const isActive = statusElement.textContent.includes('Active');
        
        try {
            const response = await fetch(`${API_URL}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ active: !isActive })
            });
            
            if (response.ok) {
                loadDashboardData();
            }
        } catch (error) {
            console.error('Error toggling system:', error);
        }
    });

    // Manual capture
    document.getElementById('captureManual').addEventListener('click', async function() {
        try {
            const response = await fetch(`${API_URL}/capture`, {
                method: 'POST'
            });
            if (response.ok) {
                alert('Image captured successfully!');
                loadDashboardData();
            }
        } catch (error) {
            console.error('Error capturing image:', error);
        }
    });

    // Manual recording
    document.getElementById('recordManual').addEventListener('click', async function() {
        try {
            const response = await fetch(`${API_URL}/record`, {
                method: 'POST'
            });
            if (response.ok) {
                alert('Recording started!');
                loadDashboardData();
            }
        } catch (error) {
            console.error('Error recording video:', error);
        }
    });
}

function startAutoRefresh() {
    // Refresh data every 10 seconds
    setInterval(loadDashboardData, 10000);
}

function showError(message) {
    // You can implement a proper toast/notification system here
    console.error(message);
}