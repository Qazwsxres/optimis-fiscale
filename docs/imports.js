/**
 * NUMMA - MODULE IMPORTS
 * Import de fichiers avec OCR pour PDFs
 * Backend: https://optimis-fiscale-production.up.railway.app
 */

// =====================================================
// CONFIGURATION
// =====================================================

const IMPORT_CONFIG = {
    API_BASE: 'https://optimis-fiscale-production.up.railway.app',
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
        
        console.log(`📁 Import API: ${options.method || 'GET'} ${endpoint}`);
        
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
    
    /**
     * Upload un fichier
     */
    async uploadFile(file, type) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', type);
        
        return await this.request(IMPORT_CONFIG.ENDPOINTS.UPLOAD, {
            method: 'POST',
            body: formData,
            headers: this.getHeaders(false) // Pas de Content-Type pour FormData
        });
    }
    
    /**
     * Parse un fichier CSV
     */
    async parseCSV(fileId) {
        return await this.request(`${IMPORT_CONFIG.ENDPOINTS.PARSE_CSV}/${fileId}`, {
            method: 'POST'
        });
    }
    
    /**
     * OCR sur un PDF
     */
    async ocrPDF(fileId) {
        return await this.request(`${IMPORT_CONFIG.ENDPOINTS.OCR_PDF}/${fileId}`, {
            method: 'POST'
        });
    }
    
    /**
     * Importe des transactions bancaires
     */
    async importTransactions(data) {
        return await this.request(IMPORT_CONFIG.ENDPOINTS.IMPORT_TRANSACTIONS, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    /**
     * Importe des factures
     */
    async importInvoices(data) {
        return await this.request(IMPORT_CONFIG.ENDPOINTS.IMPORT_INVOICES, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    /**
     * Liste l'historique des imports
     */
    async listImports() {
        return await this.request(IMPORT_CONFIG.ENDPOINTS.LIST_IMPORTS);
    }
}

const importAPI = new ImportAPI();

// =====================================================
// GESTION DES UPLOADS
// =====================================================

/**
 * Initialise les zones de drop
 */
function initializeDropZones() {
    const dropZones = document.querySelectorAll('.upload-zone');
    
    dropZones.forEach(zone => {
        const input = zone.querySelector('input[type="file"]');
        const type = zone.dataset.type;
        
        // Click sur la zone
        zone.addEventListener('click', () => {
            input?.click();
        });
        
        // Drag & Drop
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
        
        // File input change
        if (input) {
            input.addEventListener('change', async (e) => {
                const files = e.target.files;
                if (files.length > 0) {
                    await handleFileUpload(files[0], type, zone);
                }
            });
        }
    });
}

/**
 * Gère l'upload d'un fichier
 */
async function handleFileUpload(file, type, zone) {
    // Vérifier la taille
    if (file.size > IMPORT_CONFIG.MAX_FILE_SIZE) {
        showError('Fichier trop volumineux', `Maximum: ${IMPORT_CONFIG.MAX_FILE_SIZE / 1024 / 1024}MB`);
        return;
    }
    
    try {
        // Afficher le chargement
        showUploadProgress(zone, 0);
        
        showMessage('imports', 'uploading', `Upload de ${file.name}...`);
        
        // Upload
        const uploadResult = await importAPI.uploadFile(file, type);
        
        console.log('✅ Fichier uploadé:', uploadResult);
        
        showUploadProgress(zone, 50);
        
        // Traiter selon le type de fichier
        let processResult;
        
        if (file.name.endsWith('.pdf')) {
            // OCR pour les PDFs
            showMessage('imports', 'processing', 'Extraction du texte (OCR)...');
            processResult = await importAPI.ocrPDF(uploadResult.file_id);
        } else if (file.name.endsWith('.csv')) {
            // Parse CSV
            showMessage('imports', 'processing', 'Analyse du CSV...');
            processResult = await importAPI.parseCSV(uploadResult.file_id);
        }
        
        showUploadProgress(zone, 75);
        
        // Importer les données selon le type
        if (type === 'transactions') {
            await importTransactions(processResult.data);
        } else if (type === 'invoices') {
            await importInvoices(processResult.data);
        }
        
        showUploadProgress(zone, 100);
        
        showMessage('imports', 'completed',
            `${file.name} importé avec succès`,
            `${processResult.records_count || 0} enregistrement(s)`
        );
        
        // Réinitialiser la zone
        setTimeout(() => {
            resetUploadZone(zone);
        }, 2000);
        
    } catch (error) {
        console.error('Erreur upload:', error);
        showError('Erreur d\'import', error.message);
        resetUploadZone(zone);
    }
}

/**
 * Affiche la progression de l'upload
 */
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

/**
 * Réinitialise une zone d'upload
 */
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

/**
 * Importe des transactions bancaires
 */
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

/**
 * Importe des factures
 */
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

/**
 * Charge l'historique des imports
 */
async function loadImportHistory() {
    try {
        const imports = await importAPI.listImports();
        
        console.log('✅ Historique chargé:', imports);
        
        displayImportHistory(imports);
        
        return imports;
    } catch (error) {
        console.error('Erreur chargement historique:', error);
        showError('Erreur', 'Impossible de charger l\'historique');
    }
}

/**
 * Affiche l'historique
 */
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

/**
 * Voir les détails d'un import
 */
async function viewImportDetails(importId) {
    showInfo('Détails d\'import', 'Fonctionnalité en cours de développement');
}

/**
 * Label du type d'import
 */
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

/**
 * Formate une date
 */
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
// PARSERS LOCAUX (fallback)
// =====================================================

/**
 * Parse un CSV en local si backend indisponible
 */
function parseCSVLocal(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            try {
                const text = e.target.result;
                const lines = text.split('\n');
                const headers = lines[0].split(',');
                
                const data = lines.slice(1)
                    .filter(line => line.trim())
                    .map(line => {
                        const values = line.split(',');
                        const obj = {};
                        headers.forEach((header, i) => {
                            obj[header.trim()] = values[i]?.trim();
                        });
                        return obj;
                    });
                
                resolve(data);
            } catch (error) {
                reject(error);
            }
        };
        
        reader.onerror = reject;
        reader.readAsText(file);
    });
}

// =====================================================
// INITIALISATION
// =====================================================

console.log('✅ Module Imports chargé (avec OCR)');

// Initialiser au chargement de la page
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeDropZones);
} else {
    initializeDropZones();
}

// Export global
window.importAPI = importAPI;
window.handleFileUpload = handleFileUpload;
window.loadImportHistory = loadImportHistory;
window.viewImportDetails = viewImportDetails;
