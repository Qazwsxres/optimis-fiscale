/**
 * NUMMA - MODULE POINTAGES SYNCHRONISÉS
 * Synchronisation des pointages avec le backend
 * Backend: https://optimis-fiscale-production.up.railway.app
 */

// =====================================================
// CONFIGURATION
// =====================================================

const POINTAGE_CONFIG = {
    API_BASE: 'https://optimis-fiscale-production.up.railway.app',
    ENDPOINTS: {
        CLOCK_IN: '/api/pointages/clock-in',
        CLOCK_OUT: '/api/pointages/clock-out',
        LIST: '/api/pointages',
        EMPLOYEE_POINTAGES: '/api/pointages/employee',
        STATS: '/api/pointages/stats',
        EXPORT: '/api/pointages/export'
    },
    SYNC_INTERVAL: 60000, // Sync toutes les 60 secondes
    AUTO_SYNC: true
};

// =====================================================
// API CLIENT
// =====================================================

class PointageAPI {
    constructor() {
        this.baseURL = POINTAGE_CONFIG.API_BASE;
        this.syncInterval = null;
    }
    
    getHeaders() {
        const token = localStorage.getItem('authToken') || 'demo-token';
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                ...this.getHeaders(),
                ...options.headers
            }
        };
        
        console.log(`⏰ Pointage API: ${options.method || 'GET'} ${endpoint}`);
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            if (response.status === 204) return null;
            
            return await response.json();
        } catch (error) {
            console.error('❌ Pointage API Error:', error);
            throw error;
        }
    }
    
    /**
     * Pointer l'arrivée
     */
    async clockIn(employeeData) {
        return await this.request(POINTAGE_CONFIG.ENDPOINTS.CLOCK_IN, {
            method: 'POST',
            body: JSON.stringify(employeeData)
        });
    }
    
    /**
     * Pointer le départ
     */
    async clockOut(pointageId) {
        return await this.request(POINTAGE_CONFIG.ENDPOINTS.CLOCK_OUT, {
            method: 'POST',
            body: JSON.stringify({ pointage_id: pointageId })
        });
    }
    
    /**
     * Liste tous les pointages
     */
    async list(filters = {}) {
        const params = new URLSearchParams(filters);
        return await this.request(`${POINTAGE_CONFIG.ENDPOINTS.LIST}?${params}`);
    }
    
    /**
     * Pointages d'un employé
     */
    async getEmployeePointages(employeeId, filters = {}) {
        const params = new URLSearchParams(filters);
        return await this.request(`${POINTAGE_CONFIG.ENDPOINTS.EMPLOYEE_POINTAGES}/${employeeId}?${params}`);
    }
    
    /**
     * Statistiques
     */
    async getStats(filters = {}) {
        const params = new URLSearchParams(filters);
        return await this.request(`${POINTAGE_CONFIG.ENDPOINTS.STATS}?${params}`);
    }
    
    /**
     * Exporter
     */
    async export(filters = {}) {
        const params = new URLSearchParams(filters);
        return await this.request(`${POINTAGE_CONFIG.ENDPOINTS.EXPORT}?${params}`);
    }
    
    /**
     * Démarre la synchronisation automatique
     */
    startAutoSync() {
        if (this.syncInterval) return;
        
        this.syncInterval = setInterval(() => {
            this.syncPendingPointages();
        }, POINTAGE_CONFIG.SYNC_INTERVAL);
        
        console.log('✅ Auto-sync pointages démarré');
    }
    
    /**
     * Arrête la synchronisation automatique
     */
    stopAutoSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
            console.log('⏸️ Auto-sync pointages arrêté');
        }
    }
    
    /**
     * Synchronise les pointages en attente
     */
    async syncPendingPointages() {
        const pending = JSON.parse(localStorage.getItem('numma_pointages_pending') || '[]');
        
        if (pending.length === 0) return;
        
        console.log(`🔄 Synchronisation de ${pending.length} pointage(s)...`);
        
        for (const pointage of pending) {
            try {
                await this.clockIn(pointage);
                // Retirer de la file d'attente
                const index = pending.indexOf(pointage);
                pending.splice(index, 1);
            } catch (error) {
                console.error('Erreur sync pointage:', error);
                // Garder dans la file
            }
        }
        
        localStorage.setItem('numma_pointages_pending', JSON.stringify(pending));
    }
}

const pointageAPI = new PointageAPI();

// =====================================================
// GESTION DES POINTAGES
// =====================================================

/**
 * Pointer (Arrivée/Départ)
 */
async function clockIn() {
    const employeeName = document.getElementById('employeeSelect')?.value;
    
    if (!employeeName) {
        showWarning('Sélection requise', 'Veuillez sélectionner un employé');
        return;
    }
    
    const now = new Date();
    const time = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    const date = now.toLocaleDateString('fr-FR');
    
    const pointageData = {
        employee_name: employeeName,
        clock_in_time: now.toISOString(),
        date: date,
        time: time
    };
    
    try {
        showMessage('pointages', 'processing', `Enregistrement du pointage pour ${employeeName}...`);
        
        // Envoyer au backend
        const result = await pointageAPI.clockIn(pointageData);
        
        console.log('✅ Pointage enregistré:', result);
        
        showMessage('pointages', 'clocked',
            `${employeeName} a pointé`,
            `${time} - ${date}`
        );
        
        // Mettre à jour l'affichage
        await updateClockHistoryTable();
        updateClockStats();
        
    } catch (error) {
        console.error('Erreur pointage:', error);
        
        // Sauvegarder en local en attendant la sync
        savePendingPointage(pointageData);
        
        showWarning('Pointage sauvegardé', 
            'Pointage enregistré localement. Sera synchronisé automatiquement.');
    }
}

/**
 * Sauvegarde un pointage en attente de sync
 */
function savePendingPointage(pointageData) {
    const pending = JSON.parse(localStorage.getItem('numma_pointages_pending') || '[]');
    pending.push(pointageData);
    localStorage.setItem('numma_pointages_pending', JSON.stringify(pending));
    
    // Sauvegarder aussi dans l'historique local
    saveClockToLocal(pointageData);
}

/**
 * Sauvegarde locale (fallback)
 */
function saveClockToLocal(clockData) {
    const clockHistory = JSON.parse(localStorage.getItem('numma_clock_data') || '[]');
    clockHistory.push(clockData);
    localStorage.setItem('numma_clock_data', JSON.stringify(clockHistory));
}

/**
 * Met à jour le tableau d'historique
 */
async function updateClockHistoryTable() {
    try {
        // Essayer de charger depuis le backend
        const pointages = await pointageAPI.list({
            date_from: getToday(),
            date_to: getToday()
        });
        
        displayClockHistory(pointages);
        
    } catch (error) {
        console.error('Erreur chargement pointages:', error);
        
        // Fallback: charger depuis localStorage
        const localData = JSON.parse(localStorage.getItem('numma_clock_data') || '[]');
        displayClockHistory(localData);
    }
}

/**
 * Affiche l'historique des pointages
 */
function displayClockHistory(pointages) {
    const table = document.getElementById('clockHistoryTable');
    if (!table) return;
    
    const tbody = table.querySelector('tbody') || table;
    
    if (!pointages || pointages.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem;">Aucun pointage aujourd\'hui</td></tr>';
        return;
    }
    
    tbody.innerHTML = pointages.map(p => {
        const duration = calculateDuration(p.clock_in_time, p.clock_out_time);
        const status = p.clock_out_time ? 'Parti' : 'Présent';
        const statusBadge = p.clock_out_time 
            ? '<span class="badge">Parti</span>' 
            : '<span class="badge badge-success">Présent</span>';
        
        return `
            <tr>
                <td>${p.employee_name}</td>
                <td>${formatDate(p.date)}</td>
                <td>${formatTime(p.clock_in_time)}</td>
                <td>${p.clock_out_time ? formatTime(p.clock_out_time) : '--:--'}</td>
                <td>${duration}</td>
                <td>${statusBadge}</td>
            </tr>
        `;
    }).join('');
}

/**
 * Met à jour les statistiques
 */
async function updateClockStats() {
    try {
        const stats = await pointageAPI.getStats({
            date: getToday()
        });
        
        document.getElementById('presentCount').textContent = stats.present || 0;
        document.getElementById('absentCount').textContent = stats.absent || 0;
        document.getElementById('totalHoursToday').textContent = (stats.total_hours || 0).toFixed(1);
        
    } catch (error) {
        console.error('Erreur chargement stats:', error);
        
        // Calculer depuis les données locales
        const localData = JSON.parse(localStorage.getItem('numma_clock_data') || '[]');
        const today = getToday();
        const todayData = localData.filter(p => p.date === today);
        
        const present = todayData.filter(p => !p.departTime).length;
        const absent = getEmployeeCount() - present;
        
        document.getElementById('presentCount').textContent = present;
        document.getElementById('absentCount').textContent = absent;
    }
}

/**
 * Exporte les pointages
 */
async function exportPointage() {
    try {
        showMessage('exports', 'processing', 'Export des pointages...');
        
        const data = await pointageAPI.export({
            format: 'csv',
            date_from: getFirstDayOfMonth(),
            date_to: getToday()
        });
        
        // Si retour CSV
        if (typeof data === 'string') {
            downloadCSV(data, `pointages_${getToday()}.csv`);
        }
        
        showSuccess('Export réussi', 'Pointages exportés en CSV');
        
    } catch (error) {
        console.error('Erreur export:', error);
        
        // Fallback: export local
        exportPointageLocal();
    }
}

/**
 * Export local des pointages
 */
function exportPointageLocal() {
    const clockData = JSON.parse(localStorage.getItem('numma_clock_data') || '[]');
    
    if (clockData.length === 0) {
        showWarning('Aucune donnée', 'Aucun pointage à exporter');
        return;
    }
    
    let csv = 'Employé,Date,Arrivée,Départ,Durée,Statut\n';
    
    clockData.forEach(entry => {
        csv += `"${entry.employee_name}","${entry.date}","${entry.time}","${entry.departTime || '--:--'}","${entry.duration || 'En cours'}","${entry.status || 'Présent'}"\n`;
    });
    
    downloadCSV(csv, `pointages_${getToday()}.csv`);
    
    showSuccess('Export réussi', 'Pointages exportés en CSV');
}

// =====================================================
// UTILITAIRES
// =====================================================

function getToday() {
    return new Date().toISOString().split('T')[0];
}

function getFirstDayOfMonth() {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR');
}

function formatTime(timeString) {
    if (!timeString) return '--:--';
    const date = new Date(timeString);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

function calculateDuration(start, end) {
    if (!start || !end) return '-';
    
    const startDate = new Date(start);
    const endDate = new Date(end);
    const diff = endDate - startDate;
    
    const hours = Math.floor(diff / 1000 / 60 / 60);
    const minutes = Math.floor((diff / 1000 / 60) % 60);
    
    return `${hours}h ${minutes}min`;
}

function downloadCSV(csvContent, filename) {
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function getEmployeeCount() {
    const employees = JSON.parse(localStorage.getItem('numma_employees') || '[]');
    return employees.length;
}

// =====================================================
// INITIALISATION
// =====================================================

console.log('✅ Module Pointages synchronisés chargé');

// Démarrer l'auto-sync
if (POINTAGE_CONFIG.AUTO_SYNC) {
    pointageAPI.startAutoSync();
}

// Mettre à jour l'affichage toutes les 30 secondes
setInterval(() => {
    if (document.getElementById('clockHistoryTable')) {
        updateClockHistoryTable();
        updateClockStats();
    }
}, 30000);

// Export global
window.pointageAPI = pointageAPI;
window.clockIn = clockIn;
window.updateClockHistoryTable = updateClockHistoryTable;
window.updateClockStats = updateClockStats;
window.exportPointage = exportPointage;
