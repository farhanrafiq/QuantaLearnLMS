// QuantaFONS Transport Management Module
// Handles live bus tracking, fuel analytics, and fleet management

const TransportManager = {
    map: null,
    busMarkers: {},
    busData: {},
    charts: {},
    socket: null,
    refreshInterval: null,
    selectedBusId: null,

    init() {
        console.log('Initializing Transport Manager...');
        this.setupMap();
        this.setupSocketIO();
        this.setupEventListeners();
        this.loadBuses();
        this.loadAlerts();
        this.setupAutoRefresh();
        this.initializeCharts();
    },

    setupMap() {
        try {
            // Initialize Leaflet map
            this.map = L.map('transportMap').setView([28.6139, 77.2090], 12); // Default to Delhi

            // Add OpenStreetMap tiles
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.map);

            // Map controls
            this.setupMapControls();

            console.log('Map initialized successfully');
        } catch (error) {
            console.error('Error initializing map:', error);
            document.getElementById('transportMap').innerHTML = `
                <div class="d-flex align-items-center justify-content-center h-100">
                    <div class="text-center text-muted">
                        <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                        <p>Map could not be loaded</p>
                    </div>
                </div>
            `;
        }
    },

    setupMapControls() {
        const refreshBtn = document.getElementById('refreshMap');
        const centerBtn = document.getElementById('centerMap');
        const fullscreenBtn = document.getElementById('toggleFullscreen');

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadBuses();
                window.QuantaFONS.Utils.showToast('Map refreshed', 'success');
            });
        }

        if (centerBtn) {
            centerBtn.addEventListener('click', () => {
                this.centerMapOnBuses();
            });
        }

        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => {
                this.toggleFullscreen();
            });
        }
    },

    setupSocketIO() {
        if (window.QuantaFONS.socket) {
            this.socket = window.QuantaFONS.socket;

            // Listen for real-time telemetry updates
            this.socket.on('telemetry_update', (data) => {
                this.handleTelemetryUpdate(data);
            });

            // Join transport room for real-time updates
            this.socket.emit('join_transport_room');

            console.log('Transport SocketIO handlers registered');
        }
    },

    setupEventListeners() {
        // Tab change handlers
        document.addEventListener('shown.bs.tab', (e) => {
            if (e.target.id === 'fuel-tab') {
                this.loadFuelAnalytics();
            }
        });

        // Bus list click handlers
        document.addEventListener('click', (e) => {
            if (e.target.closest('.bus-list-item')) {
                const busId = parseInt(e.target.closest('.bus-list-item').dataset.busId);
                this.selectBus(busId);
            }
        });
    },

    setupAutoRefresh() {
        // Refresh bus data every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadBuses();
        }, 30000);
    },

    async loadBuses() {
        try {
            const buses = await window.QuantaFONS.API.get('/transport/buses');
            this.busData = {};
            
            buses.forEach(bus => {
                this.busData[bus.id] = bus;
            });

            this.updateBusMarkers(buses);
            this.renderBusList(buses);
            this.updateStats(buses);

        } catch (error) {
            console.error('Error loading buses:', error);
            window.QuantaFONS.Utils.showToast('Failed to load bus data', 'error');
        }
    },

    updateBusMarkers(buses) {
        if (!this.map) return;

        // Clear existing markers
        Object.values(this.busMarkers).forEach(marker => {
            this.map.removeLayer(marker);
        });
        this.busMarkers = {};

        // Add new markers
        buses.forEach(bus => {
            if (bus.latest_location && bus.latest_location.latitude && bus.latest_location.longitude) {
                const marker = this.createBusMarker(bus);
                this.busMarkers[bus.id] = marker;
            }
        });
    },

    createBusMarker(bus) {
        const isOnline = bus.latest_location.engine_on;
        const iconColor = isOnline ? '#28a745' : '#dc3545';
        
        // Create custom icon
        const busIcon = L.divIcon({
            className: 'custom-bus-marker',
            html: `
                <div class="bus-marker" style="background-color: ${iconColor};">
                    <i class="fas fa-bus text-white"></i>
                </div>
            `,
            iconSize: [32, 32],
            iconAnchor: [16, 16]
        });

        const marker = L.marker(
            [bus.latest_location.latitude, bus.latest_location.longitude], 
            { icon: busIcon }
        ).addTo(this.map);

        // Add popup with bus info
        const popupContent = this.createBusPopup(bus);
        marker.bindPopup(popupContent);

        // Add click handler
        marker.on('click', () => {
            this.selectBus(bus.id);
        });

        return marker;
    },

    createBusPopup(bus) {
        const fuelPercentage = bus.fuel_tank_capacity > 0 ? 
            Math.round((bus.latest_location.fuel_level / bus.fuel_tank_capacity) * 100) : 0;
        
        const lastUpdate = bus.latest_location.timestamp ? 
            window.QuantaFONS.Utils.timeAgo(bus.latest_location.timestamp) : 'Never';

        return `
            <div class="bus-popup">
                <h6 class="mb-2">${bus.name}</h6>
                <div class="mb-2">
                    <small class="text-muted">Registration:</small><br>
                    <strong>${bus.registration_no}</strong>
                </div>
                <div class="mb-2">
                    <small class="text-muted">Status:</small><br>
                    <span class="badge bg-${bus.latest_location.engine_on ? 'success' : 'danger'}">
                        ${bus.latest_location.engine_on ? 'Online' : 'Offline'}
                    </span>
                </div>
                <div class="mb-2">
                    <small class="text-muted">Speed:</small> ${bus.latest_location.speed || 0} km/h<br>
                    <small class="text-muted">Fuel:</small> ${fuelPercentage}%
                </div>
                <div class="mb-2">
                    <small class="text-muted">Last Update:</small><br>
                    <small>${lastUpdate}</small>
                </div>
                <button class="btn btn-sm quantafons-btn-primary w-100" onclick="showBusDetails(${bus.id})">
                    View Details
                </button>
            </div>
        `;
    },

    renderBusList(buses) {
        const busListElement = document.getElementById('busList');
        if (!busListElement) return;

        if (buses.length === 0) {
            busListElement.innerHTML = `
                <div class="list-group-item text-center text-muted py-4">
                    <i class="fas fa-bus fa-2x mb-2"></i>
                    <p>No buses in fleet</p>
                </div>
            `;
            return;
        }

        const busListHTML = buses.map(bus => {
            const isOnline = bus.latest_location && bus.latest_location.engine_on;
            const fuelLevel = bus.latest_location ? bus.latest_location.fuel_level || 0 : 0;
            const fuelPercentage = bus.fuel_tank_capacity > 0 ? 
                Math.round((fuelLevel / bus.fuel_tank_capacity) * 100) : 0;
            const lastUpdate = bus.latest_location && bus.latest_location.timestamp ? 
                window.QuantaFONS.Utils.timeAgo(bus.latest_location.timestamp) : 'No data';

            return `
                <div class="list-group-item bus-list-item ${this.selectedBusId === bus.id ? 'active' : ''}" 
                     data-bus-id="${bus.id}" style="cursor: pointer;">
                    <div class="d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <h6 class="mb-1">${bus.name}</h6>
                            <p class="mb-1 small text-muted">${bus.registration_no}</p>
                            <div class="d-flex align-items-center">
                                <span class="badge bg-${isOnline ? 'success' : 'secondary'} me-2">
                                    ${isOnline ? 'Online' : 'Offline'}
                                </span>
                                <div class="fuel-gauge me-2" style="width: 50px;">
                                    <div class="fuel-level fuel-${fuelPercentage > 50 ? 'high' : fuelPercentage > 20 ? 'medium' : 'low'}" 
                                         style="width: ${fuelPercentage}%"></div>
                                </div>
                                <small class="text-muted">${fuelPercentage}%</small>
                            </div>
                            <small class="text-muted d-block mt-1">
                                <i class="fas fa-clock me-1"></i>${lastUpdate}
                            </small>
                        </div>
                        <div class="dropdown">
                            <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                <i class="fas fa-ellipsis-v"></i>
                            </button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item" href="#" onclick="showBusDetails(${bus.id})">
                                    <i class="fas fa-info-circle me-1"></i>Details
                                </a></li>
                                <li><a class="dropdown-item" href="#" onclick="TransportManager.focusBusOnMap(${bus.id})">
                                    <i class="fas fa-map-marked-alt me-1"></i>Show on Map
                                </a></li>
                                <li><a class="dropdown-item" href="#" onclick="TransportManager.viewFuelAnalytics(${bus.id})">
                                    <i class="fas fa-chart-line me-1"></i>Fuel Analytics
                                </a></li>
                            </ul>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        busListElement.innerHTML = busListHTML;
    },

    updateStats(buses) {
        // Update statistics cards
        const totalBusesEl = document.getElementById('totalBuses');
        const activeBusesEl = document.getElementById('activeBuses');
        
        if (totalBusesEl) {
            totalBusesEl.textContent = buses.length;
        }
        
        if (activeBusesEl) {
            const activeBuses = buses.filter(bus => 
                bus.latest_location && bus.latest_location.engine_on
            ).length;
            activeBusesEl.textContent = activeBuses;
        }
    },

    handleTelemetryUpdate(data) {
        const { bus_id, latitude, longitude, speed_kmh, fuel_level_liters, engine_on } = data;
        
        // Update bus data
        if (this.busData[bus_id]) {
            this.busData[bus_id].latest_location = {
                latitude,
                longitude,
                speed: speed_kmh,
                fuel_level: fuel_level_liters,
                engine_on,
                timestamp: data.timestamp
            };

            // Update marker if exists
            if (this.busMarkers[bus_id]) {
                const marker = this.busMarkers[bus_id];
                marker.setLatLng([latitude, longitude]);
                
                // Update marker icon color
                const iconColor = engine_on ? '#28a745' : '#dc3545';
                const newIcon = L.divIcon({
                    className: 'custom-bus-marker',
                    html: `
                        <div class="bus-marker" style="background-color: ${iconColor};">
                            <i class="fas fa-bus text-white"></i>
                        </div>
                    `,
                    iconSize: [32, 32],
                    iconAnchor: [16, 16]
                });
                marker.setIcon(newIcon);

                // Update popup content
                const popupContent = this.createBusPopup(this.busData[bus_id]);
                marker.getPopup().setContent(popupContent);
            }

            // Refresh bus list to show updated data
            this.renderBusList(Object.values(this.busData));
        }
    },

    selectBus(busId) {
        this.selectedBusId = busId;
        
        // Update bus list selection
        document.querySelectorAll('.bus-list-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const selectedItem = document.querySelector(`[data-bus-id="${busId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }

        // Focus on map
        this.focusBusOnMap(busId);
    },

    focusBusOnMap(busId) {
        if (!this.map || !this.busMarkers[busId]) return;

        const marker = this.busMarkers[busId];
        this.map.setView(marker.getLatLng(), 15);
        marker.openPopup();
    },

    centerMapOnBuses() {
        if (!this.map) return;

        const markers = Object.values(this.busMarkers);
        if (markers.length === 0) {
            window.QuantaFONS.Utils.showToast('No buses to center on', 'info');
            return;
        }

        const group = new L.featureGroup(markers);
        this.map.fitBounds(group.getBounds().pad(0.1));
    },

    toggleFullscreen() {
        const mapContainer = document.getElementById('transportMap').parentElement.parentElement;
        
        if (mapContainer.classList.contains('fullscreen-map')) {
            mapContainer.classList.remove('fullscreen-map');
            document.getElementById('toggleFullscreen').innerHTML = '<i class="fas fa-expand"></i>';
        } else {
            mapContainer.classList.add('fullscreen-map');
            document.getElementById('toggleFullscreen').innerHTML = '<i class="fas fa-compress"></i>';
        }

        // Trigger map resize
        setTimeout(() => {
            this.map.invalidateSize();
        }, 100);
    },

    async loadAlerts() {
        try {
            const alerts = await window.QuantaFONS.API.get('/transport/alerts');
            this.renderAlerts(alerts);
            
            // Update alerts count
            const activeAlertsEl = document.getElementById('activeAlerts');
            if (activeAlertsEl) {
                const activeCount = alerts.filter(alert => !alert.is_acknowledged).length;
                activeAlertsEl.textContent = activeCount;
            }
            
        } catch (error) {
            console.error('Error loading alerts:', error);
        }
    },

    renderAlerts(alerts) {
        const alertsListEl = document.getElementById('alertsList');
        if (!alertsListEl) return;

        const activeAlerts = alerts.filter(alert => !alert.is_acknowledged);

        if (activeAlerts.length === 0) {
            alertsListEl.innerHTML = `
                <div class="list-group-item text-center text-muted py-4">
                    <i class="fas fa-check-circle fa-2x mb-2 text-success"></i>
                    <p>No active alerts</p>
                </div>
            `;
            return;
        }

        const alertsHTML = activeAlerts.map(alert => `
            <div class="list-group-item alert-item alert-${alert.level.toLowerCase()}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">${alert.title}</h6>
                        <p class="mb-1 small">${alert.message}</p>
                        <small class="text-muted">
                            <i class="fas fa-bus me-1"></i>${alert.bus_name}
                            <i class="fas fa-clock ms-2 me-1"></i>${window.QuantaFONS.Utils.timeAgo(alert.timestamp)}
                        </small>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary" onclick="acknowledgeAlert(${alert.id})">
                        <i class="fas fa-check"></i>
                    </button>
                </div>
            </div>
        `).join('');

        alertsListEl.innerHTML = alertsHTML;
    },

    async loadFuelAnalytics() {
        const fuelAnalyticsEl = document.getElementById('fuelAnalytics');
        if (!fuelAnalyticsEl) return;

        if (!this.selectedBusId) {
            fuelAnalyticsEl.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-chart-line fa-2x mb-2"></i>
                    <p>Select a bus to view fuel analytics</p>
                </div>
            `;
            return;
        }

        try {
            window.QuantaFONS.LoadingManager.show(fuelAnalyticsEl, 'Loading fuel analytics...');
            
            const analyticsData = await window.QuantaFONS.API.get(`/transport/fuel-analytics/${this.selectedBusId}`);
            this.renderFuelAnalytics(analyticsData, fuelAnalyticsEl);
            
        } catch (error) {
            console.error('Error loading fuel analytics:', error);
            window.QuantaFONS.LoadingManager.error(fuelAnalyticsEl, 'Failed to load fuel analytics');
        }
    },

    renderFuelAnalytics(data, element) {
        const { bus_name, efficiency, events } = data;

        const analyticsHTML = `
            <div class="row mb-4">
                <div class="col-12">
                    <h5><i class="fas fa-gas-pump me-2"></i>Fuel Analytics - ${bus_name}</h5>
                </div>
            </div>
            
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="text-primary">${efficiency.overall_kmpl || 0}</h3>
                            <small class="text-muted">km/L</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="text-info">${efficiency.overall_l_per_100km || 0}</h3>
                            <small class="text-muted">L/100km</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="text-success">${efficiency.total_distance_km || 0}</h3>
                            <small class="text-muted">km traveled</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h3 class="text-warning">${efficiency.total_fuel_consumed_l || 0}</h3>
                            <small class="text-muted">L consumed</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">Fuel Efficiency Timeline</h6>
                        </div>
                        <div class="card-body">
                            <canvas id="fuelEfficiencyChart" height="200"></canvas>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">Recent Fuel Events</h6>
                        </div>
                        <div class="card-body" style="max-height: 300px; overflow-y: auto;">
                            ${this.renderFuelEvents(events)}
                        </div>
                    </div>
                </div>
            </div>
        `;

        element.innerHTML = analyticsHTML;

        // Initialize efficiency chart
        this.initializeFuelChart(efficiency.efficiency_timeline || []);
    },

    renderFuelEvents(events) {
        if (!events || events.length === 0) {
            return `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-info-circle mb-2"></i>
                    <p>No recent fuel events</p>
                </div>
            `;
        }

        return events.map(event => {
            const severityColor = {
                'CRITICAL': 'danger',
                'WARNING': 'warning',
                'INFO': 'info'
            };

            return `
                <div class="border-start border-3 border-${severityColor[event.severity] || 'info'} ps-3 mb-3">
                    <h6 class="mb-1">${event.type.replace('_', ' ').title()}</h6>
                    <p class="mb-1 small">${event.details}</p>
                    <small class="text-muted">
                        ${window.QuantaFONS.Utils.formatDateTime(event.timestamp)}
                        ${event.amount_liters ? ` • ${event.amount_liters}L` : ''}
                    </small>
                </div>
            `;
        }).join('');
    },

    initializeFuelChart(timelineData) {
        const ctx = document.getElementById('fuelEfficiencyChart');
        if (!ctx || !timelineData.length) return;

        if (this.charts.fuelEfficiency) {
            this.charts.fuelEfficiency.destroy();
        }

        this.charts.fuelEfficiency = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timelineData.map(point => 
                    window.QuantaFONS.Utils.formatDate(point.timestamp)
                ),
                datasets: [{
                    label: 'km/L',
                    data: timelineData.map(point => point.kmpl),
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    tension: 0.4,
                    fill: true
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
                        title: {
                            display: true,
                            text: 'Fuel Efficiency (km/L)'
                        }
                    }
                }
            }
        });
    },

    initializeCharts() {
        // Initialize overview charts
        setTimeout(() => {
            this.initializeBusStatusChart();
            this.initializeFuelLevelChart();
        }, 500);
    },

    initializeBusStatusChart() {
        const ctx = document.getElementById('busStatusChart');
        if (!ctx) return;

        const buses = Object.values(this.busData);
        const onlineBuses = buses.filter(bus => 
            bus.latest_location && bus.latest_location.engine_on
        ).length;
        const offlineBuses = buses.length - onlineBuses;

        if (this.charts.busStatus) {
            this.charts.busStatus.destroy();
        }

        this.charts.busStatus = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Online', 'Offline'],
                datasets: [{
                    data: [onlineBuses, offlineBuses],
                    backgroundColor: ['#28a745', '#6c757d'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Bus Status'
                    }
                }
            }
        });
    },

    initializeFuelLevelChart() {
        const ctx = document.getElementById('fuelLevelChart');
        if (!ctx) return;

        const buses = Object.values(this.busData);
        const fuelLevels = buses.map(bus => {
            if (!bus.latest_location || !bus.latest_location.fuel_level) return 0;
            return bus.fuel_tank_capacity > 0 ? 
                Math.round((bus.latest_location.fuel_level / bus.fuel_tank_capacity) * 100) : 0;
        });

        const highFuel = fuelLevels.filter(level => level > 70).length;
        const mediumFuel = fuelLevels.filter(level => level > 30 && level <= 70).length;
        const lowFuel = fuelLevels.filter(level => level <= 30).length;

        if (this.charts.fuelLevel) {
            this.charts.fuelLevel.destroy();
        }

        this.charts.fuelLevel = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['High (>70%)', 'Medium (30-70%)', 'Low (<30%)'],
                datasets: [{
                    label: 'Number of Buses',
                    data: [highFuel, mediumFuel, lowFuel],
                    backgroundColor: ['#28a745', '#ffc107', '#dc3545'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Fuel Level Distribution'
                    },
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
    },

    viewFuelAnalytics(busId) {
        this.selectedBusId = busId;
        
        // Switch to fuel tab
        const fuelTab = document.getElementById('fuel-tab');
        if (fuelTab) {
            const tab = new bootstrap.Tab(fuelTab);
            tab.show();
        }
    },

    destroy() {
        // Clean up intervals
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        // Clean up socket listeners
        if (this.socket) {
            this.socket.off('telemetry_update');
            this.socket.emit('leave_transport_room');
        }

        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};

        // Clean up map
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
    }
};

// Add CSS for custom markers
const style = document.createElement('style');
style.textContent = `
    .bus-marker {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    
    .fullscreen-map {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        z-index: 9999 !important;
        background: white;
    }
    
    .fullscreen-map #transportMap {
        height: 100vh !important;
    }
    
    .bus-popup {
        min-width: 200px;
    }
    
    .custom-bus-marker {
        background: transparent !important;
        border: none !important;
    }
`;
document.head.appendChild(style);

// Make TransportManager globally available
window.TransportManager = TransportManager;

// Auto-cleanup on page unload
window.addEventListener('beforeunload', () => {
    TransportManager.destroy();
});

console.log('QuantaFONS transport.js loaded successfully');
