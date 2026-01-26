/**
 * ========================================
 * NUMMA - MODULE FACTURES v3.0
 * ========================================
 * Gestion complète des factures avec backend
 * Backend: https://optimis-fiscale-production.up.railway.app
 * 
 * DÉPENDANCES: numma-messages.js (REQUIS)
 */

(function() {
    'use strict';
    
    console.log('📄 Chargement module Factures...');
    
    // Vérifier que numma-messages.js est chargé
    if (typeof showMessage === 'undefined') {
        console.error('❌ ERREUR: numma-messages.js doit être chargé AVANT numma-invoices.js');
        alert('Erreur de chargement: Système de messages manquant');
        return;
    }

    // =====================================================
    // CONFIGURATION
    // =====================================================

    const INVOICE_CONFIG = {
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
            this.baseURL = window.NUMMA_CONFIG?.API_BASE || 'https://optimis-fiscale-production.up.railway.app';
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
                
                if (response.status === 204) return null;
                
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
        
        async get(invoiceId) {
            return await this.request(`${INVOICE_CONFIG.ENDPOINTS.GET}/${invoiceId}`, { method: 'GET' });
        }
        
        async create(invoiceData) {
            return await this.request(INVOICE_CONFIG.ENDPOINTS.CREATE, {
                method: 'POST',
                body: JSON.stringify(invoiceData)
            });
        }
        
        async update(invoiceId, invoiceData) {
            return await this.request(`${INVOICE_CONFIG.ENDPOINTS.UPDATE}/${invoiceId}`, {
                method: 'PUT',
                body: JSON.stringify(invoiceData)
            });
        }
        
        async delete(invoiceId) {
            return await this.request(`${INVOICE_CONFIG.ENDPOINTS.DELETE}/${invoiceId}`, { method: 'DELETE' });
        }
        
        async generatePDF(invoiceId) {
            const endpoint = INVOICE_CONFIG.ENDPOINTS.GENERATE_PDF.replace('{id}', invoiceId);
            return await this.request(endpoint, { method: 'POST' });
        }
        
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

    async function loadInvoices(filters = {}) {
        try {
            showInfo('Chargement des factures...');
            
            const invoices = await invoiceAPI.list(filters);
            console.log('✅ Factures chargées:', invoices.length);
            
            displayInvoices(invoices);
            showSuccess(`${invoices.length} facture(s) chargée(s)`);
            
            return invoices;
        } catch (error) {
            console.error('Erreur chargement factures:', error);
            showError('Impossible de charger les factures: ' + error.message);
            return [];
        }
    }

    function displayInvoices(invoices) {
        const tbody = document.getElementById('invoicesTableBody');
        if (!tbody) {
            console.warn('⚠️ Table des factures non trouvée');
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

    function formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: 'short',
            year: 'numeric'
        });
    }

    async function createInvoice(event) {
        if (event) event.preventDefault();
        
        try {
            const formData = getInvoiceFormData();
            console.log('📝 Création facture:', formData);
            
            showInfo('Création de la facture...');
            
            const invoice = await invoiceAPI.create(formData);
            console.log('✅ Facture créée:', invoice);
            
            showSuccess(`Facture ${invoice.number} créée pour ${formData.client.name}`);
            
            if (typeof hideCreateInvoiceModal === 'function') {
                hideCreateInvoiceModal();
            }
            
            loadInvoices();
            
            if (confirm('Facture créée avec succès!\n\nVoulez-vous générer le PDF maintenant?')) {
                await downloadInvoicePDF(invoice.id);
            }
            
            return invoice;
        } catch (error) {
            console.error('Erreur création facture:', error);
            showError('Erreur de création: ' + error.message);
        }
    }

    function getInvoiceFormData() {
        const userData = JSON.parse(localStorage.getItem('currentUser') || '{}');
        
        return {
            number: document.getElementById('invoiceNumber')?.value || '',
            invoice_date: document.getElementById('invoiceDate')?.value || '',
            due_date: document.getElementById('invoiceDueDate')?.value || '',
            client: {
                name: document.getElementById('clientName')?.value || '',
                address: document.getElementById('clientAddress')?.value || '',
                email: document.getElementById('clientEmail')?.value || '',
                phone: document.getElementById('clientPhone')?.value || ''
            },
            lines: getInvoiceLines(),
            total_ht: parseFloat(document.getElementById('totalHT')?.textContent.replace(/[^0-9.]/g, '') || 0),
            total_tva: parseFloat(document.getElementById('totalTVA')?.textContent.replace(/[^0-9.]/g, '') || 0),
            total_ttc: parseFloat(document.getElementById('totalTTC')?.textContent.replace(/[^0-9.]/g, '') || 0),
            tva_rate: parseFloat(document.getElementById('tvaRate')?.value || 20),
            payment_terms: document.getElementById('paymentTerms')?.value || '',
            company: {
                name: userData.company_name || 'Entreprise',
                siret: userData.siret || '',
                email: userData.email || ''
            },
            status: 'draft'
        };
    }

    function getInvoiceLines() {
        const lines = [];
        document.querySelectorAll('.invoice-line').forEach(line => {
            const description = line.querySelectorAll('input')[0]?.value;
            const price = parseFloat(line.querySelector('.line-price')?.value || 0);
            const quantity = parseFloat(line.querySelector('.line-quantity')?.value || 0);
            const unit = line.querySelector('select')?.value || 'unité';
            
            if (description && price > 0 && quantity > 0) {
                lines.push({
                    description,
                    unit_price: price,
                    quantity,
                    unit,
                    total: price * quantity
                });
            }
        });
        return lines;
    }

    async function viewInvoice(invoiceId) {
        try {
            showInfo('Chargement de la facture...');
            const invoice = await invoiceAPI.get(invoiceId);
            console.log('📄 Facture:', invoice);
            
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
            
            showInfo(details);
        } catch (error) {
            console.error('Erreur:', error);
            showError('Impossible de charger la facture: ' + error.message);
        }
    }

    async function downloadInvoicePDF(invoiceId) {
        try {
            showInfo('Génération du PDF...');
            
            const pdfBlob = await invoiceAPI.generatePDF(invoiceId);
            
            const url = window.URL.createObjectURL(pdfBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `facture_${invoiceId}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            showSuccess('PDF téléchargé');
        } catch (error) {
            console.error('Erreur génération PDF:', error);
            showError('Impossible de générer le PDF: ' + error.message);
        }
    }

    async function filterInvoices() {
        const status = document.getElementById('filterStatus')?.value;
        const searchTerm = document.getElementById('searchInvoice')?.value?.toLowerCase();
        
        console.log('🔍 Filtrage factures:', { status, searchTerm });
        
        if ((!status || status === 'all') && !searchTerm) {
            await loadInvoices();
            return;
        }
        
        const filters = {};
        if (status && status !== 'all') filters.status = status;
        if (searchTerm) filters.client = searchTerm;
        
        await loadInvoices(filters);
    }

    function setupInvoiceFilters() {
        const statusSelect = document.getElementById('filterStatus');
        const searchInput = document.getElementById('searchInvoice');
        
        if (statusSelect) {
            statusSelect.addEventListener('change', filterInvoices);
        }
        
        if (searchInput) {
            let timeout;
            searchInput.addEventListener('input', () => {
                clearTimeout(timeout);
                timeout = setTimeout(filterInvoices, 500);
            });
        }
        
        console.log('✅ Invoice filters setup');
    }

    function setupEventListeners() {
        const form = document.getElementById('createInvoiceForm');
        if (form) {
            form.addEventListener('submit', createInvoice);
        }
        
        setupInvoiceFilters();
    }

    // =====================================================
    // INITIALISATION
    // =====================================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupEventListeners);
    } else {
        setupEventListeners();
    }

    // =====================================================
    // EXPORT GLOBAL
    // =====================================================

    window.invoiceAPI = invoiceAPI;
    window.loadInvoices = loadInvoices;
    window.createInvoice = createInvoice;
    window.viewInvoice = viewInvoice;
    window.downloadInvoicePDF = downloadInvoicePDF;
    window.filterInvoices = filterInvoices;
    window.setupInvoiceFilters = setupInvoiceFilters;

    console.log('✅ Module Factures chargé');
})();
