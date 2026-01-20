/**
 * NUMMA - MODULE EXPORTS
 * Export CSV, PDF, Excel (génération backend)
 * Backend: https://optimis-fiscale-production.up.railway.app
 */

// =====================================================
// CONFIGURATION
// =====================================================

const EXPORT_CONFIG = {
    API_BASE: 'https://optimis-fiscale-production.up.railway.app',
    ENDPOINTS: {
        EXPORT_TRANSACTIONS_CSV: '/api/exports/transactions/csv',
        EXPORT_TRANSACTIONS_PDF: '/api/exports/transactions/pdf',
        EXPORT_TRANSACTIONS_EXCEL: '/api/exports/transactions/excel',
        EXPORT_INVOICES_CSV: '/api/exports/invoices/csv',
        EXPORT_INVOICES_PDF: '/api/exports/invoices/pdf',
        EXPORT_INVOICES_EXCEL: '/api/exports/invoices/excel',
        EXPORT_EMPLOYEES_CSV: '/api/exports/employees/csv',
        EXPORT_PAYSLIPS_PDF: '/api/exports/payslips/pdf',
        EXPORT_REPORT_PDF: '/api/exports/reports/fiscal/pdf'
    }
};

// =====================================================
// API CLIENT
// =====================================================

class ExportAPI {
    constructor() {
        this.baseURL = EXPORT_CONFIG.API_BASE;
    }
    
    getHeaders() {
        const token = localStorage.getItem('authToken') || 'demo-token';
        return {
            'Authorization': `Bearer ${token}`
        };
    }
    
    async downloadFile(endpoint, filename, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        console.log(`📥 Export: ${endpoint}`);
        
        try {
            const response = await fetch(url, {
                method: options.method || 'GET',
                headers: {
                    ...this.getHeaders(),
                    ...options.headers
                },
                body: options.body
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            // Télécharger le fichier
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(downloadUrl);
            
            return true;
        } catch (error) {
            console.error('❌ Export Error:', error);
            throw error;
        }
    }
    
    // TRANSACTIONS
    async exportTransactionsCSV(filters = {}) {
        const params = new URLSearchParams(filters);
        const endpoint = `${EXPORT_CONFIG.ENDPOINTS.EXPORT_TRANSACTIONS_CSV}?${params}`;
        return await this.downloadFile(endpoint, 'transactions.csv');
    }
    
    async exportTransactionsPDF(filters = {}) {
        const params = new URLSearchParams(filters);
        const endpoint = `${EXPORT_CONFIG.ENDPOINTS.EXPORT_TRANSACTIONS_PDF}?${params}`;
        return await this.downloadFile(endpoint, 'transactions.pdf');
    }
    
    async exportTransactionsExcel(filters = {}) {
        const params = new URLSearchParams(filters);
        const endpoint = `${EXPORT_CONFIG.ENDPOINTS.EXPORT_TRANSACTIONS_EXCEL}?${params}`;
        return await this.downloadFile(endpoint, 'transactions.xlsx');
    }
    
    // FACTURES
    async exportInvoicesCSV(filters = {}) {
        const params = new URLSearchParams(filters);
        const endpoint = `${EXPORT_CONFIG.ENDPOINTS.EXPORT_INVOICES_CSV}?${params}`;
        return await this.downloadFile(endpoint, 'factures.csv');
    }
    
    async exportInvoicesPDF(filters = {}) {
        const params = new URLSearchParams(filters);
        const endpoint = `${EXPORT_CONFIG.ENDPOINTS.EXPORT_INVOICES_PDF}?${params}`;
        return await this.downloadFile(endpoint, 'factures.pdf');
    }
    
    async exportInvoicesExcel(filters = {}) {
        const params = new URLSearchParams(filters);
        const endpoint = `${EXPORT_CONFIG.ENDPOINTS.EXPORT_INVOICES_EXCEL}?${params}`;
        return await this.downloadFile(endpoint, 'factures.xlsx');
    }
    
    // EMPLOYÉS
    async exportEmployeesCSV() {
        return await this.downloadFile(EXPORT_CONFIG.ENDPOINTS.EXPORT_EMPLOYEES_CSV, 'employes.csv');
    }
    
    // FICHES DE PAIE
    async exportPayslipsPDF(month, year) {
        const endpoint = `${EXPORT_CONFIG.ENDPOINTS.EXPORT_PAYSLIPS_PDF}?month=${month}&year=${year}`;
        return await this.downloadFile(endpoint, `fiches_paie_${month}_${year}.pdf');
    }
    
    // RAPPORTS
    async exportFiscalReportPDF(year) {
        const endpoint = `${EXPORT_CONFIG.ENDPOINTS.EXPORT_REPORT_PDF}?year=${year}`;
        return await this.downloadFile(endpoint, `rapport_fiscal_${year}.pdf`);
    }
}

const exportAPI = new ExportAPI();

// =====================================================
// FONCTIONS D'EXPORT
// =====================================================

/**
 * Export CSV - Transactions
 */
async function exportTransactionsCSV() {
    try {
        showMessage('exports', 'processing', 'Génération du CSV...');
        
        await exportAPI.exportTransactionsCSV({
            date_from: getFilterDate('from'),
            date_to: getFilterDate('to')
        });
        
        showSuccess('Export CSV', 'Transactions exportées en CSV');
        
    } catch (error) {
        console.error('Erreur export CSV:', error);
        showError('Erreur d\'export', error.message);
    }
}

/**
 * Export PDF - Transactions
 */
async function exportTransactionsPDF() {
    try {
        showMessage('exports', 'processing', 'Génération du PDF...');
        
        await exportAPI.exportTransactionsPDF({
            date_from: getFilterDate('from'),
            date_to: getFilterDate('to')
        });
        
        showSuccess('Export PDF', 'Transactions exportées en PDF');
        
    } catch (error) {
        console.error('Erreur export PDF:', error);
        showError('Erreur d\'export', error.message);
    }
}

/**
 * Export Excel - Transactions
 */
async function exportTransactionsExcel() {
    try {
        showMessage('exports', 'processing', 'Génération du fichier Excel...');
        
        await exportAPI.exportTransactionsExcel({
            date_from: getFilterDate('from'),
            date_to: getFilterDate('to')
        });
        
        showSuccess('Export Excel', 'Transactions exportées en Excel');
        
    } catch (error) {
        console.error('Erreur export Excel:', error);
        showError('Erreur d\'export', error.message);
    }
}

/**
 * Export CSV - Factures
 */
async function exportInvoicesCSV() {
    try {
        showMessage('exports', 'processing', 'Génération du CSV...');
        
        await exportAPI.exportInvoicesCSV();
        
        showSuccess('Export CSV', 'Factures exportées en CSV');
        
    } catch (error) {
        console.error('Erreur export CSV:', error);
        showError('Erreur d\'export', error.message);
    }
}

/**
 * Export PDF - Factures
 */
async function exportInvoicesPDF() {
    try {
        showMessage('exports', 'processing', 'Génération du PDF...');
        
        await exportAPI.exportInvoicesPDF();
        
        showSuccess('Export PDF', 'Factures exportées en PDF');
        
    } catch (error) {
        console.error('Erreur export PDF:', error);
        showError('Erreur d\'export', error.message);
    }
}

/**
 * Export Excel - Factures
 */
async function exportInvoicesExcel() {
    try {
        showMessage('exports', 'processing', 'Génération du fichier Excel...');
        
        await exportAPI.exportInvoicesExcel();
        
        showSuccess('Export Excel', 'Factures exportées en Excel');
        
    } catch (error) {
        console.error('Erreur export Excel:', error);
        showError('Erreur d\'export', error.message);
    }
}

/**
 * Export CSV - Employés
 */
async function exportEmployeesCSV() {
    try {
        showMessage('exports', 'processing', 'Génération du CSV...');
        
        await exportAPI.exportEmployeesCSV();
        
        showSuccess('Export CSV', 'Employés exportés en CSV');
        
    } catch (error) {
        console.error('Erreur export CSV:', error);
        showError('Erreur d\'export', error.message);
    }
}

/**
 * Export PDF - Rapport fiscal
 */
async function generateCompleteReport() {
    const year = prompt('Année du rapport:', new Date().getFullYear());
    if (!year) return;
    
    try {
        showMessage('reports', 'generating', 'Génération du rapport fiscal complet...');
        
        await exportAPI.exportFiscalReportPDF(year);
        
        showSuccess('Rapport généré', `Rapport fiscal ${year} téléchargé`);
        
    } catch (error) {
        console.error('Erreur génération rapport:', error);
        showError('Erreur de génération', error.message);
    }
}

// =====================================================
// EXPORTS LOCAUX (FALLBACK)
// =====================================================

/**
 * Génère un CSV en local (si backend indisponible)
 */
function generateCSVLocal(data, filename) {
    if (!data || data.length === 0) {
        showWarning('Aucune donnée', 'Aucune donnée à exporter');
        return;
    }
    
    // Récupérer les headers
    const headers = Object.keys(data[0]);
    
    // Créer le CSV
    let csv = headers.join(',') + '\n';
    
    data.forEach(row => {
        const values = headers.map(header => {
            const value = row[header] || '';
            // Échapper les virgules et guillemets
            return `"${String(value).replace(/"/g, '""')}"`;
        });
        csv += values.join(',') + '\n';
    });
    
    // Télécharger
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showSuccess('Export CSV', `${filename} téléchargé`);
}

/**
 * Génère un Excel simple en local (format CSV)
 */
function generateExcelLocal(data, filename) {
    // Pour un vrai Excel, il faudrait une lib comme XLSX.js
    // Pour l'instant, on utilise CSV
    generateCSVLocal(data, filename.replace('.xlsx', '.csv'));
}

// =====================================================
// UTILITAIRES
// =====================================================

/**
 * Récupère une date de filtre
 */
function getFilterDate(type) {
    const input = document.getElementById(`filter${type.charAt(0).toUpperCase() + type.slice(1)}Date`);
    return input ? input.value : null;
}

/**
 * Récupère les transactions depuis localStorage (fallback)
 */
function getTransactionsLocal() {
    return JSON.parse(localStorage.getItem('numma_transactions') || '[]');
}

/**
 * Récupère les factures depuis localStorage (fallback)
 */
function getInvoicesLocal() {
    return JSON.parse(localStorage.getItem('numma_invoices') || '[]');
}

// =====================================================
// MENU CONTEXTUEL D'EXPORT
// =====================================================

/**
 * Affiche le menu d'export
 */
function showExportMenu(dataType) {
    const menu = `
        <div class="export-menu">
            <h3>Exporter ${dataType}</h3>
            <button onclick="export${dataType}CSV()" class="btn btn-outline">
                📊 CSV
            </button>
            <button onclick="export${dataType}PDF()" class="btn btn-outline">
                📄 PDF
            </button>
            <button onclick="export${dataType}Excel()" class="btn btn-outline">
                📗 Excel
            </button>
        </div>
    `;
    
    // TODO: Afficher dans une modal
    console.log('Export menu:', dataType);
}

// =====================================================
// EXPORT GLOBAL
// =====================================================

window.exportAPI = exportAPI;
window.exportTransactionsCSV = exportTransactionsCSV;
window.exportTransactionsPDF = exportTransactionsPDF;
window.exportTransactionsExcel = exportTransactionsExcel;
window.exportInvoicesCSV = exportInvoicesCSV;
window.exportInvoicesPDF = exportInvoicesPDF;
window.exportInvoicesExcel = exportInvoicesExcel;
window.exportEmployeesCSV = exportEmployeesCSV;
window.generateCompleteReport = generateCompleteReport;
window.generateCSVLocal = generateCSVLocal;
window.showExportMenu = showExportMenu;

console.log('✅ Module Exports chargé (CSV, PDF, Excel)');
