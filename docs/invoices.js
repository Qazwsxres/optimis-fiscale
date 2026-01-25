/**
 * NUMMA - MODULE FACTURES
 * Gestion complète des factures avec backend
 * Backend: https://optimis-fiscale-production.up.railway.app
 */

// Simple message fallback if numma-messages doesn't exist
if (typeof showMessage === 'undefined') {
    window.showMessage = function(module, type, message) {
        console.log(`[${module}] ${type}: ${message}`);
    };
}
if (typeof showSuccess === 'undefined') {
    window.showSuccess = function(title, message) {
        console.log(`✅ ${title}: ${message || ''}`);
    };
}
if (typeof showError === 'undefined') {
    window.showError = function(title, message) {
        console.error(`❌ ${title}: ${message || ''}`);
        alert(`❌ ${title}\n\n${message || ''}`);
    };
}
if (typeof showInfo === 'undefined') {
    window.showInfo = function(title, message) {
        console.log(`ℹ️ ${title}: ${message || ''}`);
    };
}

/**
 * NUMMA - MODULE FACTURES
 * Gestion complète des factures avec backend
 * Backend: https://optimis-fiscale-production.up.railway.app
 */

// =====================================================
// CONFIGURATION
// =====================================================

const INVOICE_CONFIG = {
    API_BASE: 'https://optimis-fiscale-production.up.railway.app',
    ENDPOINTS: {
        LIST: '/api/invoices',
        CREATE: '/api/invoices',
        GET: '/api/invoices',
        UPDATE: '/api/invoices',
        DELETE: '/api/invoices',
        GENERATE_PDF: '/api/invoices/{id}/pdf',
        SEND_EMAIL: '/api/invoices/{id}/send'
    }
};

// =====================================================
// API CLIENT POUR FACTURES
// =====================================================

class InvoiceAPI {
    constructor() {
        this.baseURL = INVOICE_CONFIG.API_BASE;
    }
    
    getToken() {
        return localStorage.getItem('authToken') || 'demo-token';
    }
    
    getHeaders() {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.getToken()}`
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
        
        console.log(`📤 Invoice API: ${options.method || 'GET'} ${endpoint}`);
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || error.message || `HTTP ${response.status}`);
            }
            
            // Handle 204 No Content
            if (response.status === 204) {
                return null;
            }
            
            // Handle PDF/Binary responses
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/pdf')) {
                return await response.blob();
            }
            
            return await response.json();
        } catch (error) {
            console.error('❌ Invoice API Error:', error);
            throw error;
        }
    }
    
    // Liste toutes les factures
    async list(filters = {}) {
        const params = new URLSearchParams();
        
        if (filters.status) params.append('status', filters.status);
        if (filters.client) params.append('client', filters.client);
        if (filters.dateFrom) params.append('date_from', filters.dateFrom);
        if (filters.dateTo) params.append('date_to', filters.dateTo);
        
        const query = params.toString();
        const endpoint = query ? `${INVOICE_CONFIG.ENDPOINTS.LIST}?${query}` : INVOICE_CONFIG.ENDPOINTS.LIST;
        
        return await this.request(endpoint, { method: 'GET' });
    }
    
    // Récupère une facture
    async get(invoiceId) {
        return await this.request(`${INVOICE_CONFIG.ENDPOINTS.GET}/${invoiceId}`, {
            method: 'GET'
        });
    }
    
    // Crée une facture
    async create(invoiceData) {
        return await this.request(INVOICE_CONFIG.ENDPOINTS.CREATE, {
            method: 'POST',
            body: JSON.stringify(invoiceData)
        });
    }
    
    // Met à jour une facture
    async update(invoiceId, invoiceData) {
        return await this.request(`${INVOICE_CONFIG.ENDPOINTS.UPDATE}/${invoiceId}`, {
            method: 'PUT',
            body: JSON.stringify(invoiceData)
        });
    }
    
    // Supprime une facture
    async delete(invoiceId) {
        return await this.request(`${INVOICE_CONFIG.ENDPOINTS.DELETE}/${invoiceId}`, {
            method: 'DELETE'
        });
    }
    
    // Génère le PDF d'une facture
    async generatePDF(invoiceId) {
        const endpoint = INVOICE_CONFIG.ENDPOINTS.GENERATE_PDF.replace('{id}', invoiceId);
        return await this.request(endpoint, {
            method: 'POST'
        });
    }
    
    // Envoie la facture par email
    async sendByEmail(invoiceId, emailData) {
        const endpoint = INVOICE_CONFIG.ENDPOINTS.SEND_EMAIL.replace('{id}', invoiceId);
        return await this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(emailData)
        });
    }
}

// Instance globale
const invoiceAPI = new InvoiceAPI();

// =====================================================
// FONCTIONS DE GESTION DES FACTURES
// =====================================================

/**
 * Charge toutes les factures
 */
async function loadInvoices(filters = {}) {
    try {
        showMessage('generic', 'loading', 'Chargement des factures...');
        
        const invoices = await invoiceAPI.list(filters);
        
        console.log('✅ Factures chargées:', invoices);
        
        // Afficher dans le tableau
        displayInvoices(invoices);
        
        showSuccess('Factures chargées', `${invoices.length} facture(s) trouvée(s)`);
        
        return invoices;
    } catch (error) {
        console.error('Erreur chargement factures:', error);
        showError('Erreur', 'Impossible de charger les factures: ' + error.message);
        return [];
    }
}

/**
 * Affiche les factures dans le tableau
 */
function displayInvoices(invoices) {
    const tbody = document.getElementById('invoicesTableBody');
    if (!tbody) {
        console.warn('Table des factures non trouvée');
        return;
    }
    
    if (!invoices || invoices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-gray);">Aucune facture trouvée</td></tr>';
        return;
    }
    
    tbody.innerHTML = invoices.map(invoice => {
        const statusBadge = getInvoiceStatusBadge(invoice.status);
        const totalHT = parseFloat(invoice.total_ht || 0).toFixed(2);
        const totalTTC = parseFloat(invoice.total_ttc || 0).toFixed(2);
        
        return `
            <tr>
                <td><strong>${invoice.number || 'N/A'}</strong></td>
                <td>${invoice.client_name || 'Client'}</td>
                <td>${formatDate(invoice.invoice_date)}</td>
                <td>${formatDate(invoice.due_date)}</td>
                <td>€ ${totalHT}</td>
                <td>€ ${totalTTC}</td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-outline" style="padding: 0.25rem 0.75rem; font-size: 0.875rem;" onclick="viewInvoice('${invoice.id}')">
                        Voir
                    </button>
                    <button class="btn btn-primary" style="padding: 0.25rem 0.75rem; font-size: 0.875rem; margin-left: 0.5rem;" onclick="downloadInvoicePDF('${invoice.id}')">
                        PDF
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Retourne le badge de statut
 */
function getInvoiceStatusBadge(status) {
    const badges = {
        'draft': '<span class="badge">Brouillon</span>',
        'sent': '<span class="badge badge-warning">Envoyée</span>',
        'paid': '<span class="badge badge-success">Payée</span>',
        'overdue': '<span class="badge badge-danger">En retard</span>',
        'cancelled': '<span class="badge">Annulée</span>'
    };
    
    return badges[status] || '<span class="badge">Inconnu</span>';
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
        year: 'numeric'
    });
}

/**
 * Crée une nouvelle facture
 */
async function createInvoice(event) {
    event.preventDefault();
    
    try {
        // Récupérer les données du formulaire
        const formData = getInvoiceFormData();
        
        console.log('📝 Création facture:', formData);
        
        showMessage('invoices', 'processing', 'Création de la facture...');
        
        // Créer la facture
        const invoice = await invoiceAPI.create(formData);
        
        console.log('✅ Facture créée:', invoice);
        
        showMessage('invoices', 'created', 
            `Facture ${invoice.number} créée pour ${formData.client.name}`,
            `Montant TTC: € ${formData.totalTTC}`
        );
        
        // Fermer le modal
        hideCreateInvoiceModal();
        
        // Recharger la liste
        loadInvoices();
        
        // Proposer de générer le PDF
        if (confirm('Facture créée avec succès!\n\nVoulez-vous générer le PDF maintenant?')) {
            await downloadInvoicePDF(invoice.id);
        }
        
        return invoice;
    } catch (error) {
        console.error('Erreur création facture:', error);
        showError('Erreur de création', error.message);
    }
}

/**
 * Récupère les données du formulaire de facture
 */
function getInvoiceFormData() {
    // Infos entreprise (depuis localStorage ou form)
    const userData = JSON.parse(localStorage.getItem('currentUser') || '{}');
    const companyInfo = {
        name: document.getElementById('companyName')?.value || userData.company_name || 'Entreprise',
        address: document.getElementById('companyAddress')?.value || 'Adresse',
        siret: document.getElementById('companySIRET')?.value || '000000000',
        email: document.getElementById('companyEmail')?.value || 'contact@entreprise.fr',
        phone: document.getElementById('companyPhone')?.value || '01 00 00 00 00',
        iban: document.getElementById('companyIBAN')?.value || 'FR76'
    };
    
    // Infos facture
    const invoiceData = {
        number: document.getElementById('invoiceNumber').value,
        invoice_date: document.getElementById('invoiceDate').value,
        due_date: document.getElementById('invoiceDueDate').value,
        
        // Client
        client: {
            name: document.getElementById('clientName').value,
            address: document.getElementById('clientAddress').value,
            email: document.getElementById('clientEmail').value,
            phone: document.getElementById('clientPhone').value
        },
        
        // Lignes de facture
        lines: [],
        
        // Totaux
        total_ht: parseFloat(document.getElementById('totalHT').textContent.replace(/[^0-9.]/g, '')),
        total_tva: parseFloat(document.getElementById('totalTVA').textContent.replace(/[^0-9.]/g, '')),
        total_ttc: parseFloat(document.getElementById('totalTTC').textContent.replace(/[^0-9.]/g, '')),
        
        // Taux TVA
        tva_rate: parseFloat(document.getElementById('tvaRate').value),
        
        // Conditions
        payment_terms: document.getElementById('paymentTerms').value,
        
        // Infos entreprise
        company: companyInfo,
        
        // Statut
        status: 'draft'
    };
    
    // Récupérer toutes les lignes
    document.querySelectorAll('.invoice-line').forEach(line => {
        const description = line.querySelectorAll('input')[0].value;
        const price = parseFloat(line.querySelector('.line-price').value) || 0;
        const quantity = parseFloat(line.querySelector('.line-quantity').value) || 0;
        const unit = line.querySelector('select').value;
        
        if (description && price > 0 && quantity > 0) {
            invoiceData.lines.push({
                description: description,
                unit_price: price,
                quantity: quantity,
                unit: unit,
                total: price * quantity
            });
        }
    });
    
    return invoiceData;
}

/**
 * Voir une facture
 */
async function viewInvoice(invoiceId) {
    try {
        showMessage('generic', 'loading', 'Chargement de la facture...');
        
        const invoice = await invoiceAPI.get(invoiceId);
        
        console.log('📄 Facture:', invoice);
        
        // Afficher dans une modal ou rediriger
        showInvoiceDetails(invoice);
        
    } catch (error) {
        console.error('Erreur chargement facture:', error);
        showError('Erreur', 'Impossible de charger la facture: ' + error.message);
    }
}

/**
 * Affiche les détails d'une facture
 */
function showInvoiceDetails(invoice) {
    // Pour l'instant, juste afficher dans une alert
    // TODO: Créer une belle modal de détails
    const details = `
Facture: ${invoice.number}
Client: ${invoice.client_name}
Date: ${formatDate(invoice.invoice_date)}
Échéance: ${formatDate(invoice.due_date)}

Montant HT: € ${invoice.total_ht}
TVA: € ${invoice.total_tva}
Montant TTC: € ${invoice.total_ttc}

Statut: ${invoice.status}
    `.trim();
    
    showInfo('Détails de la facture', details);
}

/**
 * Télécharge le PDF d'une facture
 */
async function downloadInvoicePDF(invoiceId) {
    try {
        showMessage('invoices', 'processing', 'Génération du PDF...');
        
        const pdfBlob = await invoiceAPI.generatePDF(invoiceId);
        
        // Créer un lien de téléchargement
        const url = window.URL.createObjectURL(pdfBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `facture_${invoiceId}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        showSuccess('PDF généré', 'Le PDF a été téléchargé');
        
    } catch (error) {
        console.error('Erreur génération PDF:', error);
        showError('Erreur PDF', 'Impossible de générer le PDF: ' + error.message);
    }
}

/**
 * Filtre les factures
 */
async function filterInvoices() {
    const statusSelect = document.getElementById('filterStatus');
    const searchInput = document.getElementById('searchInvoice');
    
    const status = statusSelect?.value;
    const searchTerm = searchInput?.value?.toLowerCase();
    
    console.log('🔍 Filtering invoices:', { status, searchTerm });
    
    // If no filters, just reload all
    if ((!status || status === 'all') && !searchTerm) {
        await loadInvoices();
        return;
    }
    
    // Build filters for API
    const filters = {};
    if (status && status !== 'all') filters.status = status;
    if (searchTerm) filters.client = searchTerm;
    
    await loadInvoices(filters);
}

/**
 * Setup invoice filters on page load
 */
function setupInvoiceFilters() {
    const statusSelect = document.getElementById('filterStatus');
    const searchInput = document.getElementById('searchInvoice');
    
    if (statusSelect) {
        statusSelect.addEventListener('change', () => {
            console.log('📊 Status filter changed:', statusSelect.value);
            filterInvoices();
        });
    }
    
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            console.log('🔍 Search term changed:', searchInput.value);
            // Debounce search
            clearTimeout(window.invoiceSearchTimeout);
            window.invoiceSearchTimeout = setTimeout(() => {
                filterInvoices();
            }, 500);
        });
    }
    
    console.log('✅ Invoice filters setup complete');
}

/**
 * Ouvre le modal de création
 */
function showCreateInvoiceModal() {
    const modal = document.getElementById('createInvoiceModal');
    if (modal) {
        modal.classList.add('active');
        
        // Définir la date du jour
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('invoiceDate').value = today;
        
        // Définir la date d'échéance (30 jours)
        const dueDate = new Date();
        dueDate.setDate(dueDate.getDate() + 30);
        document.getElementById('invoiceDueDate').value = dueDate.toISOString().split('T')[0];
        
        // Générer le numéro de facture
        generateInvoiceNumber();
    }
}

/**
 * Ferme le modal de création
 */
function hideCreateInvoiceModal() {
    const modal = document.getElementById('createInvoiceModal');
    if (modal) {
        modal.classList.remove('active');
        document.getElementById('createInvoiceForm')?.reset();
    }
}

/**
 * Génère un numéro de facture
 */
function generateInvoiceNumber() {
    const lastNumber = parseInt(localStorage.getItem('lastInvoiceNumber') || '0');
    const newNumber = lastNumber + 1;
    const year = new Date().getFullYear();
    const invoiceNumber = `F-${year}-${String(newNumber).padStart(3, '0')}`;
    
    const input = document.getElementById('invoiceNumber');
    if (input) {
        input.value = invoiceNumber;
    }
    
    return invoiceNumber;
}

// =====================================================
// INITIALISATION
// =====================================================

console.log('✅ Module Factures chargé');

// Charger les factures au chargement de la page
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Attacher l'événement au formulaire
        const form = document.getElementById('createInvoiceForm');
        if (form) {
            form.addEventListener('submit', createInvoice);
        }
        
        // Setup filters
        setupInvoiceFilters();
    });
} else {
    const form = document.getElementById('createInvoiceForm');
    if (form) {
        form.addEventListener('submit', createInvoice);
    }
    
    // Setup filters
    setupInvoiceFilters();
}

// Exposer les fonctions globalement
window.invoiceAPI = invoiceAPI;
window.loadInvoices = loadInvoices;
window.createInvoice = createInvoice;
window.viewInvoice = viewInvoice;
window.downloadInvoicePDF = downloadInvoicePDF;
window.filterInvoices = filterInvoices;
window.setupInvoiceFilters = setupInvoiceFilters;
window.showCreateInvoiceModal = showCreateInvoiceModal;
window.hideCreateInvoiceModal = hideCreateInvoiceModal;
