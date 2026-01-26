/**
 * ========================================
 * NUMMA - MODULE POINTAGES SYNCHRONISÉS v3.0
 * ========================================
 * Synchronisation des pointages avec le backend
 * Backend: https://optimis-fiscale-production.up.railway.app
 * 
 * DÉPENDANCES: numma-messages.js (REQUIS)
 */

(function() {
    'use strict';

    console.log('⏰ Chargement module Pointages...');

    // Vérifier que numma-messages.js est chargé
    if (typeof showMessage === 'undefined') {
        console.error('❌ ERREUR: numma-messages.js doit être chargé AVANT numma-pointages.js');
        return;
    }

    // =====================================================
    // CONFIGURATION
    // =====================================================

    const POINTAGE_CONFIG = {
        API_BASE: window.NUMMA_CONFIG?.API_BASE || 'https://optimis-fiscale-production.up.railway.app',
        ENDPOINTS: {
            CLOCK_IN: '/api/pointages/clock-in',
            CLOCK_OUT: '/api/pointages/clock-out',
            LIST: '/api/pointages',
            EMPLOYEE_POINTAGES: '/api/pointages/employee',
            STATS: '/api/pointages/stats',
            EXPORT: '/api/pointages/export'
        },
        SYNC_INTERVAL: 60000, // 60 secondes
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
        
        async clockIn(employeeData) {
            return await this.request(POINTAGE_CONFIG.ENDPOINTS.CLOCK_IN, {
                method: 'POST',
                body: JSON.stringify(employeeData)
            });
        }
        
        async clockOut(pointageId) {
            return await this.request(POINTAGE_CONFIG.ENDPOINTS.CLOCK_OUT, {
                method: 'POST',
                body: JSON.stringify({ pointage_id: pointageId })
            });
        }
        
        async list(filters = {}) {
            const params = new URLSearchParams(filters);
            return await this.request(`${POINTAGE_CONFIG.ENDPOINTS.LIST}?${params}`);
        }
        
        async getEmployeePointages(employeeId, filters = {}) {
            const params = new URLSearchParams(filters);
            return await this.request(`${POINTAGE_CONFIG.ENDPOINTS.EMPLOYEE_POINTAGES}/${employeeId}?${params}`);
        }
        
        async getStats(filters = {}) {
            const params = new URLSearchParams(filters);
            return await this.request(`${POINTAGE_CONFIG.ENDPOINTS.STATS}?${params}`);
        }
        
        async export(filters = {}) {
            const params = new URLSearchParams(filters);
            return await this.request(`${POINTAGE_CONFIG.ENDPOINTS.EXPORT}?${params}`);
        }
        
        startAutoSync() {
            if (this.syncInterval) return;
            
            this.syncInterval = setInterval(() => {
                this.syncPendingPointages();
            }, POINTAGE_CONFIG.SYNC_INTERVAL);
            
            console.log('✅ Auto-sync pointages démarré');
        }
        
        stopAutoSync() {
            if (this.syncInterval) {
                clearInterval(this.syncInterval);
                this.syncInterval = null;
                console.log('⏸️ Auto-sync pointages arrêté');
            }
        }
        
        async syncPendingPointages() {
            const pending = JSON.parse(localStorage.getItem('numma_pointages_pending') || '[]');
            
            if (pending.length === 0) return;
            
            console.log(`🔄 Synchronisation de ${pending.length} pointage(s)...`);
            
            for (const pointage of pending) {
                try {
                    await this.clockIn(pointage);
                    const index = pending.indexOf(pointage);
                    pending.splice(index, 1);
                } catch (error) {
                    console.error('Erreur sync pointage:', error);
                }
            }
            
            localStorage.setItem('numma_pointages_pending', JSON.stringify(pending));
        }
    }

    const pointageAPI = new PointageAPI();

    // =====================================================
    // GESTION DES POINTAGES
    // =====================================================

    async function clockIn() {
        const employeeName = document.getElementById('clockEmployeeSelect')?.value;
        
        if (!employeeName) {
            showWarning('Veuillez sélectionner un employé');
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
            showInfo(`Enregistrement du pointage pour ${employeeName}...`);
            
            const result = await pointageAPI.clockIn(pointageData);
            console.log('✅ Pointage enregistré:', result);
            
            showSuccess(`${employeeName} a pointé - ${time} - ${date}`);
            
            await updateClockHistoryTable();
            updateClockStats();
            
        } catch (error) {
            console.error('Erreur pointage:', error);
            
            savePendingPointage(pointageData);
            showWarning('Pointage sauvegardé localement - Sera synchronisé automatiquement');
        }
    }

    function savePendingPointage(pointageData) {
        const pending = JSON.parse(localStorage.getItem('numma_pointages_pending') || '[]');
        pending.push(pointageData);
        localStorage.setItem('numma_pointages_pending', JSON.stringify(pending));
        
        saveClockToLocal(pointageData);
    }

    function saveClockToLocal(clockData) {
        const clockHistory = JSON.parse(localStorage.getItem('numma_clock_data') || '[]');
        clockHistory.push(clockData);
        localStorage.setItem('numma_clock_data', JSON.stringify(clockHistory));
    }

    async function updateClockHistoryTable() {
        try {
            const pointages = await pointageAPI.list({
                date_from: getToday(),
                date_to: getToday()
            });
            
            displayClockHistory(pointages);
            
        } catch (error) {
            console.error('Erreur chargement pointages:', error);
            
            const localData = JSON.parse(localStorage.getItem('numma_clock_data') || '[]');
            displayClockHistory(localData);
        }
    }

    function displayClockHistory(pointages) {
        const table = document.getElementById('clockHistoryTable');
        if (!table) return;
        
        if (!pointages || pointages.length === 0) {
            table.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 2rem;">Aucun pointage aujourd\'hui</td></tr>';
            return;
        }
        
        table.innerHTML = pointages.map(p => {
            const duration = calculateDuration(p.clock_in_time, p.clock_out_time);
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
                    <td style="font-size: 0.875rem; color: var(--text-gray);">${p.expected_start || '09:00'} - ${p.expected_end || '18:00'}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        }).join('');
    }

    async function updateClockStats() {
        try {
            const stats = await pointageAPI.getStats({
                date: getToday()
            });
            
            if (document.getElementById('presentCount')) {
                document.getElementById('presentCount').textContent = stats.present || 0;
            }
            if (document.getElementById('absentCount')) {
                document.getElementById('absentCount').textContent = stats.absent || 0;
            }
            if (document.getElementById('lateCount')) {
                document.getElementById('lateCount').textContent = stats.late || 0;
            }
            
        } catch (error) {
            console.error('Erreur chargement stats:', error);
            
            const localData = JSON.parse(localStorage.getItem('numma_clock_data') || '[]');
            const today = getToday();
            const todayData = localData.filter(p => p.date === today);
            
            const present = todayData.filter(p => !p.departTime).length;
            
            if (document.getElementById('presentCount')) {
                document.getElementById('presentCount').textContent = present;
            }
        }
    }

    async function exportPointage() {
        try {
            showInfo('Export des pointages...');
            
            const data = await pointageAPI.export({
                format: 'csv',
                date_from: getFirstDayOfMonth(),
                date_to: getToday()
            });
            
            if (typeof data === 'string') {
                downloadCSV(data, `pointages_${getToday()}.csv`);
            }
            
            showSuccess('Pointages exportés en CSV');
            
        } catch (error) {
            console.error('Erreur export:', error);
            exportPointageLocal();
        }
    }

    function exportPointageLocal() {
        const clockData = JSON.parse(localStorage.getItem('numma_clock_data') || '[]');
        
        if (clockData.length === 0) {
            showWarning('Aucun pointage à exporter');
            return;
        }
        
        let csv = 'Employé,Date,Arrivée,Départ,Durée,Statut\n';
        
        clockData.forEach(entry => {
            csv += `"${entry.employee_name}","${entry.date}","${entry.time}","${entry.departTime || '--:--'}","${entry.duration || 'En cours'}","${entry.status || 'Présent'}"\n`;
        });
        
        downloadCSV(csv, `pointages_${getToday()}.csv`);
        showSuccess('Pointages exportés en CSV');
    }

    function filterClocks() {
        const dateFilter = document.getElementById('dateFilter')?.value;
        const employeeFilter = document.getElementById('employeeFilter')?.value;
        const table = document.getElementById('clockHistoryTable');
        
        if (!table) return;
        
        for (let i = 0; i < table.rows.length; i++) {
            const row = table.rows[i];
            let show = true;
            
            if (employeeFilter && row.cells[0].textContent !== employeeFilter) {
                show = false;
            }
            
            if (dateFilter) {
                const rowDate = row.cells[1].textContent;
                const filterDateObj = new Date(dateFilter);
                const filterDateStr = filterDateObj.toLocaleDateString('fr-FR');
                if (rowDate !== filterDateStr) {
                    show = false;
                }
            }
            
            row.style.display = show ? '' : 'none';
        }
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
        URL.revokeObjectURL(url);
    }

    // =====================================================
    // INITIALISATION
    // =====================================================

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

    // =====================================================
    // EXPORT GLOBAL
    // =====================================================

    window.pointageAPI = pointageAPI;
    window.clockIn = clockIn;
    window.updateClockHistoryTable = updateClockHistoryTable;
    window.updateClockStats = updateClockStats;
    window.exportPointage = exportPointage;
    window.filterClocks = filterClocks;

    console.log('✅ Module Pointages chargé (avec auto-sync)');
})();
