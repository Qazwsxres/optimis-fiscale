/**
 * ========================================
 * NUMMA - MODULE IMPORTS v3.0
 * ========================================
 * Import de fichiers avec OCR pour PDFs
 * Backend: https://optimis-fiscale-production.up.railway.app
 * 
 * DÉPENDANCES: numma-messages.js (REQUIS)
 */

(function() {
    'use strict';

    console.log('📁 Chargement module Imports...');

    // Vérifier que numma-messages.js est chargé
    if (typeof showMessage === 'undefined') {
        console.error('❌ ERREUR: numma-messages.js doit être chargé AVANT numma-imports.js');
        return;
    }

    // =====================================================
    // CONFIGURATION
    // =====================================================

    const IMPORT_CONFIG = {
        API_BASE: window.NUMMA_CONFIG?.API_BASE || 'https://optimis-fiscale-production.up.railway.app',
        ENDPOINTS: {
            UPLOAD: '/api/uploads',
            PARSE_CSV: '/api/uploads/parse-csv',
            OCR_PDF: '/api/uploads/ocr-pdf',
            IMPORT_TRANSACTIONS: '/api/uploads/import-transactions',
            IMPORT_INVOICES: '/api/uploads/import-invoices',
            LIST_IMPORTS: '/api/uploads/history'
        },
        MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
        ALLOWED_TYPES: {
            transactions: ['.csv', '.pdf', '.xlsx'],
            invoices: ['.csv', '.pdf', '.xlsx'],
            balance: ['.csv', '.pdf'],
            documents: ['.pdf', '.jpg', '.png', '.doc', '.docx']
        }
    };

    // =====================================================
    // API CLIENT
    // =====================================================

    class ImportAPI {
        constructor() {
            this.baseURL = IMPORT_CONFIG.API_BASE;
        }
        
        getHeaders(includeContentType = false) {
            const token = localStorage.getItem('authToken') || 'demo-token';
            const headers = {
                'Authorization': `Bearer ${token}`
            };
            
            if (includeContentType) {
                headers['Content-Type'] = 'application/json';
            }
            
            return headers;
        }
        
        async request(endpoint, options = {}) {
            const url = `${this.baseURL}${endpoint}`;
            const config = {
                ...options,
                headers: {
                    ...this.getHeaders(options.method !== 'POST' || !!options.body),
                    ...options.headers
                }
            };
            
            console.log(`📤 Import API: ${options.method || 'GET'} ${endpoint}`);
            
            try {
                const response = await fetch(url, config);
                
                if (!response.ok) {
                    const error = await response.json().catch(() => ({}));
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }
                
                if (response.status === 204) return null;
                
                return await response.json();
            } catch (error) {
                console.error('❌ Import API Error:', error);
                throw error;
            }
        }
        
        async uploadFile(file, type) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('type', type);
            
            return await this.request(IMPORT_CONFIG.ENDPOINTS.UPLOAD, {
                method: 'POST',
                body: formData,
                headers: this.getHeaders(false)
            });
        }
        
        async parseCSV(fileId) {
            return await this.request(`${IMPORT_CONFIG.ENDPOINTS.PARSE_CSV}/${fileId}`, {
                method: 'POST'
            });
        }
        
        async ocrPDF(fileId) {
            return await this.request(`${IMPORT_CONFIG.ENDPOINTS.OCR_PDF}/${fileId}`, {
                method: 'POST'
            });
        }
        
        async importTransactions(data) {
            return await this.request(IMPORT_CONFIG.ENDPOINTS.IMPORT_TRANSACTIONS, {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }
        
        async importInvoices(data) {
            return await this.request(IMPORT_CONFIG.ENDPOINTS.IMPORT_INVOICES, {
                method: 'POST',
                body: JSON.stringify(data)
            });
        }
        
        async listImports() {
            return await this.request(IMPORT_CONFIG.ENDPOINTS.LIST_IMPORTS);
        }
    }

    const importAPI = new ImportAPI();

    // =====================================================
    // GESTION DES UPLOADS
    // =====================================================

    function initializeDropZones() {
        const dropZones = document.querySelectorAll('.upload-zone');
        
        dropZones.forEach(zone => {
            const input = zone.querySelector('input[type="file"]');
            const type = zone.dataset.type;
            
            zone.addEventListener('click', () => {
                input?.click();
            });
            
            zone.addEventListener('dragover', (e) => {
                e.preventDefault();
                zone.classList.add('dragover');
            });
            
            zone.addEventListener('dragleave', () => {
                zone.classList.remove('dragover');
            });
            
            zone.addEventListener('drop', async (e) => {
                e.preventDefault();
                zone.classList.remove('dragover');
                
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    await handleFileUpload(files[0], type, zone);
                }
            });
            
            if (input) {
                input.addEventListener('change', async (e) => {
                    const files = e.target.files;
                    if (files.length > 0) {
                        await handleFileUpload(files[0], type, zone);
                    }
                });
            }
        });
        
        console.log('✅ Drop zones initialisées');
    }

    async function handleFileUpload(file, type, zone) {
        if (file.size > IMPORT_CONFIG.MAX_FILE_SIZE) {
            showError(`Fichier trop volumineux - Maximum: ${IMPORT_CONFIG.MAX_FILE_SIZE / 1024 / 1024}MB`);
            return;
        }
        
        try {
            showUploadProgress(zone, 0);
            showInfo(`Upload de ${file.name}...`);
            
            const uploadResult = await importAPI.uploadFile(file, type);
            console.log('✅ Fichier uploadé:', uploadResult);
            
            showUploadProgress(zone, 50);
            
            let processResult;
            
            if (file.name.endsWith('.pdf')) {
                showInfo('Extraction du texte (OCR)...');
                processResult = await importAPI.ocrPDF(uploadResult.file_id);
            } else if (file.name.endsWith('.csv')) {
                showInfo('Analyse du CSV...');
                processResult = await importAPI.parseCSV(uploadResult.file_id);
            }
            
            showUploadProgress(zone, 75);
            
            if (type === 'transactions') {
                await importTransactions(processResult.data);
            } else if (type === 'invoices') {
                await importInvoices(processResult.data);
            }
            
            showUploadProgress(zone, 100);
            
            showSuccess(`${file.name} importé - ${processResult.records_count || 0} enregistrement(s)`);
            
            setTimeout(() => {
                resetUploadZone(zone);
            }, 2000);
            
        } catch (error) {
            console.error('Erreur upload:', error);
            showError('Erreur d\'import: ' + error.message);
            resetUploadZone(zone);
        }
    }

    function showUploadProgress(zone, percent) {
        let progressBar = zone.querySelector('.upload-progress');
        
        if (!progressBar) {
            progressBar = document.createElement('div');
            progressBar.className = 'upload-progress';
            progressBar.innerHTML = `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
                <div class="progress-text">0%</div>
            `;
            zone.appendChild(progressBar);
        }
        
        const fill = progressBar.querySelector('.progress-fill');
        const text = progressBar.querySelector('.progress-text');
        
        fill.style.width = `${percent}%`;
        text.textContent = `${percent}%`;
    }

    function resetUploadZone(zone) {
        const progress = zone.querySelector('.upload-progress');
        if (progress) {
            progress.remove();
        }
        
        const input = zone.querySelector('input[type="file"]');
        if (input) {
            input.value = '';
        }
    }

    // =====================================================
    // IMPORT DE DONNÉES
    // =====================================================

    async function importTransactions(data) {
        if (!data || data.length === 0) {
            throw new Error('Aucune transaction trouvée');
        }
        
        console.log('💰 Import de transactions:', data.length);
        
        const result = await importAPI.importTransactions({
            transactions: data,
            auto_categorize: true
        });
        
        return result;
    }

    async function importInvoices(data) {
        if (!data || data.length === 0) {
            throw new Error('Aucune facture trouvée');
        }
        
        console.log('📄 Import de factures:', data.length);
        
        const result = await importAPI.importInvoices({
            invoices: data,
            auto_validate: true
        });
        
        return result;
    }

    // =====================================================
    // HISTORIQUE DES IMPORTS
    // =====================================================

    async function loadImportHistory() {
        try {
            const imports = await importAPI.listImports();
            console.log('✅ Historique chargé:', imports.length);
            displayImportHistory(imports);
            return imports;
        } catch (error) {
            console.error('Erreur chargement historique:', error);
            showError('Impossible de charger l\'historique');
        }
    }

    function displayImportHistory(imports) {
        const tbody = document.getElementById('importHistoryTable');
        if (!tbody) return;
        
        if (!imports || imports.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem;">Aucun import</td></tr>';
            return;
        }
        
        tbody.innerHTML = imports.map(imp => {
            const statusBadge = imp.status === 'success' 
                ? '<span class="badge badge-success">Réussi</span>'
                : '<span class="badge badge-danger">Erreur</span>';
                
            return `
                <tr>
                    <td>${formatDate(imp.date)}</td>
                    <td>${imp.filename}</td>
                    <td>${getImportTypeLabel(imp.type)}</td>
                    <td>${imp.records_count || 0}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <button class="btn btn-outline" style="padding: 0.25rem 0.75rem; font-size: 0.875rem;" 
                                onclick="viewImportDetails('${imp.id}')">
                            Voir
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async function viewImportDetails(importId) {
        showInfo('Détails d\'import - Fonctionnalité en développement');
    }

    function getImportTypeLabel(type) {
        const labels = {
            'transactions': 'Transactions bancaires',
            'invoices': 'Factures',
            'balance': 'Balance comptable',
            'documents': 'Documents',
            'fiscal': 'Documents fiscaux'
        };
        
        return labels[type] || type;
    }

    function formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // =====================================================
    // INITIALISATION
    // =====================================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeDropZones);
    } else {
        initializeDropZones();
    }

    // =====================================================
    // EXPORT GLOBAL
    // =====================================================

    window.importAPI = importAPI;
    window.handleFileUpload = handleFileUpload;
    window.loadImportHistory = loadImportHistory;
    window.viewImportDetails = viewImportDetails;
    window.initializeDropZones = initializeDropZones;

    console.log('✅ Module Imports chargé (avec OCR)');
})();
